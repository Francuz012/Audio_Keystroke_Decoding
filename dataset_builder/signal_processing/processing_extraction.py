import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Union

import librosa
import numpy as np
import torch

# Configure terminal logging for pipeline monitoring
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AcousticFeatureExtractor:
    """
    Ingests continuous acoustic sessions, processes Mel-spectrogram feature matrices,
    and extracts temporally aligned keystroke targets for PyTorch ingestion.
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        n_fft: int = 2048,
        hop_length: int = 512,
        n_mels: int = 128
    ) -> None:
        self.sample_rate = sample_rate
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.n_mels = n_mels
        
        # Initialize dynamic vocabulary mapping. Index 0 is strictly reserved for CTC <BLANK>.
        self.char_to_id: Dict[str, int] = {"<BLANK>": 0}

    def _encode_character(self, character: str) -> int:
        """Maps a character to its integer ID, expanding the vocabulary dynamically."""
        if character not in self.char_to_id:
            self.char_to_id[character] = len(self.char_to_id)
        return self.char_to_id[character]

    def extract_mel_spectrogram(self, audio_path: Union[str, Path]) -> torch.Tensor:
        """Ingests a WAV file and outputs a log-scaled Mel-spectrogram tensor."""
        waveform, _ = librosa.load(audio_path, sr=self.sample_rate, mono=True)

        mel_spec = librosa.feature.melspectrogram(
            y=waveform,
            sr=self.sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            n_mels=self.n_mels
        )

        log_mel_spec = librosa.power_to_db(mel_spec, ref=np.max)
        tensor_spec = torch.from_numpy(log_mel_spec).unsqueeze(0).float()
        
        return tensor_spec

    def extract_sequence_targets(self, json_path: Union[str, Path]) -> Tuple[torch.Tensor, torch.Tensor]:
        """Parses session JSON to extract encoded character sequences and frame indices."""
        with open(json_path, 'r', encoding='utf-8') as file:
            session_data = json.load(file)

        events = session_data.get("events", [])
        events = sorted(events, key=lambda x: x.get("audio_frame_start", 0))

        target_sequence: List[int] = []
        frame_indices: List[int] = []

        for event in events:
            char = event.get("character", "")
            frame_start = event.get("audio_frame_start", 0)

            char_id = self._encode_character(char)
            target_sequence.append(char_id)
            frame_indices.append(frame_start)

        target_tensor = torch.tensor(target_sequence, dtype=torch.long)
        frame_tensor = torch.tensor(frame_indices, dtype=torch.long)

        return target_tensor, frame_tensor

    def process_session(self, session_dir: Union[str, Path]) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Processes a unified session directory to return aligned feature and target tensors."""
        session_dir = Path(session_dir)
        
        audio_files = list(session_dir.glob("*.wav"))
        json_files = list(session_dir.glob("*.json"))

        if not audio_files or not json_files:
            raise FileNotFoundError(f"Missing required .wav or .json in session root: {session_dir}")

        audio_path = audio_files[0]
        json_path = json_files[0]

        mel_spectrogram = self.extract_mel_spectrogram(audio_path)
        target_sequence, frame_indices = self.extract_sequence_targets(json_path)

        return mel_spectrogram, target_sequence, frame_indices


class DatasetCompiler:
    """
    Orchestrates the batch processing of the entire dataset root directory
    and serializes the output tensors for PyTorch ingestion.
    """

    def __init__(self, extractor: AcousticFeatureExtractor, output_dir: Union[str, Path]) -> None:
        self.extractor = extractor
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def compile_dataset(self, dataset_root: Union[str, Path]) -> None:
        """Iterates through all session directories and serializes outputs."""
        dataset_root = Path(dataset_root)
        session_dirs = [d for d in dataset_root.iterdir() if d.is_dir()]

        logging.info(f"Initiating batch extraction for {len(session_dirs)} sessions in {dataset_root}")

        for session_dir in session_dirs:
            logging.info(f"Processing: {session_dir.name}")
            try:
                features, targets, frames = self.extractor.process_session(session_dir)
                self._serialize_tensors(session_dir.name, features, targets, frames)
            except Exception as e:
                logging.error(f"Extraction failure in {session_dir.name}: {e}")

        self._serialize_vocabulary()

    def _serialize_tensors(
        self, 
        session_name: str, 
        features: torch.Tensor, 
        targets: torch.Tensor, 
        frames: torch.Tensor
    ) -> None:
        """Saves PyTorch tensors to disk."""
        output_path = self.output_dir / f"{session_name}_processed.pt"
        torch.save({
            'features': features,
            'targets': targets,
            'frames': frames
        }, output_path)
        logging.info(f"Serialized target: {output_path}")

    def _serialize_vocabulary(self) -> None:
        """Saves the dynamic vocabulary mapping for NLP sequence decoding."""
        vocab_path = self.output_dir / "vocabulary_map.json"
        with open(vocab_path, 'w', encoding='utf-8') as f:
            json.dump(self.extractor.char_to_id, f, indent=4)
        logging.info(f"Vocabulary mapping serialized: {vocab_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Acoustic Dataset Batch Compiler")
    parser.add_argument("--dataset_root", type=str, required=True, help="Root directory containing all session folders.")
    parser.add_argument("--output_dir", type=str, required=True, help="Target directory for serialized .pt files.")
    parser.add_argument("--sample_rate", type=int, default=44100, help="Audio sample rate in Hz.")
    parser.add_argument("--n_fft", type=int, default=2048, help="Fast Fourier Transform window size.")
    parser.add_argument("--hop_length", type=int, default=512, help="Hop length for feature extraction.")
    
    args = parser.parse_args()
    
    extractor = AcousticFeatureExtractor(
        sample_rate=args.sample_rate,
        n_fft=args.n_fft,
        hop_length=args.hop_length
    )
    
    compiler = DatasetCompiler(extractor=extractor, output_dir=args.output_dir)
    
    try:
        compiler.compile_dataset(args.dataset_root)
        logging.info("Batch compilation sequence completed without errors.")
    except Exception as e:
        logging.error(f"Global pipeline failure detected: {e}")

if __name__ == "__main__":
    main()