"""Run every build step in order: content, handbook, practicals, content again.

The second content pass picks up the download links the handbook step created.
Run from the repository root after any content change: ``python scripts/build_all.py``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STEPS = ["build_content.py", "build_handbook.py", "build_practicals.py", "build_content.py"]


def main() -> None:
    """Run each step and stop at the first failure."""
    for step in STEPS:
        print(f"== {step}")
        subprocess.run([sys.executable, str(ROOT / "scripts" / step)], check=True, cwd=ROOT)


if __name__ == "__main__":
    main()
