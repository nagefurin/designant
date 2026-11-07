#!/usr/bin/env python3
"""Build and validate the installable Anki add-on archive."""

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
OUTPUT = DIST / "frequency_date_reorder.ankiaddon"
FILES = ("__init__.py", "core.py", "config.json", "manifest.json")


def validate_manifest() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest.get("package"), str) or not manifest["package"].strip():
        raise ValueError("manifest.json must define a non-empty package")
    if not isinstance(manifest.get("name"), str) or not manifest["name"].strip():
        raise ValueError("manifest.json must define a non-empty name")
    if not manifest["package"].replace("_", "").isalnum():
        raise ValueError("manifest.json package must contain only letters, numbers, and underscores")


def main() -> None:
    validate_manifest()
    missing = [name for name in FILES if not (ROOT / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing required add-on files: {', '.join(missing)}")

    DIST.mkdir(exist_ok=True)
    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED) as archive:
        for relative in FILES:
            archive.write(ROOT / relative, arcname=relative)

    with ZipFile(OUTPUT) as archive:
        names = set(archive.namelist())
        required = set(FILES)
        if not required.issubset(names):
            raise RuntimeError(f"Archive is missing files: {sorted(required - names)}")
        if any(name.startswith("/") or name.startswith("../") for name in names):
            raise RuntimeError("Archive contains an unsafe path")

    print(f"Built and validated {OUTPUT}")


if __name__ == "__main__":
    main()
