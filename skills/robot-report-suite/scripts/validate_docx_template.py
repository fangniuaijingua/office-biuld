"""Audit a DOCX report against a protected template and monochrome-style contract.

The script does not edit either file.  It detects common template-first failures:
missing text anchors, a changed page geometry, additional coloured text/shading,
and missing requested template styles.  It is a gate, not a replacement for
rendered visual review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET


W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def qn(name: str) -> str:
    return W + name


def get_attr(element: ET.Element | None, name: str) -> str | None:
    return None if element is None else element.get(qn(name))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_of(element: ET.Element) -> str:
    return "".join(node.text or "" for node in element.iter(qn("t"))).strip()


def read_docx(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        doc = ET.fromstring(archive.read("word/document.xml"))
        sections = []
        for section in doc.findall(".//" + qn("sectPr")):
            page_size = section.find(qn("pgSz"))
            margins = section.find(qn("pgMar"))
            sections.append(
                {
                    "w": get_attr(page_size, "w"),
                    "h": get_attr(page_size, "h"),
                    "orient": get_attr(page_size, "orient") or "portrait",
                    "top": get_attr(margins, "top"),
                    "bottom": get_attr(margins, "bottom"),
                    "left": get_attr(margins, "left"),
                    "right": get_attr(margins, "right"),
                }
            )
        paragraphs = [text_of(p) for p in doc.findall(".//" + qn("p")) if text_of(p)]
        colours = Counter()
        shading = Counter()
        for name in (name for name in names if name.startswith("word/") and name.endswith(".xml")):
            try:
                root = ET.fromstring(archive.read(name))
            except ET.ParseError:
                continue
            colours.update(
                value.upper()
                for element in root.iter(qn("color"))
                if (value := get_attr(element, "val")) and value.lower() not in {"auto", "000000"}
            )
            shading.update(
                value.upper()
                for element in root.iter(qn("shd"))
                if (value := get_attr(element, "fill")) and value.lower() not in {"auto", "ffffff", "000000"}
            )
        return {
            "sha256": sha256(path),
            "sections": sections,
            "text": "\n".join(paragraphs),
            "paragraph_count": len(paragraphs),
            "table_count": len(doc.findall(".//" + qn("tbl"))),
            "media_count": sum(
                1 for name in names if name.startswith("word/media/") and not name.endswith("/")
            ),
            "colours": dict(colours),
            "shading": dict(shading),
        }


def load_inventory(path: Path | None) -> dict[str, object]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def counter_delta(actual: dict[str, int], baseline: dict[str, int]) -> dict[str, int]:
    result: dict[str, int] = {}
    for key, count in actual.items():
        extra = count - int(baseline.get(key, 0))
        if extra > 0:
            result[key] = extra
    return result


def normalise_sections(sections: object) -> list[dict[str, str | None]]:
    """Accept both inspector keys and the compact keys used by this validator."""
    result: list[dict[str, str | None]] = []
    for section in list(sections):
        if not isinstance(section, dict):
            continue
        result.append(
            {
                "w": section.get("w", section.get("width_twips")),
                "h": section.get("h", section.get("height_twips")),
                "orient": section.get("orient", section.get("orientation", "portrait")),
                "top": section.get("top", section.get("top_twips")),
                "bottom": section.get("bottom", section.get("bottom_twips")),
                "left": section.get("left", section.get("left_twips")),
                "right": section.get("right", section.get("right_twips")),
            }
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an output DOCX against a protected template.")
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--require-anchor", action="append", default=[])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--allow-new-colour", action="store_true", help="Use only when the user explicitly requested new colour styling.")
    parser.add_argument("--strict-monochrome", action="store_true", help="Require all WordprocessingML text colours to be black and fills to be white.")
    args = parser.parse_args()
    template = args.template.resolve()
    output = args.output.resolve()
    if template == output:
        raise SystemExit("Refusing to validate a report that overwrites the original template.")
    if not template.is_file() or not output.is_file():
        raise SystemExit("Both --template and --output must be existing .docx files.")

    inventory = load_inventory(args.inventory)
    template_info = read_docx(template)
    output_info = read_docx(output)
    anchors = list(args.require_anchor)
    if not anchors:
        anchors = list(inventory.get("suggested_protected_anchors", []))[:12]
    missing = [anchor for anchor in anchors if anchor and anchor not in str(output_info["text"])]
    expected_sections = normalise_sections(inventory.get("sections", template_info["sections"]))
    geometry_match = expected_sections == output_info["sections"]
    baseline_colours = dict(inventory.get("template_color_baseline", template_info["colours"]))
    baseline_shading = dict(inventory.get("template_shading_baseline", template_info["shading"]))
    new_colours = counter_delta(dict(output_info["colours"]), baseline_colours)
    new_shading = counter_delta(dict(output_info["shading"]), baseline_shading)
    strict_colour_violations = dict(output_info["colours"]) if args.strict_monochrome else {}
    strict_shading_violations = dict(output_info["shading"]) if args.strict_monochrome else {}
    strict_monochrome_pass = not strict_colour_violations and not strict_shading_violations

    checks = {
        "output_is_not_template": template != output,
        "template_hash_recorded": bool(template_info["sha256"]),
        "protected_anchors_present": not missing,
        "missing_anchors": missing,
        "section_geometry_matches_template": geometry_match,
        "template_media_count": template_info["media_count"],
        "output_media_count": output_info["media_count"],
        "template_media_not_reduced": output_info["media_count"] >= template_info["media_count"],
        "new_coloured_text_runs_over_baseline": new_colours,
        "new_coloured_shading_over_baseline": new_shading,
        "monochrome_delta_pass": args.allow_new_colour or (not new_colours and not new_shading),
        "strict_monochrome_requested": args.strict_monochrome,
        "strict_monochrome_coloured_text": strict_colour_violations,
        "strict_monochrome_coloured_shading": strict_shading_violations,
        "strict_monochrome_pass": strict_monochrome_pass,
        "output_paragraph_count": output_info["paragraph_count"],
        "output_table_count": output_info["table_count"],
    }
    passed = (
        checks["output_is_not_template"]
        and checks["protected_anchors_present"]
        and checks["section_geometry_matches_template"]
        and checks["template_media_not_reduced"]
        and checks["monochrome_delta_pass"]
        and checks["strict_monochrome_pass"]
    )
    report = {
        "status": "PASS" if passed else "REVIEW_REQUIRED",
        "template": str(template),
        "template_sha256": template_info["sha256"],
        "output": str(output),
        "output_sha256": output_info["sha256"],
        "checks": checks,
        "manual_review_required": [
            "Compare protected cover/basic pages, logos, existing illustrations, abstract and required tables visually.",
            "Render the report to PDF/PNG and inspect page count, wrapping, tables, figure captions and headings.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(report["status"])
    print(args.out)
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
