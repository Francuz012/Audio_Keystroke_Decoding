"""CLI entry point for recording a single session."""

import argparse
from session_manager import SessionManager

def main():
    parser = argparse.ArgumentParser(description="Record a keystroke‑audio session.")
    parser.add_argument("session_id", help="Unique ID for the session (e.g., session_001)")
    args = parser.parse_args()

    session = SessionManager(args.session_id)
    session.run()

if __name__ == "__main__":
    main()
