"""Create a beta ZIP package for CalibrationDesignerV3."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import zipfile

INCLUDE_PATHS = [
    "src",
    "tests",
    "examples",
    "README.md",
    "BETA_INSTALLATION_GUIDE.md",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    "start_calibration_designer_v3.bat",
    "calibration_designer_v3.py",
    "scripts",
]

EXCLUDE_PARTS = {
    ".venv",
    ".git",
    "__pycache__",
    ".pytest_cache",
    "outputs",
    "dist",
    "build",
    ".tmp_test_runs",
}



def _should_exclude(path: Path) -> bool:
    parts = set(path.parts)
    if parts.intersection(EXCLUDE_PARTS):
        return True
    if any(part.endswith(".egg-info") for part in path.parts):
        return True
    return False


def create_beta_zip(project_root: str | Path | None = None, dist_dir: str | Path | None = None) -> Path:
    root = Path(project_root) if project_root is not None else Path(__file__).resolve().parents[1]
    out_dir = Path(dist_dir) if dist_dir is not None else root / "dist"
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = out_dir / f"CalibrationDesignerV3_beta_{timestamp}.zip"

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for include in INCLUDE_PATHS:
            include_path = root / include
            if not include_path.exists():
                continue

            if include_path.is_file():
                zf.write(include_path, include_path.relative_to(root).as_posix())
                continue

            for file_path in include_path.rglob("*"):
                if file_path.is_dir():
                    continue
                rel = file_path.relative_to(root)
                if _should_exclude(rel):
                    continue
                zf.write(file_path, rel.as_posix())

    return zip_path


def main() -> int:
    zip_path = create_beta_zip()
    print(zip_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
