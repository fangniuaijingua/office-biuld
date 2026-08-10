"""Render a final report PDF into reviewable showcase images.

The renderer never edits the report. It creates per-page PNG previews, a
contact sheet and a manifest for a versioned ``showcase/vN`` directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit("PyMuPDF is required: python -m pip install pymupdf") from exc

from PIL import Image, ImageDraw


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_contact_sheet(pages: list[Path], output: Path, columns: int, thumbnail_width: int) -> None:
    thumbnails: list[Image.Image] = []
    for page in pages:
        with Image.open(page) as image:
            ratio = thumbnail_width / image.width
            height = max(1, round(image.height * ratio))
            thumbnails.append(image.convert("RGB").resize((thumbnail_width, height), Image.Resampling.LANCZOS))

    gap = 24
    label_height = 30
    rows = (len(thumbnails) + columns - 1) // columns
    row_heights = [0] * rows
    for index, image in enumerate(thumbnails):
        row_heights[index // columns] = max(row_heights[index // columns], image.height + label_height)
    width = columns * thumbnail_width + (columns + 1) * gap
    height = sum(row_heights) + (rows + 1) * gap
    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)
    for index, image in enumerate(thumbnails):
        row, column = divmod(index, columns)
        x = gap + column * (thumbnail_width + gap)
        y = gap + sum(row_heights[:row]) + row * gap
        sheet.paste(image, (x, y))
        draw.text((x, y + image.height + 6), f"Page {index + 1:02d}", fill="black")
    sheet.save(output, "PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a final report PDF into a versioned showcase directory.")
    parser.add_argument("--input", type=Path, required=True, help="Final, reviewed PDF report.")
    parser.add_argument("--output", type=Path, required=True, help="Empty or new showcase/vN directory.")
    parser.add_argument("--dpi", type=int, default=144, help="PNG rendering DPI; default: 144.")
    parser.add_argument("--columns", type=int, default=3, help="Contact-sheet columns; default: 3.")
    parser.add_argument("--force", action="store_true", help="Allow overwriting known generated preview files.")
    args = parser.parse_args()

    source = args.input.resolve()
    output = args.output.resolve()
    if not source.is_file() or source.suffix.lower() != ".pdf":
        raise SystemExit("--input must be an existing final PDF.")
    if args.dpi < 72 or args.dpi > 300:
        raise SystemExit("--dpi must be between 72 and 300.")
    if args.columns < 1 or args.columns > 6:
        raise SystemExit("--columns must be between 1 and 6.")
    if output == source.parent:
        raise SystemExit("--output must be a separate showcase directory.")
    output.mkdir(parents=True, exist_ok=True)
    existing = list(output.iterdir())
    if existing and not args.force:
        raise SystemExit(f"Refusing to reuse non-empty output directory: {output}; use --force for generated previews.")

    document = fitz.open(source)
    matrix = fitz.Matrix(args.dpi / 72, args.dpi / 72)
    pages: list[Path] = []
    for number, page in enumerate(document, start=1):
        destination = output / f"page-{number:02d}.png"
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        pixmap.save(destination)
        pages.append(destination)
    document.close()

    contact_sheet = output / "contact-sheet.png"
    make_contact_sheet(pages, contact_sheet, args.columns, thumbnail_width=360)
    manifest = {
        "purpose": "layout_preview",
        "source_pdf_name": source.name,
        "source_pdf_sha256": sha256(source),
        "page_count": len(pages),
        "dpi": args.dpi,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "page_images": [page.name for page in pages],
        "contact_sheet": contact_sheet.name,
        "write_policy": "Derived preview only; the source PDF and report DOCX were not modified.",
    }
    (output / "preview-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
