"""Local launcher shim so `python -m calibration_designer_v3` works without installation."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from calibration_designer_v3.app import main


if __name__ == "__main__":
    raise SystemExit(main())