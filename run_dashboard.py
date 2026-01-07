#!/usr/bin/env python3
"""Run the BookSpring analytics dashboard."""
import subprocess
import sys


def main():
    """Launch the Streamlit dashboard."""
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "src/dashboard/app.py",
        "--server.headless", "true"
    ])


if __name__ == "__main__":
    main()
