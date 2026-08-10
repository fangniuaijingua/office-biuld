"""Safely initialise a template-bound report workspace.

It copies a template into the protected input/template area and a versioned
output copy, then creates fuel, evidence and inventory scaffolding. It never
edits the user template and refuses to overwrite an existing deliverable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a protected template-bound report workspace.")
    parser.add_argument("template", type=Path)
    parser.add_argument("--workspace", type=Path, default=Path("report-workspace"))
    parser.add_argument("--output-name", help="Versioned output filename; defaults to <template-stem>_v0.docx")
    args = parser.parse_args()
    template = args.template.resolve()
    workspace = args.workspace.resolve()
    if template.suffix.lower() != ".docx":
        raise SystemExit("Use convert_legacy_doc_copy.ps1 for .doc before initialising a DOCX workspace.")
    if not template.is_file():
        raise SystemExit(f"Template not found: {template}")

    output_name = args.output_name or f"{template.stem}_v0.docx"
    if Path(output_name).suffix.lower() != ".docx":
        raise SystemExit("--output-name must end in .docx")
    for directory in ("input/template", "input/fuel", "evidence", "figures/source", "figures/export", "sections", "output", "qa"):
        (workspace / directory).mkdir(parents=True, exist_ok=True)
    input_copy = workspace / "input" / "template" / template.name
    output_copy = workspace / "output" / output_name
    if output_copy.exists():
        raise SystemExit(f"Refusing to overwrite existing output: {output_copy}")
    shutil.copy2(template, input_copy)
    shutil.copy2(template, output_copy)

    inspector = Path(__file__).with_name("inspect_docx_template.py")
    inventory = workspace / "template-inventory.json"
    subprocess.run([sys.executable, str(inspector), str(template), "--out", str(inventory)], check=True)
    contract = workspace / "format-contract.md"
    if not contract.exists():
        contract.write_text(
            "# 格式契约\n\n"
            f"模板：`{template}`\n\n"
            f"模板 SHA-256：`{sha256(template)}`\n\n"
            f"输出副本：`{output_copy}`\n\n"
            "## 必须保留\n\n"
            "- 页面/节：待根据 `template-inventory.json` 确认。\n"
            "- 文本锚点：待确认封面、摘要、目录、任务书和附录入口。\n"
            "- 图片、图标、表格：模板现有内容默认全部保留。\n\n"
            "## 样式映射\n\n"
            "| 用途 | 模板样式 | 字体/字号 | 行距/缩进 | 说明 |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| 正文 | 待确认 | 待确认 | 待确认 | 优先套用模板既有样式 |\n"
            "| 标题 | 待确认 | 待确认 | 待确认 | 不重建原章节层级 |\n"
            "| 图题/表题 | 待确认 | 待确认 | 待确认 | 编号与正文交叉引用一致 |\n\n"
            "## 新增内容限制\n\n"
            "- 颜色模式：待确认 `template_inherit`、`new_content_monochrome` 或 `strict_monochrome_override`。\n"
            "- 表格：模板样式优先；无模板样式时用黑白三线表。\n"
            "- 图：黑白可编辑源图；图题使用模板样式。\n\n"
            "## 页数与章节预算\n\n"
            "| 页/节 | 主结论 | 证据 | 图/表 | 预计篇幅 |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| 待规划 |  |  |  |  |\n\n"
            "## 尚待确认\n\n- 模板可填充区域与固定页面范围。\n",
            encoding="utf-8-sig",
        )
    manifest = {
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "mode": "template_bound",
        "template_original": str(template),
        "template_sha256": sha256(template),
        "input_copy": str(input_copy),
        "input_copy_sha256": sha256(input_copy),
        "fuel_directory": str(workspace / "input" / "fuel"),
        "output_copy": str(output_copy),
        "write_policy": "Only the output copy may be edited; preserve template anchors and media.",
        "next_gate": "Register materials in input/fuel and complete format-contract.md before inserting new report content.",
    }
    (workspace / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output_copy)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
