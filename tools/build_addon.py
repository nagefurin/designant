#!/usr/bin/env python3
"""Build the installable Anki add-on archive."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
OUTPUT = DIST / "frequency_date_reorder.ankiaddon"
FILES = ("__init__.py", "core.py", "config.json")


def main() -> None:
    DIST.mkdir(exist_ok=True)
    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED) as archive:
        for relative in FILES:
            archive.write(ROOT / relative, arcname=relative)
    print(f"Built {OUTPUT}")


if __name__ == "__main__":
    main()
