from __future__ import annotations

import zipfile
from pathlib import Path

from scripts.make_beta_zip import create_beta_zip


def test_make_beta_zip_creates_archive(local_tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    dist = local_tmp_path / "dist"
    zip_path = create_beta_zip(project_root=root, dist_dir=dist)
    assert zip_path.exists()


def test_zip_excludes_unwanted_paths(local_tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    dist = local_tmp_path / "dist"
    zip_path = create_beta_zip(project_root=root, dist_dir=dist)

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()

    excluded_markers = [
        ".venv/",
        ".git/",
        "__pycache__/",
        ".pytest_cache/",
        ".tmp_test_runs/",
        "outputs/",
        "dist/",
        "build/",
    ]
    for marker in excluded_markers:
        assert not any(marker in name for name in names)


def test_zip_includes_required_paths(local_tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    dist = local_tmp_path / "dist"
    zip_path = create_beta_zip(project_root=root, dist_dir=dist)

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()

    assert any(name.startswith("src/") for name in names)
    assert any(name.startswith("tests/") for name in names)
    assert any(name.startswith("examples/") for name in names)
    assert "README.md" in names
    assert "BETA_INSTALLATION_GUIDE.md" in names
    assert "pyproject.toml" in names
    assert "uv.lock" in names
    assert ".python-version" in names
    assert "start_calibration_designer_v3.bat" in names
    assert "calibration_designer_v3.py" in names
