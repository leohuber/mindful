import json
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "src").mkdir()
    shutil.copy2(ROOT / "scripts" / "build_addon.py", tmp_path / "scripts")
    shutil.copytree(ROOT / "src" / "mindful", tmp_path / "src" / "mindful")
    return tmp_path


def build_archive(checkout: Path) -> Path:
    subprocess.run([sys.executable, str(checkout / "scripts" / "build_addon.py")], check=True, cwd=checkout)
    return checkout / "dist" / "mindful.ankiaddon"


def test_archive_has_addon_modules_and_direct_install_manifest(checkout: Path) -> None:
    with ZipFile(build_archive(checkout)) as archive:
        assert set(archive.namelist()) == {
            "__init__.py",
            "bootstrap.py",
            "core/__init__.py",
            "application/__init__.py",
            "integration/__init__.py",
            "ui/__init__.py",
            "manifest.json",
        }
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["package"] == "mindful"
        assert manifest["name"] == "Mindful"


def test_archive_excludes_checkout_and_user_files(checkout: Path) -> None:
    with ZipFile(build_archive(checkout)) as archive:
        expected = set(archive.namelist())

    unwanted = (
        "src/mindful/__pycache__/cache.pyc",
        "src/mindful/core/__pycache__/cache.pyc",
        "src/mindful/tests/test_feature.py",
        "src/mindful/.venv/lib/package.py",
        "src/mindful/meta.json",
        "src/mindful/user_files/data.json",
        "src/mindful/config.json",
        "src/mindful/anki/__init__.py",
        "src/mindful/aqt/__init__.py",
        "src/mindful/PyQt5/__init__.py",
        "src/mindful/PyQt6/__init__.py",
        "src/mindful/PySide2/__init__.py",
        "src/mindful/PySide6/__init__.py",
        "tests/test_external.py",
        ".venv/lib/package.py",
        ".git/config",
        ".env",
    )
    for path in unwanted:
        target = checkout / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("not for distribution", encoding="utf-8")

    with ZipFile(build_archive(checkout)) as archive:
        assert set(archive.namelist()) == expected
