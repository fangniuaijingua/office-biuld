"""Read-only DOCX template inventory for the template-first report workflow.

This avoids editing a template just to discover its sections, styles, media, or
basic layout.  It deliberately uses only the Python standard library so it can
run before optional document packages are installed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET


W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def qn(name: str) -> str:
    return W + name


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_of(element: ET.Element) -> str:
    return "".join(node.text or "" for node in element.iter(qn("t"))).strip()


def get_attr(element: ET.Element | None, name: str) -> str | None:
    return None if element is None else element.get(qn(name))


def style_inventory(root: ET.Element | None) -> list[dict[str, object]]:
    if root is None:
        return []
    styles: list[dict[str, object]] = []
    for style in root.findall(qn("style")):
        style_id = get_attr(style, "styleId")
        if not style_id:
            continue
        name_element = style.find(qn("name"))
        rpr = style.find(qn("rPr"))
        fonts = rpr.find(qn("rFonts")) if rpr is not None else None
        size = rpr.find(qn("sz")) if rpr is not None else None
        color = rpr.find(qn("color")) if rpr is not None else None
        styles.append(
            {
                "id": style_id,
                "type": get_attr(style, "type"),
                "name": get_attr(name_element, "val"),
                "based_on": get_attr(style.find(qn("basedOn")), "val"),
                "font_ascii": get_attr(fonts, "ascii"),
                "font_east_asia": get_attr(fonts, "eastAsia"),
                "font_size_half_points": get_attr(size, "val"),
                "font_color": get_attr(color, "val"),
            }
        )
    return styles


def section_inventory(root: ET.Element) -> list[dict[str, str | None]]:
    sections: list[dict[str, str | None]] = []
    for section in root.findall(".//" + qn("sectPr")):
        size = section.find(qn("pgSz"))
        margin = section.find(qn("pgMar"))
        sections.append(
            {
                "width_twips": get_attr(size, "w"),
                "height_twips": get_attr(size, "h"),
                "orientation": get_attr(size, "orient") or "portrait",
                "top_twips": get_attr(margin, "top"),
                "bottom_twips": get_attr(margin, "bottom"),
                "left_twips": get_attr(margin, "left"),
                "right_twips": get_attr(margin, "right"),
                "header_twips": get_attr(margin, "header"),
                "footer_twips": get_attr(margin, "footer"),
            }
        )
    return sections


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a read-only DOCX template inventory.")
    parser.add_argument("template", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--anchor-limit", type=int, default=14)
    args = parser.parse_args()
    template = args.template.resolve()
    if template.suffix.lower() != ".docx":
        raise SystemExit("This inspector accepts .docx only; convert legacy .doc on an output copy first.")
    if not template.is_file():
        raise SystemExit(f"Template not found: {template}")

    with zipfile.ZipFile(template) as archive:
        names = set(archive.namelist())
        document = ET.fromstring(archive.read("word/document.xml"))
        styles = ET.fromstring(archive.read("word/styles.xml")) if "word/styles.xml" in names else None
        paragraphs: list[dict[str, object]] = []
        for index, paragraph in enumerate(document.findall(".//" + qn("p")), start=1):
            text = text_of(paragraph)
            ppr = paragraph.find(qn("pPr"))
            pstyle = ppr.find(qn("pStyle")) if ppr is not None else None
            if text:
                paragraphs.append(
                    {
                        "index": index,
                        "text": text[:300],
                        "style": get_attr(pstyle, "val"),
                        "contains_page_break": paragraph.find(".//" + qn("br") + "[@" + qn("type") + "='page']") is not None,
                    }
                )

        candidate_terms = ("摘要", "关键词", "目录", "参考文献", "附录", "任务书", "设计要求", "封面", "声明")
        anchors: list[str] = []
        # Cover titles are normally the first short text blocks.  Do not turn
        # full abstract/body paragraphs into immutable anchors: those are often
        # the intended fillable content of a template.
        for item in paragraphs[:4]:
            if item["text"] not in anchors:
                anchors.append(str(item["text"]))
        for item in paragraphs:
            compact_text = re.sub(r"\s+", "", str(item["text"]))
            if (
                len(str(item["text"])) <= 80
                and any(term in compact_text for term in candidate_terms)
                and item["text"] not in anchors
            ):
                anchors.append(str(item["text"]))
        anchors = anchors[: args.anchor_limit]

        colors = Counter()
        shading = Counter()
        for xml_name in (name for name in names if name.startswith("word/") and name.endswith(".xml")):
            try:
                xml = ET.fromstring(archive.read(xml_name))
            except ET.ParseError:
                continue
            colors.update(
                value.upper()
                for element in xml.iter(qn("color"))
                if (value := get_attr(element, "val")) and value.lower() not in {"auto", "000000"}
            )
            shading.update(
                value.upper()
                for element in xml.iter(qn("shd"))
                if (value := get_attr(element, "fill")) and value.lower() not in {"auto", "ffffff", "000000"}
            )

        media = sorted(
            name for name in names if name.startswith("word/media/") and not name.endswith("/")
        )
        inventory = {
            "template": str(template),
            "sha256": sha256(template),
            "bytes": template.stat().st_size,
            "sections": section_inventory(document),
            "paragraph_count": len(paragraphs),
            "table_count": len(document.findall(".//" + qn("tbl"))),
            "page_break_count": sum(1 for item in paragraphs if item["contains_page_break"]),
            "media": {"count": len(media), "files": media},
            "styles": style_inventory(styles),
            "paragraph_preview": paragraphs[:80],
            "suggested_protected_anchors": anchors,
            "template_color_baseline": dict(colors),
            "template_shading_baseline": dict(shading),
            "notes": [
                "This inventory is read-only and cannot determine visual page ranges by itself.",
                "Confirm protected pages and fillable regions in format-contract.md before editing the output copy.",
            ],
        }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
