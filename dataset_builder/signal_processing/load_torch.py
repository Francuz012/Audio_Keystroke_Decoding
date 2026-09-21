import argparse
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import torch

# Configure terminal logging for execution monitoring
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SpectrogramVisualizer:
    """
    Ingests serialized PyTorch tensors and generates human-readable 
    2D Mel-spectrogram visualizations.
    """
    
    @staticmethod
    def render_spectrogram(pt_file_path: str, output_path: str) -> None:
        """
        Loads tensor dictionary, extracts the feature matrix, and plots the spatial representation.
        """
        pt_path = Path(pt_file_path)
        if not pt_path.exists():
            raise FileNotFoundError(f"Target tensor file not found: {pt_path}")

        logging.info(f"Loading serialized tensor from: {pt_path}")
        
        # Load the PyTorch dictionary
        tensor_data = torch.load(pt_path, weights_only=False)
        
        features = tensor_data.get('features')
        if features is None:
            raise ValueError("The key 'features' was not found in the serialized tensor.")

        # The feature tensor is shaped (1, n_mels, time_frames). 
        # Squeeze the channel dimension to isolate the 2D matrix for plotting.
        mel_matrix = features.squeeze(0).numpy()

        logging.info(f"Feature matrix extracted. Matrix shape: {mel_matrix.shape}. Generating visualization.")

        # Construct the visual plot
        plt.figure(figsize=(12, 4))
        plt.imshow(mel_matrix, aspect='auto', origin='lower', cmap='viridis')
        plt.colorbar(format='%+2.0f dB')
        plt.title(f"Acoustic Mel-Spectrogram: {pt_path.stem}")
        plt.ylabel("Mel Filter Banks")
        plt.xlabel("Temporal Frames")
        plt.tight_layout()

        # Serialize plot to disk
        out_path = Path(output_path)
        plt.savefig(out_path, dpi=300)
        plt.close()
        
        logging.info(f"Spectrogram visualization rendered and saved to: {out_path}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Render PyTorch tensor to 2D Mel-spectrogram image.")
    parser.add_argument("--pt_file", type=str, required=True, help="Path to the serialized .pt file.")
    parser.add_argument("--output_image", type=str, required=True, help="Destination path for the .png output.")
    
    args = parser.parse_args()
    
    try:
        SpectrogramVisualizer.render_spectrogram(args.pt_file, args.output_image)
    except Exception as e:
        logging.error(f"Visualization pipeline failure: {e}")

if __name__ == "__main__":
    main()