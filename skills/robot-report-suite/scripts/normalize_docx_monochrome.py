"""Create a strict black-text / white-table DOCX copy without rebuilding the template.

The tool operates on OOXML parts instead of rebuilding a document with
python-docx. It preserves media, fields, sections, headers and relationships,
while remapping WordprocessingML text colors and shadings to a monochrome
output. Use only when the user explicitly requires no colored text or fills.
"""
from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import Counter
from pathlib import Path


COLOUR_TAG = re.compile(rb"<w:color\b[^>]*>", re.IGNORECASE)
SHADING_TAG = re.compile(rb"<w:shd\b[^>]*>", re.IGNORECASE)
HIGHLIGHT_TAG = re.compile(rb"<w:highlight\b[^>]*>", re.IGNORECASE)
ATTRIBUTE = re.compile(rb"\s+w:([A-Za-z]+)\s*=\s*(?:\"[^\"]*\"|'[^']*')", re.IGNORECASE)


def word_xml_part(name: str) -> bool:
    return name.startswith("word/") and name.endswith(".xml") and not name.startswith("word/theme/")


def attribute_value(tag: bytes, name: bytes) -> bytes:
    match = re.search(rb"\s+w:" + re.escape(name) + rb"\s*=\s*(?:\"([^\"]*)\"|'([^']*)')", tag, re.IGNORECASE)
    if not match:
        return b""
    return match.group(1) if match.group(1) is not None else match.group(2)


def rewrite_tag(tag: bytes, attributes: dict[bytes, bytes], remove: set[bytes]) -> bytes:
    """Update only w:* attributes while preserving every other raw XML byte."""

    def keep_or_remove(match: re.Match[bytes]) -> bytes:
        name = match.group(1).lower()
        return b"" if name in remove or name in attributes else match.group(0)

    retained = ATTRIBUTE.sub(keep_or_remove, tag)
    closing = b"/>" if retained.rstrip().endswith(b"/>") else b">"
    index = retained.rfind(closing)
    if index < 0:
        return retained
    additions = b"".join(b' w:' + key + b'="' + value + b'"' for key, value in attributes.items())
    return retained[:index] + additions + retained[index:]


def normalise_part(payload: bytes) -> tuple[bytes, Counter[str]]:
    changes: Counter[str] = Counter()

    def replace_colour(match: re.Match[bytes]) -> bytes:
        tag = match.group(0)
        value = attribute_value(tag, b"val").upper()
        if value not in {b"", b"AUTO", b"000000"}:
            changes["text_colours_to_black"] += 1
        return rewrite_tag(tag, {b"val": b"000000"}, {b"val", b"themecolor", b"themetint", b"themeshade"})

    def replace_shading(match: re.Match[bytes]) -> bytes:
        tag = match.group(0)
        fill = attribute_value(tag, b"fill").upper()
        if fill not in {b"", b"AUTO", b"FFFFFF"}:
            changes["shading_to_white"] += 1
        return rewrite_tag(
            tag,
            {b"val": b"clear", b"color": b"auto", b"fill": b"FFFFFF"},
            {b"val", b"color", b"fill", b"themecolor", b"themetint", b"themeshade", b"themefill", b"themefilltint", b"themefillshade"},
        )

    def replace_highlight(match: re.Match[bytes]) -> bytes:
        tag = match.group(0)
        changes["highlights_removed"] += 1
        return rewrite_tag(tag, {b"val": b"none"}, {b"val"})

    payload = COLOUR_TAG.sub(replace_colour, payload)
    payload = SHADING_TAG.sub(replace_shading, payload)
    payload = HIGHLIGHT_TAG.sub(replace_highlight, payload)
    return payload, changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a strict monochrome DOCX output copy.")
    parser.add_argument("--input", type=Path, required=True, help="Source DOCX copy, never the original template.")
    parser.add_argument("--output", type=Path, required=True, help="New versioned DOCX output.")
    parser.add_argument("--report", type=Path, help="Optional JSON normalisation report.")
    args = parser.parse_args()
    source = args.input.resolve()
    output = args.output.resolve()
    if source == output:
        raise SystemExit("Refusing to overwrite the source copy.")
    if not source.is_file() or source.suffix.lower() != ".docx":
        raise SystemExit("--input must be an existing .docx file.")
    if output.exists():
        raise SystemExit(f"Refusing to overwrite versioned output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    changes: Counter[str] = Counter()
    parts_changed: list[str] = []
    with zipfile.ZipFile(source, "r") as reader, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as writer:
        for item in reader.infolist():
            payload = reader.read(item.filename)
            if word_xml_part(item.filename):
                payload, part_changes = normalise_part(payload)
                if part_changes:
                    parts_changed.append(item.filename)
                    changes.update(part_changes)
            writer.writestr(item, payload)

    report = {
        "source": str(source),
        "output": str(output),
        "mode": "strict_monochrome",
        "word_xml_parts_changed": parts_changed,
        "changes": dict(changes),
        "preserved_without_rasterisation": ["media", "relationships", "sections", "headers", "footers", "fields"],
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
