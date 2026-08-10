#!/usr/bin/env python3
"""Render an editable Graphviz source into slide-ready monochrome SVG/PNG."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


ALLOWED_MONO = {
    "black", "white", "gray", "grey", "lightgray", "lightgrey",
    "darkgray", "darkgrey", "transparent", "none",
    "#000", "#000000", "#fff", "#ffffff", "#f2f2f2", "#bfbfbf",
    "#808080", "#666666", "#333333",
}
COLOR_ATTR = re.compile(r"(?:color|fontcolor|fillcolor|bgcolor)\s*=\s*\"?([^,;\]\s\"]+)", re.I)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Editable .dot source")
    parser.add_argument("--out-dir", required=True, type=Path, help="Directory for SVG/PNG and manifest")
    parser.add_argument("--formats", default="svg,png", help="Comma-separated subset of svg,png")
    parser.add_argument("--monochrome", action="store_true", help="Reject non-gray Graphviz color attributes")
    parser.add_argument("--dpi", type=int, default=180, help="PNG resolution, default: 180")
    return parser.parse_args()


def validate_monochrome(source: str) -> list[str]:
    invalid: list[str] = []
    for value in COLOR_ATTR.findall(source):
        normalized = value.lower().strip()
        is_gray_hex = False
        if re.fullmatch(r"#[0-9a-f]{3}", normalized):
            is_gray_hex = normalized[1] == normalized[2] == normalized[3]
        elif re.fullmatch(r"#[0-9a-f]{6}", normalized):
            is_gray_hex = normalized[1:3] == normalized[3:5] == normalized[5:7]
        if normalized not in ALLOWED_MONO and not is_gray_hex:
            invalid.append(value)
    return sorted(set(invalid))


def main() -> int:
    args = parse_args()
    if args.input.suffix.lower() != ".dot" or not args.input.is_file():
        print("ERROR: --input must name an existing .dot file", file=sys.stderr)
        return 2
    dot = shutil.which("dot")
    if not dot:
        print("ERROR: Graphviz 'dot' was not found on PATH", file=sys.stderr)
        return 3
    source = args.input.read_text(encoding="utf-8")
    invalid = validate_monochrome(source) if args.monochrome else []
    if invalid:
        print("ERROR: --monochrome rejects non-gray color values: " + ", ".join(invalid), file=sys.stderr)
        return 4
    formats = [item.strip().lower() for item in args.formats.split(",") if item.strip()]
    if not formats or any(item not in {"svg", "png"} for item in formats):
        print("ERROR: --formats accepts only svg,png", file=sys.stderr)
        return 2
    args.out_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[str] = []
    stem = args.input.stem
    for fmt in formats:
        target = args.out_dir / f"{stem}.{fmt}"
        command = [dot, f"-T{fmt}", str(args.input), "-o", str(target)]
        if fmt == "png":
            command.insert(1, f"-Gdpi={args.dpi}")
        subprocess.run(command, check=True)
        outputs.append(str(target.resolve()))
    manifest = {
        "source": str(args.input.resolve()),
        "outputs": outputs,
        "monochrome_checked": args.monochrome,
        "dpi": args.dpi,
        "evidence_status": "design_explanation_or_explicitly_mapped_evidence",
    }
    (args.out_dir / f"{stem}.manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
