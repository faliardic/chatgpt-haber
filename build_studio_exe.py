from __future__ import annotations

import subprocess
import sys


def main() -> None:
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            "--onefile",
            "--windowed",
            "--name",
            "GazetteStudio",
            "apps/gazette_studio.py",
        ]
    )


if __name__ == "__main__":
    main()
