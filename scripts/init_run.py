#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""init_run.py - 新建一次 AI 工程流水线运行目录。

只做确定性的事情：建目录、铺模板、填占位符、git init、首次提交。
不做判级、不写需求、不做架构。判级由 lead 写进 07。

用法:
    python init_run.py "把 markdown 表格转 csv 的命令行工具" --root .
    python init_run.py "<需求原文>" --root D:/proj --size M
    python init_run.py --file req.txt --root .        # 从文件读原文
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_ROOT / "assets" / "templates"

# 需要铺出来的壳：模板相对路径 -> 运行目录内相对路径（None 表示同名）
LAYOUT = [
    ("00-原文.md", "00-原文.md"),
    ("00a-意图主线.md", "00a-意图主线.md"),
    ("00b-领域实例.md", "00b-领域实例.md"),
    ("00d-场景工况.md", "00d-场景工况.md"),
    ("00e-需求澄清.md", "00e-需求澄清.md"),
    ("00f-专业复核.md", "00f-专业复核.md"),
    ("01-需求规格.md", "01-需求规格.md"),
    ("02-验收标准.md", "02-验收标准.md"),
    ("03-架构方案.md", "03-架构方案.md"),
    ("04-实施路径.md", "04-实施路径.md"),
    ("05-实现/README.md", "05-实现/README.md"),
    ("06-盲审报告.md", "06-盲审报告.md"),
    ("07-裁决记录.md", "07-裁决记录.md"),
    ("08-追溯矩阵.md", "08-追溯矩阵.md"),
]

# 只有陌生领域才铺取证台账（预设领域不铺，避免误导成"必须填"）
LAYOUT_CUSTOM = [("00c-领域取证.md", "00c-领域取证.md")]


def say(msg: str = "") -> None:
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("utf-8", "replace").decode("ascii", "replace"))


def next_run_id(root: Path, today: str) -> str:
    """run-YYYYMMDD-NN，NN 为当日已有目录的最大值 +1，两位补零。"""
    pat = re.compile(r"^run-" + today + r"-(\d{2,3})$")
    used = []
    if root.is_dir():
        for child in root.iterdir():
            m = pat.match(child.name)
            if m and child.is_dir():
                used.append(int(m.group(1)))
    return "run-%s-%02d" % (today, (max(used) + 1) if used else 1)


def render(text: str, mapping: dict) -> str:
    for key, value in mapping.items():
        text = text.replace("{{%s}}" % key, value)
    return text


def git(args: list, cwd: Path) -> tuple:
    try:
        proc = subprocess.run(
            ["git"] + args, cwd=str(cwd), capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except OSError as exc:  # git 不存在
        return 127, str(exc)


def main() -> int:
    ap = argparse.ArgumentParser(description="新建一次 AI 工程流水线运行目录")
    ap.add_argument("request", nargs="*", help="需求原文（口语即可，原样落盘）")
    ap.add_argument("--file", dest="req_file", help="从文本文件读取需求原文")
    ap.add_argument("--root", default=".", help="运行目录的父目录，默认当前目录")
    ap.add_argument("--domain", default="未判",
                    choices=["software", "hardware", "hr", "custom", "未判"],
                    help="Stage 0 领域判定，默认未判（由 lead 补全 00b 并经 G0）")
    ap.add_argument("--size", default="未判", choices=["S", "M", "L", "未判"],
                    help="lead 判级结果，默认未判（由 lead 补写 07）")
    ap.add_argument("--no-git", action="store_true", help="不执行 git init")
    args = ap.parse_args()

    raw = ""
    if args.req_file:
        raw = Path(args.req_file).read_text(encoding="utf-8")
    elif args.request:
        raw = " ".join(args.request)
    if not raw.strip():
        say("错误: 需求原文为空。用法: python init_run.py \"<需求原文>\" --root .")
        return 2

    if not TEMPLATES.is_dir():
        say("错误: 找不到模板目录 %s" % TEMPLATES)
        return 2

    root = Path(args.root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    today = _dt.date.today().strftime("%Y%m%d")
    run_id = next_run_id(root, today)
    run_dir = root / run_id
    if run_dir.exists():
        say("错误: 目录已存在 %s" % run_dir)
        return 2
    run_dir.mkdir(parents=False)

    mapping = {
        "RUN_ID": run_id,
        "DATE": _dt.date.today().isoformat(),
        "ORIGINAL_REQUEST": raw.strip(),
        "DOMAIN": args.domain,
        "SIZE": args.size,
    }

    created = []
    layout = list(LAYOUT)
    if args.domain in ("custom", "未判"):
        layout += LAYOUT_CUSTOM
    for src_rel, dst_rel in layout:
        src = TEMPLATES / src_rel
        dst = run_dir / dst_rel
        if not src.exists():
            say("错误: 缺少模板 %s" % src)
            return 2
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(render(src.read_text(encoding="utf-8"), mapping), encoding="utf-8")
        created.append(dst_rel)

    # 版本控制落地成脚本而不是角色（C6）
    git_state = "skipped"
    if not args.no_git:
        if shutil.which("git") is None:
            git_state = "git-not-found"
        else:
            code, out = git(["rev-parse", "--is-inside-work-tree"], run_dir)
            if code != 0:
                git(["init", "-q"], run_dir)
                git(["symbolic-ref", "HEAD", "refs/heads/main"], run_dir)
            git(["add", "-A"], run_dir)
            code, out = git([
                "-c", "user.name=ai-eng-pipeline",
                "-c", "user.email=pipeline@local",
                "commit", "-q", "-m",
                "chore(run): 初始化 %s 骨架（%d 份产物空壳）" % (run_id, len(created)),
            ], run_dir)
            git_state = "committed" if code == 0 else "commit-skipped"

    say("")
    say("运行目录: %s" % run_dir)
    say("领域: %s（Stage 0 需复核并补全 00b）" % args.domain)
    say("判级: %s（由 lead 复核并写入 07）" % args.size)
    say("git: %s" % git_state)
    say("")
    say("已铺模板:")
    for item in created:
        say("  - %s" % item)
    say("")
    say("下一步（按顺序，不许跳）:")
    say("  0 [Stage 0] lead 判领域、补全 00b-领域实例、过 G0、请用户确认")
    ref = "_template" if args.domain in ("custom", "未判") else args.domain
    say("    参考 references/core/stage0-instantiate.md 与 references/domains/%s.md" % ref)
    if args.domain in ("custom", "未判"):
        say("  0b [!] 陌生领域：先取证再填槽位")
        say("    读 references/core/domain-discovery.md（E0-E3 四级证据）")
        say("    产出 00c-领域取证.md，过 G0.9；取证能力不足则不许进 Stage 1")
        say("    规则：写进 02 的每条判据必须能追到 E0/E1 证据编号，E3 只能当问题不能当判据")
    say("  0c [!] 场景实例化：读 references/core/scenario.md，写 00d-场景工况.md，过 G0.10")
    say("    SC1-SC8 八槽位 -> OP 工况参数 -> DC 设计约束（挂 RULE-/EV-）")
    say("    用户给不出参数：分「知识缺口(去查)/输入缺口(登记假设)」，假设上限 S2/M5/L8")
    say("  0d 规则包：读 references/core/rulepack.md，按场景标签挂 rulepacks/<pack>@<ver>")
    say("    R0-R3 四级；R3 社区规则只能作建议，不得当拒收判据")
    say("    —— 领域与场景未确认，不许进入 Stage 1（I11）")
    say("  0e 澄清（I12）：读 references/core/intake-bridge.md，用领域包槽位10框架提问")
    say("    把「用户口语 -> 专业含义 -> 据此追问」记进 00e-需求澄清.md，原话逐字保留")
    say("  0f 专家复核（I12）：委派独立领域专家（roles/domain-expert.md），产出 00f-专业复核.md")
    say("    翻译者≠复核者；无子代理环境如实标 unblinded，不许假装独立")
    say("  1. lead 读 00.1 判级，写 07 第 1 节")
    say("  2. M/L: spec 写 01 + 02（02 前置于架构）；每条 R 来源须指向 SC/OP/RULE/假设")
    say("  3. 过 G0+G0.10+G0.11+G1: python scripts/check_run.py \"%s\" --stage g0|g1" % run_dir)
    say("  4. architect 写 03（含规则包引用段）+ 04，过 G2")
    say("  5. builder 写 05-实现/，过自查")
    say("  6. reviewer 写 08-追溯矩阵（扫四类孤儿，层覆盖 L0-L7）")
    say("  7. 起独立子代理盲审（见 references/core/blind-review.md），产出 06")
    say("  8. lead 判 G3，写 07 第 2/3 节，向用户汇报")
    say("")
    say("判门禁前先过 anti-bypass.md 的自检三问；发现 B1/B2/B3/B5 -> VOID，不是返工")
    return 0


if __name__ == "__main__":
    sys.exit(main())
