#!/usr/bin/env python3
"""
Build the photo manifest and WebP thumbnails for the static China Tour gallery.

Run from the repository root:

    python build_gallery.py

Expected structure:

    index.html
    build_gallery.py
    photos/
        DSC_0001.JPG
        DSC_0002.JPG
        ...
        movie.mp4

The script creates:

    photos/thumbs/*.webp
    photos.json

Original photos/videos are never deleted by this script.

Requirements:
    Python 3.9+
    Pillow:
        python -m pip install Pillow

If Pillow is unavailable, the script will still create photos.json but will
skip thumbnail generation.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MEDIA_DIR = ROOT / "photos"
THUMB_DIR = MEDIA_DIR / "thumbs"
MANIFEST_FILE = ROOT / "photos.json"

# Adjust this if you want smaller/larger grid thumbnails.
THUMB_MAX_SIZE = 480

PHOTO_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".avif"
}

VIDEO_EXTENSIONS = {
    ".mp4", ".webm", ".mov", ".m4v", ".avi", ".mkv"
}


def load_pillow():
    try:
        from PIL import Image
        return Image
    except ImportError:
        return None


def is_media(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in (
        PHOTO_EXTENSIONS | VIDEO_EXTENSIONS
    )


def thumb_name(photo: Path) -> str:
    return photo.stem + ".webp"


def relative_web_path(path: Path) -> str:
    # GitHub Pages / web URLs always use forward slashes.
    return path.relative_to(ROOT).as_posix()


def make_thumbnail(Image, src: Path, dst: Path) -> bool:
    """
    Create/update one thumbnail.

    Returns True when a thumbnail was written.
    """
    # Skip when the thumbnail is newer than the original.
    if dst.exists() and dst.stat().st_mtime_ns >= src.stat().st_mtime_ns:
        return False

    dst.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(src) as im:
        # Animated images: use the first frame for the gallery thumbnail.
        try:
            im.seek(0)
        except Exception:
            pass

        # Preserve orientation from EXIF.
        try:
            from PIL import ImageOps
            im = ImageOps.exif_transpose(im)
        except Exception:
            pass

        # Convert formats/modes that WebP does not like directly.
        if im.mode not in ("RGB", "RGBA"):
            if "transparency" in im.info:
                im = im.convert("RGBA")
            else:
                im = im.convert("RGB")

        im.thumbnail(
            (THUMB_MAX_SIZE, THUMB_MAX_SIZE),
            Image.Resampling.LANCZOS
        )

        # Save as WebP. Quality 82 is a good size/quality compromise for
        # a photo grid; the original file remains untouched.
        im.save(
            dst,
            "WEBP",
            quality=82,
            method=6
        )

    return True


def main() -> int:
    if not MEDIA_DIR.is_dir():
        print(f"ERROR: media directory not found: {MEDIA_DIR}")
        return 1

    Image = load_pillow()

    if Image is None:
        print("WARNING: Pillow is not installed.")
        print("Install it with:")
        print("  python -m pip install Pillow")
        print()
        print("photos.json will still be generated, but thumbnails will not.")
    else:
        THUMB_DIR.mkdir(parents=True, exist_ok=True)

    manifest = []
    created = 0
    skipped = 0

    # Only scan files directly under photos/.
    # This deliberately ignores photos/thumbs/ so generated thumbnails are
    # never treated as source media.
    media_files = sorted(
        [p for p in MEDIA_DIR.iterdir() if is_media(p)],
        key=lambda p: p.name.lower()
    )

    for path in media_files:
        ext = path.suffix.lower()

        if ext in PHOTO_EXTENSIONS:
            thumb = THUMB_DIR / thumb_name(path)

            if Image is not None:
                try:
                    if make_thumbnail(Image, path, thumb):
                        created += 1
                    else:
                        skipped += 1
                except Exception as exc:
                    print(f"WARNING: thumbnail failed: {path.name}: {exc}")
                    thumb = None
            else:
                thumb = None

            item = {
                "name": path.name,
                "type": "photo",
                "src": relative_web_path(path),
            }

            if thumb is not None and thumb.exists():
                item["thumb"] = relative_web_path(thumb)

            manifest.append(item)

        elif ext in VIDEO_EXTENSIONS:
            manifest.append({
                "name": path.name,
                "type": "video",
                "src": relative_web_path(path),
            })

    MANIFEST_FILE.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    print(f"Media files : {len(manifest)}")
    print(f"Thumbnails  : {created} created, {skipped} unchanged")
    print(f"Manifest    : {MANIFEST_FILE}")

    if Image is None:
        print()
        print("NOTE: install Pillow and run this script again to create WebP thumbnails.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
