#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bump.py - 版本号、规范 commit message、CHANGELOG、变更影响分析。

"可追溯、可回滚"靠 git 和文件系统，不靠提示词（C6）。
让 AI "负责版本控制"只会编个版本号，那是假的安全感；这里把它做成确定性操作。

用法:
    python bump.py --run run-20261122-01 --type feat --scope build \
        --message "实现竖线转义还原" --bump minor
    python bump.py --run . --type fix --scope build --message "修正行尾转义丢失" --commit
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import subprocess
import sys
from pathlib import Path

SCOPES = ["spec", "arch", "build", "review", "run"]
TYPES = ["feat", "fix", "docs", "refactor", "test", "chore", "perf"]

# 产物影响面映射：改了什么 → 谁必须重读
IMPACT = {
    "00-原文.md": ["spec", "reviewer"],
    "01-需求规格.md": ["architect", "builder", "reviewer(G1 重跑)"],
    "02-验收标准.md": ["architect", "builder", "reviewer", "★G1 必须重跑"],
    "03-架构方案.md": ["builder", "reviewer"],
    "04-实施路径.md": ["builder"],
    "05-实现": ["reviewer", "★G3 必须重跑"],
    "06-盲审报告.md": ["lead"],
    "07-裁决记录.md": ["lead"],
}


def say(msg: str = "") -> None:
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("utf-8", "replace").decode("ascii", "replace"))


def git(cwd: Path, *args: str) -> tuple:
    try:
        p = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except OSError as exc:
        return 127, str(exc)


def parse_version(text: str) -> tuple:
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    if not m:
        return (0, 1, 0)
    return tuple(int(x) for x in m.groups())


def bump_version(ver: tuple, kind: str) -> tuple:
    major, minor, patch = ver
    if kind == "major":
        return (major + 1, 0, 0)
    if kind == "minor":
        return (major, minor + 1, 0)
    return (major, minor, patch + 1)


def _unquote(raw: str) -> str:
    """把 git 的 C 风格转义路径（\\346\\226...）还原成 UTF-8。"""
    raw = raw.strip()
    if not raw.startswith('"') or not raw.endswith('"'):
        return raw
    body = raw[1:-1]
    out, i = bytearray(), 0
    while i < len(body):
        ch = body[i]
        if ch == "\\" and i + 3 < len(body) and body[i + 1:i + 4].isdigit():
            out.append(int(body[i + 1:i + 4], 8))
            i += 4
        elif ch == "\\" and i + 1 < len(body):
            out.append(ord(body[i + 1]))
            i += 2
        else:
            out.extend(ch.encode("utf-8"))
            i += 1
    return out.decode("utf-8", "replace")


def changed_files(run: Path) -> list:
    """改用 core.quotepath=false，避免中文文件名被转义成八进制。"""
    code, out = git(run, "-c", "core.quotepath=false", "status", "--porcelain")
    if code != 0:
        return []
    files = []
    for line in out.splitlines():
        if len(line) > 3:
            files.append(_unquote(line[3:]))
    return files


def impact_of(files: list) -> list:
    hit = []
    for f in files:
        for key, who in IMPACT.items():
            base = key.replace(".md", "")
            if f.startswith(key) or base in f:
                hit.append("%s -> 需重读: %s" % (key, "、".join(who)))
    return list(dict.fromkeys(hit))


def write_changelog(run: Path, version: str, ctype: str, scope: str,
                    message: str, files: list) -> Path:
    path = run / "CHANGELOG.md"
    head = "# 变更日志\n\n本文件由 scripts/bump.py 追加，格式固定，不手改历史条目。\n\n"
    body = "## [%s] - %s\n\n### %s(%s)\n\n- %s\n" % (
        version, _dt.date.today().isoformat(), ctype, scope, message)
    if files:
        body += "\n变更文件:\n" + "".join("- %s\n" % f for f in files[:20])
        if len(files) > 20:
            body += "- ...共 %d 个文件\n" % len(files)

    if path.is_file():
        old = path.read_text(encoding="utf-8")
        if old.startswith("# "):
            idx = old.find("\n## [")
            if idx == -1:
                new = old.rstrip() + "\n\n" + body
            else:
                new = old[:idx].rstrip() + "\n\n" + body + "\n" + old[idx:].lstrip("\n")
        else:
            new = head + body + "\n" + old
    else:
        new = head + body
    path.write_text(new, encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description="版本号 / commit message / CHANGELOG")
    ap.add_argument("--run", default=".", help="run 目录，默认当前目录")
    ap.add_argument("--type", default="feat", choices=TYPES)
    ap.add_argument("--scope", default="build", choices=SCOPES)
    ap.add_argument("--message", required=True, help="一句话，动词开头，不带句号")
    ap.add_argument("--bump", default="patch", choices=["patch", "minor", "major"])
    ap.add_argument("--commit", action="store_true", help="执行 git add -A 并提交")
    args = ap.parse_args()

    run = Path(args.run).expanduser().resolve()
    if not run.is_dir():
        say("错误: 不是目录 %s" % run)
        return 2
    msg = args.message.strip().rstrip("。.")
    if not msg:
        say("错误: --message 为空")
        return 2
    if len(msg) > 60:
        say("警告: message 超过 60 字，commit 标题会被截断阅读，建议精简")

    vpath = run / "VERSION"
    old_text = vpath.read_text(encoding="utf-8") if vpath.is_file() else "0.1.0"
    old = parse_version(old_text)
    new = bump_version(old, args.bump)
    old_s, new_s = "%d.%d.%d" % old, "%d.%d.%d" % new
    vpath.write_text(new_s + "\n", encoding="utf-8")

    files = changed_files(run)
    cl = write_changelog(run, new_s, args.type, args.scope, msg, files)

    title = "%s(%s): %s" % (args.type, args.scope, msg)
    body_lines = ["版本: %s -> %s" % (old_s, new_s)]
    impacts = impact_of(files)
    if impacts:
        body_lines.append("变更影响:")
        body_lines += ["  - " + x for x in impacts]
    body = "\n".join(body_lines)

    say("VERSION: %s -> %s" % (old_s, new_s))
    say("CHANGELOG: %s" % cl)
    say("")
    say("commit message:")
    say("  " + title)
    for line in body.splitlines():
        say("  " + line)
    if impacts:
        say("")
        say("变更影响分析（谁必须重读）:")
        for x in impacts:
            say("  - " + x)

    if args.commit:
        code, out = git(run, "add", "-A")
        if code != 0:
            say("git add 失败: %s" % out.strip())
            return 1
        code, out = git(run, "-c", "user.name=ai-eng-pipeline",
                        "-c", "user.email=pipeline@local",
                        "commit", "-m", title, "-m", body)
        if code != 0:
            say("git commit 失败: %s" % out.strip())
            return 1
        say("")
        say("已提交: %s" % title)
    else:
        say("")
        say("（未提交；确认无误后加 --commit）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
