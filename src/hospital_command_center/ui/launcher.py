"""Streamlit process launcher for console script entry."""

import subprocess
import sys
from pathlib import Path

from hospital_command_center.core.config import get_settings


def main() -> None:
    settings = get_settings()
    app_path = Path(__file__).resolve().parent / "app.py"
    root = app_path.parents[3]
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_path),
            "--server.port",
            str(settings.streamlit_server_port),
        ],
        check=True,
        cwd=root,
    )
