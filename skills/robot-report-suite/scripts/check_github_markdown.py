"""Check repository Markdown for GitHub-readable documentation defects.

The default scan avoids network access and validates local paths, basic heading
structure, simple GitHub-style anchors, media alt text, local machine paths,
oversized tables and navigation in long documents. Optional Git checks add
branch and diff-whitespace verification; remote-default verification is opt-in.
Run it from the repository being documented, not from this skill repository.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
LINK_RE = re.compile(r"(!?)\[([^\]]*)\]\(([^)]+)\)")
FENCE_RE = re.compile(r"^\s*(```+|~~~+)(.*)$")
ABSOLUTE_PATH_RE = re.compile(r"(?:\bfile://|(?<![A-Za-z])[A-Za-z]:[\\/])", re.IGNORECASE)
TOC_RE = re.compile(r"^(?:#{2,3}\s+(?:目录|快速导航|快速跳转|table of contents|contents|navigation|quick links)|.*\]\(#.+\))", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    level: str
    path: Path
    line: int
    message: str


@dataclass
class MarkdownInfo:
    headings: list[tuple[int, int, str]]
    anchors: set[str]
    lines: list[str]


def github_slug(text: str, used: Counter[str]) -> str:
    """Produce a conservative GitHub-compatible slug for ordinary headings."""
    text = re.sub(r"<[^>]+>", "", text).strip().lower()
    characters: list[str] = []
    for char in text:
        if char.isalnum() or char in {" ", "-", "_"}:
            characters.append(char)
    slug = "".join(characters).replace("_", "-")
    slug = re.sub(r"\s+", "-", slug).strip("-") or "section"
    suffix = used[slug]
    used[slug] += 1
    return slug if suffix == 0 else f"{slug}-{suffix}"


def parse_markdown(path: Path) -> MarkdownInfo:
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    headings: list[tuple[int, int, str]] = []
    anchors: set[str] = set()
    used: Counter[str] = Counter()
    in_fence = False

    for line_number, line in enumerate(lines, start=1):
        fence = FENCE_RE.match(line)
        if fence:
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            text = heading.group(2).strip()
            headings.append((line_number, level, text))
            anchors.add(github_slug(text, used))
        for explicit in re.finditer(r"\bid=[\"']([^\"']+)[\"']", line, flags=re.IGNORECASE):
            anchors.add(explicit.group(1).strip().lower())
    return MarkdownInfo(headings=headings, anchors=anchors, lines=lines)


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def split_target(value: str) -> str:
    value = value.strip()
    if value.startswith("<") and ">" in value:
        return value[1 : value.index(">")].strip()
    return value.split(maxsplit=1)[0] if value else ""


def is_external(target: str) -> bool:
    return bool(re.match(r"^(?:https?://|mailto:|tel:|data:)", target, flags=re.IGNORECASE))


def count_table_columns(line: str) -> int:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return len([cell for cell in stripped.split("|")])


def inspect_file(path: Path, root: Path, infos: dict[Path, MarkdownInfo], args: argparse.Namespace) -> list[Finding]:
    info = infos[path]
    findings: list[Finding] = []
    relative = path.relative_to(root)
    h1 = [entry for entry in info.headings if entry[1] == 1]
    if len(h1) != 1:
        findings.append(Finding("ERROR", relative, 1, f"一级标题数量为 {len(h1)}，应为 1。"))

    previous_level: int | None = None
    in_fence = False
    for number, line in enumerate(info.lines, start=1):
        fence = FENCE_RE.match(line)
        if fence:
            if not in_fence and args.require_code_language and not fence.group(2).strip():
                findings.append(Finding("WARN", relative, number, "代码块未标注语言。"))
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            if previous_level is not None and level > previous_level + 1:
                findings.append(Finding("WARN", relative, number, f"标题从 H{previous_level} 跳到 H{level}。"))
            previous_level = level

        if ABSOLUTE_PATH_RE.search(line):
            findings.append(Finding("ERROR", relative, number, "出现 file:// 或本机绝对路径。"))

        if "|" in line and not line.lstrip().startswith("<!--"):
            columns = count_table_columns(line)
            if columns > args.max_table_columns:
                findings.append(Finding("WARN", relative, number, f"表格有 {columns} 列，超过 {args.max_table_columns} 列。"))

        for match in LINK_RE.finditer(line):
            is_image, alt, raw_target = match.groups()
            target = split_target(raw_target)
            if is_image and not alt.strip():
                findings.append(Finding("ERROR", relative, number, "图片缺少 alt 文本。"))
            if not target or is_external(target):
                continue
            if ABSOLUTE_PATH_RE.match(target) or target.startswith("/"):
                findings.append(Finding("ERROR", relative, number, f"链接不是仓库相对路径：{target}"))
                continue

            local_target, marker, anchor = target.partition("#")
            local_target = unquote(local_target.split("?", maxsplit=1)[0])
            destination = path if not local_target else (path.parent / local_target).resolve()
            if not is_within(destination, root):
                findings.append(Finding("ERROR", relative, number, f"链接越出仓库：{target}"))
                continue
            if not destination.exists():
                findings.append(Finding("ERROR", relative, number, f"本地链接目标不存在：{target}"))
                continue
            if anchor:
                markdown_destination = destination
                if markdown_destination.is_dir():
                    markdown_destination = markdown_destination / "README.md"
                if markdown_destination.suffix.lower() != ".md":
                    findings.append(Finding("WARN", relative, number, f"无法校验非 Markdown 锚点：{target}"))
                    continue
                target_info = infos.get(markdown_destination)
                if target_info is None:
                    target_info = parse_markdown(markdown_destination)
                    infos[markdown_destination] = target_info
                normalized_anchor = unquote(anchor).lower()
                if normalized_anchor not in target_info.anchors:
                    findings.append(Finding("ERROR", relative, number, f"页面锚点不存在：{target}"))

    if len(info.lines) >= args.toc_threshold_lines:
        first_screen = info.lines[: min(100, len(info.lines))]
        if not any(TOC_RE.match(line.strip()) for line in first_screen):
            findings.append(Finding("WARN", relative, 1, "长文档缺少开头目录或快速导航。"))
    return findings


def scan(root: Path, args: argparse.Namespace) -> list[Finding]:
    root = root.resolve()
    files = sorted(path for path in root.rglob("*.md") if ".git" not in path.parts)
    infos = {path: parse_markdown(path) for path in files}
    findings: list[Finding] = []
    for path in files:
        findings.extend(inspect_file(path, root, infos, args))
    return findings


def run_git(root: Path, *command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )


def summarize_git_error(result: subprocess.CompletedProcess[str]) -> str:
    text = (result.stderr or result.stdout).strip().replace("\n", " ")
    return text[:180] or f"git exited with status {result.returncode}"


def inspect_git_state(root: Path, args: argparse.Namespace) -> list[Finding]:
    """Validate local repository state and, when requested, remote HEAD."""
    findings: list[Finding] = []
    relative = Path(".")
    try:
        inside = run_git(root, "rev-parse", "--is-inside-work-tree")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return [Finding("ERROR", relative, 1, "无法执行 git，不能进行仓库状态检查。")]
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return [Finding("ERROR", relative, 1, "目标目录不是 Git 工作树。")]

    for command in (("diff", "--check"), ("diff", "--cached", "--check")):
        result = run_git(root, *command)
        if result.returncode != 0:
            findings.append(Finding("ERROR", relative, 1, f"git {' '.join(command)} 失败：{summarize_git_error(result)}"))

    branch = run_git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    if branch.returncode != 0:
        findings.append(Finding("WARN", relative, 1, "当前为 detached HEAD；提交前请确认目标分支。"))

    origin = run_git(root, "remote", "get-url", "origin")
    if origin.returncode != 0:
        findings.append(Finding("WARN", relative, 1, "未配置 origin；无法核对默认分支或发布目标。"))

    if args.require_clean_tree:
        status = run_git(root, "status", "--porcelain")
        if status.returncode != 0:
            findings.append(Finding("ERROR", relative, 1, f"无法读取工作区状态：{summarize_git_error(status)}"))
        elif status.stdout.strip():
            findings.append(Finding("ERROR", relative, 1, "工作区仍有未提交改动。"))

    if args.verify_remote_default:
        remote_head = run_git(root, "ls-remote", "--symref", "origin", "HEAD")
        if remote_head.returncode != 0:
            findings.append(Finding("ERROR", relative, 1, f"无法读取远程默认分支：{summarize_git_error(remote_head)}"))
            return findings
        match = re.search(r"^ref: refs/heads/(.+)\tHEAD$", remote_head.stdout, flags=re.MULTILINE)
        if not match:
            findings.append(Finding("ERROR", relative, 1, "远程未返回可解析的默认分支。"))
            return findings
        expected = f"origin/{match.group(1)}"
        local_head = run_git(root, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
        if local_head.returncode != 0:
            findings.append(Finding("WARN", relative, 1, f"本地未设置 origin/HEAD；远程默认分支为 {expected}。"))
        elif local_head.stdout.strip() != expected:
            findings.append(Finding("ERROR", relative, 1, f"本地 {local_head.stdout.strip()} 与远程默认分支 {expected} 不一致；请 fetch 后执行 git remote set-head origin -a。"))
    return findings


def run_self_test() -> int:
    with tempfile.TemporaryDirectory() as raw_directory:
        root = Path(raw_directory)
        (root / "docs").mkdir()
        (root / "assets").mkdir()
        (root / "assets" / "board.png").write_bytes(b"placeholder")
        (root / "docs" / "protocol.md").write_text(
            "# 协议\n\n## 目录\n\n- [字段](#字段)\n\n## 字段\n\n```text\nlength=8\n```\n\n"
            + "\n".join("- 已归档记录" for _ in range(185))
            + "\n",
            encoding="utf-8",
        )
        (root / "README.md").write_text(
            "# 示例\n\n[协议](docs/protocol.md#字段)\n\n![控制板](assets/board.png)\n",
            encoding="utf-8",
        )
        args = argparse.Namespace(
            require_code_language=True,
            max_table_columns=8,
            toc_threshold_lines=180,
            verify_git_state=False,
            verify_remote_default=False,
            require_clean_tree=False,
        )
        if scan(root, args):
            print("Self-test failed: a valid fixture produced findings.", file=sys.stderr)
            return 1
        (root / "README.md").write_text("# 示例\n\n![](missing.png)\n", encoding="utf-8")
        if not any(finding.level == "ERROR" for finding in scan(root, args)):
            print("Self-test failed: an invalid fixture produced no error.", file=sys.stderr)
            return 1
    print("Self-test passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check GitHub-readable Markdown in a local repository.")
    parser.add_argument("root", nargs="?", type=Path, default=Path("."), help="Repository root to inspect.")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures.")
    parser.add_argument("--require-code-language", action="store_true", help="Warn on untyped fenced code blocks.")
    parser.add_argument("--max-table-columns", type=int, default=8, help="Warn when a table row has more columns.")
    parser.add_argument("--toc-threshold-lines", type=int, default=180, help="Warn when a longer page has no opening navigation.")
    parser.add_argument("--verify-git-state", action="store_true", help="Check Git worktree, branch and diff whitespace errors.")
    parser.add_argument("--verify-remote-default", action="store_true", help="Query origin and verify that origin/HEAD matches its default branch.")
    parser.add_argument("--require-clean-tree", action="store_true", help="Fail when the Git worktree has uncommitted changes.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in fixtures instead of scanning a repository.")
    args = parser.parse_args()
    if args.self_test:
        return run_self_test()
    root = args.root.resolve()
    if not root.is_dir():
        parser.error(f"Repository root not found: {root}")
    findings = scan(root, args)
    if args.verify_git_state or args.verify_remote_default or args.require_clean_tree:
        findings.extend(inspect_git_state(root, args))
    for finding in findings:
        print(f"{finding.level} {finding.path}:{finding.line}: {finding.message}")
    errors = sum(finding.level == "ERROR" for finding in findings)
    warnings = sum(finding.level == "WARN" for finding in findings)
    print(f"Checked {len(list(root.rglob('*.md')))} Markdown files: {errors} error(s), {warnings} warning(s).")
    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
