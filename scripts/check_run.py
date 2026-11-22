#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_run.py - 对一次运行目录做机械校验（门禁的可执行部分）。

只查"能不能判真假"的部分：文件齐不齐、字数超没超、编号追不追溯、级别标没标。
不判断方案好不好、代码优雅不优雅——那些是 reviewer 的事。

用法:
    python check_run.py <run 目录>            # 全部检查
    python check_run.py <run 目录> --stage g1 # 只查需求门禁
退出码: 0 全过；1 有 NG。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

LIMITS = {
    "00-原文.md": 5000,
    "01-需求规格.md": 1200,
    "02-验收标准.md": 900,
    "03-架构方案.md": 1500,
    "04-实施路径.md": 800,
    "06-盲审报告.md": 1000,
    "07-裁决记录.md": 600,
}

BLACKLIST = ["好用", "易用", "友好", "高效", "快速", "稳定", "健壮", "合理", "优雅",
             "灵活", "尽量", "适当", "较好", "基本满足", "等等", "若干", "大量"]

REQUIRED_SECTIONS = {
    "01-需求规格.md": ["需求清单", "范围边界", "冲突与未决", "假设"],
    "02-验收标准.md": ["判据表"],
    "03-架构方案.md": ["取舍记录", "失败模式", "依赖", "验证路径"],
    "04-实施路径.md": ["步骤"],
    "06-盲审报告.md": ["读过的文件", "攻击点", "问题清单", "AC 证据核对"],
    "07-裁决记录.md": ["判级", "门禁判定"],
}

CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
WORD = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_\-\.]*")

results: list = []


def ok(cid, desc, detail=""):
    results.append((True, cid, desc, detail))


def ng(cid, desc, detail=""):
    results.append((False, cid, desc, detail))


def count_units(text: str) -> int:
    """汉字按字计，连续拉丁串按 1 词计。"""
    return len(CJK.findall(text)) + len(WORD.findall(CJK.sub(" ", text)))


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def table_rows(text: str) -> list:
    """取出所有 markdown 表格行，返回单元格列表（已 strip）。"""
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("|") and s.count("|") >= 2:
            if re.match(r"^\|[\s:\-|]+\|$", s):
                continue  # 分隔行
            cells = [c.strip() for c in s.strip("|").split("|")]
            rows.append(cells)
    return rows


def section(text: str, key: str) -> str:
    """按标题行取某一段（标题行含 key），到下一个标题为止。"""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("#") and key in stripped:
            start = i
            break
    if start is None:
        return ""
    out = []
    for line in lines[start + 1:]:
        if line.lstrip().startswith("#"):
            break
        out.append(line)
    return "\n".join(out)


def is_blank(cell: str) -> bool:
    cell = cell.strip()
    return cell in ("", "__", "—", "N/A", "待填")


# ---------------------------------------------------------------- 结构

def check_structure(run: Path, stage: str) -> None:
    need = ["00-原文.md"]
    if stage in ("g1", "all"):
        need += ["01-需求规格.md", "02-验收标准.md"]
    if stage in ("g2", "all"):
        need += ["03-架构方案.md", "04-实施路径.md"]
    if stage in ("g3", "all"):
        need += ["06-盲审报告.md", "07-裁决记录.md"]
    for name in need:
        p = run / name
        if p.is_file() and p.stat().st_size > 0:
            ok("S." + name[:2], "存在 %s" % name)
        else:
            ng("S." + name[:2], "缺失或为空 %s" % name)

    if stage in ("g3", "all"):
        impl = run / "05-实现"
        if impl.is_dir() and any(p.is_file() for p in impl.rglob("*")):
            ok("S.05", "存在 05-实现/ 且有文件")
        else:
            ng("S.05", "05-实现/ 为空或不存在")
        if (impl / "README.md").is_file():
            ok("S.05R", "存在 05-实现/README.md")
        else:
            ng("S.05R", "缺 05-实现/README.md（运行方式 + AC→测试映射）")
        v = run / "VERSION"
        if v.is_file():
            ok("S.VER", "存在 VERSION = %s" % v.read_text(encoding="utf-8").strip())
        else:
            ng("S.VER", "缺 VERSION（用 scripts/bump.py 生成）")
        c = run / "CHANGELOG.md"
        if c.is_file():
            ok("S.CL", "存在 CHANGELOG.md")
        else:
            ng("S.CL", "缺 CHANGELOG.md（用 scripts/bump.py 生成）")


def check_word_limits(run: Path) -> None:
    for name, limit in LIMITS.items():
        p = run / name
        if not p.is_file():
            continue
        n = count_units(read(p))
        if n <= limit:
            ok("W." + name[:2], "%s 字数 %d/%d" % (name, n, limit))
        else:
            ng("W." + name[:2], "%s 超限 %d/%d" % (name, n, limit), "删解释，留契约")


def check_sections(run: Path) -> None:
    for name, keys in REQUIRED_SECTIONS.items():
        p = run / name
        if not p.is_file():
            continue
        text = read(p)
        missing = [k for k in keys if k not in text]
        if missing:
            ng("H." + name[:2], "%s 缺章节" % name, ",".join(missing))
        else:
            ok("H." + name[:2], "%s 章节齐备" % name)


# ---------------------------------------------------------------- G1

def check_g1(run: Path) -> None:
    r1 = read(run / "01-需求规格.md")
    r2 = read(run / "02-验收标准.md")
    r7_txt = read(run / "07-裁决记录.md")

    req_ids = []
    for cells in table_rows(r1):
        if cells and re.fullmatch(r"R\d+", cells[0]):
            req_ids.append(cells[0])
    req_ids = list(dict.fromkeys(req_ids))
    if req_ids:
        ok("G1.1", "01 有需求编号 %d 条" % len(req_ids), ",".join(req_ids))
    else:
        ng("G1.1", "01 无 R# 编号")

    blank_src = []
    for cells in table_rows(r1):
        if cells and re.fullmatch(r"R\d+", cells[0]):
            src = cells[2] if len(cells) > 2 else ""
            if is_blank(src):
                blank_src.append(cells[0])
    if blank_src:
        ng("G1.1b", "01 需求缺来源", ",".join(blank_src))
    elif req_ids:
        ok("G1.1b", "01 每条需求有来源或 [假设]")

    ac_rows = {}
    for cells in table_rows(r2):
        if cells and re.fullmatch(r"AC\d+", cells[0]):
            cov = cells[1] if len(cells) > 1 else ""
            ac_rows[cells[0]] = cov
    if ac_rows:
        ok("G1.2", "02 有 AC %d 条" % len(ac_rows))
    else:
        ng("G1.2", "02 无 AC# 编号")

    covered = set()
    bad_ref = []
    for ac, cov in ac_rows.items():
        found = re.findall(r"R\d+", cov)
        if not found:
            bad_ref.append(ac)
        covered.update(found)
    unknown = sorted(covered - set(req_ids))
    if bad_ref:
        ng("G1.2b", "AC 未覆盖任何 R", ",".join(bad_ref))
    elif unknown:
        ng("G1.2b", "AC 引用了不存在的 R", ",".join(unknown))
    elif ac_rows:
        ok("G1.2b", "AC 全部指向存在的 R")

    uncovered = [r for r in req_ids if r not in covered]
    if uncovered:
        ng("G1.2c", "有 R 无 AC 覆盖", ",".join(uncovered))
    elif req_ids:
        ok("G1.2c", "每条 R 至少 1 条 AC")

    # AC 三段可判定：判定列与期望列非空
    empty_cells = []
    for cells in table_rows(r2):
        if cells and re.fullmatch(r"AC\d+", cells[0]):
            if len(cells) < 4 or is_blank(cells[2]) or is_blank(cells[3]):
                empty_cells.append(cells[0])
    if empty_cells:
        ng("G1.3", "AC 缺判定命令或期望结果", ",".join(empty_cells))
    elif ac_rows:
        ok("G1.3", "AC 均有判定命令与可观测期望")

    hits = []
    for cells in table_rows(r2):
        if cells and re.fullmatch(r"AC\d+", cells[0]):
            joined = " ".join(cells[2:])
            for w in BLACKLIST:
                if w in joined:
                    hits.append("%s:%s" % (cells[0], w))
    if hits:
        ng("G1.4", "02 判据含不可测词", ",".join(hits))
    else:
        ok("G1.4", "02 判据无不可测词")

    if "冲突与未决" in r1:
        seg = section(r1, "冲突与未决")
        body = re.sub(r"<!--.*?-->", "", seg, flags=re.S)
        body = re.sub(r"[（(][^）)]*[）)]", "", body)
        body = re.sub(r"^[#\s\-:：>]*", "", body).strip()
        if len(body) < 2:
            ng("G1.5", "01 冲突段为空白", "必须写'无'或列出冲突")
        elif body.startswith("无"):
            ok("G1.5", "01 声明无冲突")
        else:
            # 有冲突：必须有 07 的裁决，否则 G1 不许过（不许自行消解）
            resolved = False
            for cells in table_rows(r7_txt):
                if cells and re.fullmatch(r"D\d+", cells[0]):
                    joined = "".join(cells[1:])
                    filled = sum(1 for c in cells[1:] if not is_blank(c))
                    if filled >= 4 and ("冲突" in joined or "互斥" in joined):
                        resolved = True
            if resolved:
                ok("G1.5", "01 冲突已在 07 裁决")
            else:
                ng("G1.5b", "01 存在未裁决冲突", "先在 07 记一条裁决再回 G1")

    scope = section(r1, "范围边界")
    items = [l for l in scope.splitlines() if re.match(r"^\s*(\d+[\.\)]|[-*])\s+\S", l)]
    if len(items) >= 2:
        ok("G1.6", "01 范围边界 %d 条" % len(items))
    else:
        ng("G1.6", "01 范围边界不足 2 条", "当前 %d 条" % len(items))


# ---------------------------------------------------------------- G2

def check_g2(run: Path) -> None:
    r3 = read(run / "03-架构方案.md")
    r4 = read(run / "04-实施路径.md")
    r2 = read(run / "02-验收标准.md")

    trade = []
    if "取舍记录" in r3:
        seg = section(r3, "取舍记录")
        for line in seg.splitlines():
            if "选择" in line and "｜" in line:
                parts = [p for p in line.split("｜") if p.strip()]
                if len(parts) >= 3 and "代价" in line:
                    trade.append(line.strip())
    if len(trade) >= 2:
        ok("G2.1", "03 取舍三段式 %d 条" % len(trade))
    else:
        ng("G2.1", "03 取舍三段式不足 2 条", "需 '选择了X（放弃Y）｜理由｜代价'")

    fails = []
    for cells in table_rows(r3):
        if cells and re.fullmatch(r"F\d+", cells[0]) and len(cells) >= 4:
            if all(not is_blank(c) for c in cells[1:4]):
                fails.append(cells[0])
    if len(fails) >= 2:
        ok("G2.2", "03 失败模式 %d 条完整" % len(fails))
    else:
        ng("G2.2", "03 失败模式不足 2 条或缺列", "需 触发/表现/兜底 三列")

    ac_ids = [c[0] for c in table_rows(r2) if c and re.fullmatch(r"AC\d+", c[0])]
    mapped = set()
    if "验证路径" in r3:
        mapped = set(re.findall(r"AC\d+", section(r3, "验证路径")))
    miss = [a for a in ac_ids if a not in mapped]
    if ac_ids and not miss:
        ok("G2.3", "03 验证路径覆盖全部 AC")
    else:
        ng("G2.3", "03 验证路径缺 AC", ",".join(miss) or "无映射段")

    if "依赖" in r3:
        dep_seg = section(r3, "依赖")
        dep_rows = [c for c in table_rows(dep_seg) if len(c) >= 3
                    and not re.fullmatch(r"[-\s]*", c[0]) and c[0] != "依赖"]
        blank = [c[0] for c in dep_rows if is_blank(c[1]) or is_blank(c[2])]
        if not dep_rows:
            ok("G2.4", "03 无依赖表行")
        elif blank:
            ng("G2.4", "03 依赖缺版本/可用性", ",".join(blank))
        else:
            ok("G2.4", "03 依赖 %d 条已写明版本与可用性" % len(dep_rows))

    steps = []
    for cells in table_rows(r4):
        if cells and re.fullmatch(r"S\d+", cells[0]) and len(cells) >= 5:
            steps.append(cells)
    bad_steps = [c[0] for c in steps if is_blank(c[2]) or is_blank(c[4])]
    if steps and not bad_steps:
        ok("G2.7", "04 步骤 %d 条均有产出与回退点" % len(steps))
    elif steps:
        ng("G2.7", "04 步骤缺产出文件或回退点", ",".join(bad_steps))
    else:
        ng("G2.7", "04 无步骤表（S# 编号）")

    vague = [w for w in ("完善细节", "优化结构", "搭建框架", "其他类似") if w in r4]
    if vague:
        ng("G2.8", "04 含不可执行步骤词", ",".join(vague))
    elif steps:
        ok("G2.8", "04 无'完善细节'类空步骤")


# ---------------------------------------------------------------- G3

def check_g3(run: Path) -> None:
    r6 = read(run / "06-盲审报告.md")
    r7 = read(run / "07-裁决记录.md")
    r2 = read(run / "02-验收标准.md")

    m = re.search(r"REVIEW_MODE:\s*([a-z]+)", r6)
    mode = m.group(1) if m else ""
    if mode == "blinded":
        ok("G3.1", "REVIEW_MODE = blinded")
    elif mode in ("degraded", "unblinded", "invalid"):
        ng("G3.1", "REVIEW_MODE = %s（非 blinded 需 07 登记裁决）" % mode)
    else:
        ng("G3.1", "06 缺 REVIEW_MODE")

    # 隔离污染检查：清单里不许出现 01/03/04
    seg = section(r6, "读过的文件")
    listed = re.findall(r"`?([A-Za-z]:[\\/][^`\n]*|/[^`\n]*|[\w\-\.]+\.md|05-实现[^\s`]*)", seg)
    leaked = [x for x in listed if any(k in x for k in ("01-需求规格", "03-架构方案", "04-实施路径"))]
    if leaked:
        ng("G3.1b", "审查读到了未授权文件", ",".join(sorted(set(leaked))))
    elif seg.strip():
        ok("G3.1b", "审查文件清单未见越权读取")
    else:
        ng("G3.1b", "06 未自证读过哪些文件")

    levels = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    found_explicit = False
    for lv in levels:
        mm = re.search(lv + r"\s*[=:：]\s*(\d+)", r6)
        if mm:
            levels[lv] = int(mm.group(1))
            found_explicit = True
    if not found_explicit:
        for cells in table_rows(r6):
            for c in cells:
                if c in levels:
                    levels[c] += 1
                    break
    open_bad = levels["P0"] + levels["P1"]
    if open_bad == 0:
        ok("G3.3", "未闭环 P0/P1 = 0")
    else:
        ng("G3.3", "存在未闭环问题 P0=%d P1=%d" % (levels["P0"], levels["P1"]))

    passed = bool(re.search(r"结论[:：]?\s*PASS|结论[^\n]*\bPASS\b", r6))
    if passed and open_bad == 0:
        ok("G3.2", "结论 PASS 且与级别自洽")
    elif passed and open_bad > 0:
        ng("G3.2", "结论 PASS 但有 P0/P1", "自相矛盾，审查无效")
    else:
        ng("G3.2", "结论非 PASS", "FAIL 需新一轮闭环")

    ac_ids = [c[0] for c in table_rows(r2) if c and re.fullmatch(r"AC\d+", c[0])]
    evid = set()
    if "AC 证据核对" in r6:
        seg4 = section(r6, "AC 证据核对")
        evid = set(re.findall(r"AC\d+", seg4))
    miss = [a for a in ac_ids if a not in evid]
    if ac_ids and not miss:
        ok("G3.4", "06 证据表覆盖全部 %d 条 AC" % len(ac_ids))
    else:
        ng("G3.4", "06 证据表缺 AC", ",".join(miss) or "无证据段")

    # 无效审查：全 0 问题却无攻击过程
    if levels["P0"] + levels["P1"] + levels["P2"] == 0:
        atk = 0
        if "攻击点" in r6:
            seg2 = section(r6, "攻击点")
            atk = len([c for c in table_rows(seg2) if c and not is_blank(c[1] if len(c) > 1 else "")])
        if atk >= 3:
            ok("G3.7", "零问题但有 %d 个攻击点实证" % atk)
        else:
            ng("G3.7", "零问题且攻击点不足 3 个", "判为无效审查")
    else:
        ok("G3.7", "有问题清单，非空审查")

    if re.search(r"G1\s*\|", r7) or "G1" in r7:
        ok("G3.5", "07 有门禁判定记录")
    else:
        ng("G3.5", "07 无门禁判定记录")
    if re.search(r"[Ss]/[Mm]/[Ll]|级别[:：]\s*(S|M|L)", r7):
        ok("G3.6", "07 有判级记录")
    else:
        ng("G3.6", "07 缺判级记录", "lead 第一个动作是判级")


# ---------------------------------------------------------------- 05

def check_impl(run: Path) -> None:
    impl = run / "05-实现"
    if not impl.is_dir():
        return
    bad = []
    for p in impl.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in (".py", ".js", ".ts", ".go", ".java", ".rs", ".c", ".cpp", ".sh"):
            continue
        text = read(p)
        if len(text.splitlines()) > 300:
            bad.append("%s 超 300 行" % p.name)
        for pat, label in ((r"\bTODO\b|\bFIXME\b", "TODO"), (r"\bNotImplemented(Error)?\b", "未实现"),
                           (r"^\s*pass\s*$", "空实现 pass")):
            if re.search(pat, text, re.M):
                bad.append("%s:%s" % (p.name, label))
    if bad:
        ng("I.1", "05 含占位实现或超长文件", ";".join(sorted(set(bad))[:6]))
    else:
        ok("I.1", "05 无 TODO/空实现，单文件 ≤300 行")

    readme = impl / "README.md"
    r2 = read(run / "02-验收标准.md")
    ac_ids = [c[0] for c in table_rows(r2) if c and re.fullmatch(r"AC\d+", c[0])]
    if readme.is_file() and ac_ids:
        txt = read(readme)
        miss = [a for a in ac_ids if a not in txt]
        if miss:
            ng("I.2", "05 README 缺 AC→测试映射", ",".join(miss))
        else:
            ok("I.2", "05 README 覆盖全部 AC 映射")
    elif ac_ids:
        ng("I.2", "05 缺 README 映射")


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description="运行目录机械校验")
    ap.add_argument("run", help="run 目录路径")
    ap.add_argument("--stage", default="all", choices=["g1", "g2", "g3", "all"])
    args = ap.parse_args()

    run = Path(args.run).expanduser().resolve()
    if not run.is_dir():
        print("错误: 不是目录 %s" % run)
        return 2

    check_structure(run, args.stage)
    check_word_limits(run)
    check_sections(run)
    if args.stage in ("g1", "all"):
        check_g1(run)
    if args.stage in ("g2", "all"):
        check_g2(run)
    if args.stage in ("g3", "all"):
        check_g3(run)
        check_impl(run)

    width = max(len(r[1]) for r in results)
    for good, cid, desc, detail in results:
        tag = "OK" if good else "NG"
        line = "[%s] %-*s %s" % (tag, width, cid, desc)
        if detail:
            line += "  <- " + detail
        print(line)
    bad = [r for r in results if not r[0]]
    print("")
    print("合计 %d 项，NG %d 项。%s" % (len(results), len(bad),
                                  "门禁可判" if not bad else "门禁不通过，按 gates.md 退回"))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
