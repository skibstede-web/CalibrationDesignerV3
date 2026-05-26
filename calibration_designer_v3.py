"""Local launcher shim so `python -m calibration_designer_v3` works without installation."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
PACKAGE = SRC / "calibration_designer_v3"
src_path = str(SRC)
if src_path in sys.path:
    sys.path.remove(src_path)
sys.path.insert(0, src_path)

if PACKAGE.exists():
    __path__ = [str(PACKAGE)]  # Makes this launcher safe if imported as a package.

from calibration_designer_v3.app import main


if __name__ == "__main__":
    raise SystemExit(main())
