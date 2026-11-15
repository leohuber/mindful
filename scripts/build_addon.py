"""Build a direct-install Anki add-on archive."""

import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "mindful"
DESTINATION = ROOT / "dist" / "mindful.ankiaddon"
ADDON_FILES = (
    "__init__.py",
    "bootstrap.py",
    "core/__init__.py",
    "application/__init__.py",
    "integration/__init__.py",
    "ui/__init__.py",
    "manifest.json",
)


def main() -> None:
    """Write the explicitly listed add-on files at the archive root."""
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(DESTINATION, "w", compression=ZIP_DEFLATED) as archive:
        for name in ADDON_FILES:
            archive.write(SOURCE / name, name)
    sys.stdout.write(f"Built {DESTINATION}\n")


if __name__ == "__main__":
    main()
