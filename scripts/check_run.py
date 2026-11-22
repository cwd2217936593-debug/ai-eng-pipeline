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
    "00c-领域取证.md": 1500,
    "00d-场景工况.md": 900,
    "01-需求规格.md": 1200,
    "02-验收标准.md": 900,
    "03-架构方案.md": 1500,
    "04-实施路径.md": 800,
    "06-盲审报告.md": 1000,
    "07-裁决记录.md": 600,
    "08-追溯矩阵.md": 1000,
}

BLACKLIST = ["好用", "易用", "友好", "高效", "快速", "稳定", "健壮", "合理", "优雅",
             "灵活", "尽量", "适当", "较好", "基本满足", "等等", "若干", "大量"]

REQUIRED_SECTIONS = {
    "00c-领域取证.md": ["证据台账", "未取证清单", "架构适配假设", "取证能力"],
    "00d-场景工况.md": ["场景八槽位", "工况参数", "设计约束", "假设登记"],
    "01-需求规格.md": ["需求清单", "范围边界", "冲突与未决", "假设"],
    "02-验收标准.md": ["判据表"],
    "03-架构方案.md": ["取舍记录", "失败模式", "依赖", "验证路径"],
    "04-实施路径.md": ["步骤"],
    "06-盲审报告.md": ["读过的文件", "攻击点", "问题清单", "AC 证据核对"],
    "07-裁决记录.md": ["判级", "门禁判定"],
    "08-追溯矩阵.md": ["矩阵", "分层覆盖", "孤儿统计"],
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


def split_md_row(line: str) -> list:
    """按未转义的 | 切分表格行；\\| 视为单元格内容的一部分。"""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells, buf, i = [], [], 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            buf.append("|")          # 转义竖线还原为普通字符
            i += 2
            continue
        if ch == "|":
            cells.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
        i += 1
    cells.append("".join(buf).strip())
    return cells


def table_rows(text: str) -> list:
    """取出所有 markdown 表格行，返回单元格列表（已 strip）。"""
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("|") and s.count("|") >= 2:
            if re.match(r"^\|[\s:\-|]+\|$", s):
                continue  # 分隔行
            rows.append(split_md_row(s))
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


# ---------------------------------------------------------------- G0 领域门禁

ROLES = ("lead", "spec", "architect", "builder", "reviewer")
DOMAINS = ("software", "hardware", "hr", "custom")


def check_g0(run: Path) -> None:
    """Stage 0 领域实例的机械可判部分（G0.1/0.3/0.6/0.8）。"""
    p = run / "00b-领域实例.md"
    if not (p.is_file() and p.stat().st_size > 0):
        ng("G0.0", "缺 00b-领域实例.md（Stage 0 未做，不许进入 Stage 1）")
        return
    ok("G0.0", "存在 00b-领域实例.md")

    text = p.read_text(encoding="utf-8", errors="replace")

    m = re.search(r"`domain`\s*[:：]\s*`?([A-Za-z]+)`?", text) or \
        re.search(r"domain\s*[:：]\s*`?([A-Za-z]+)`?", text)
    dom = (m.group(1).lower() if m else "")
    if dom in DOMAINS:
        ok("G0.1", "domain = %s" % dom)
    else:
        ng("G0.1", "domain 不合法或未填 <- %r（应为 software/hardware/hr/custom）" % dom)

    found = {}
    for role in ROLES:
        row = re.search(r"^\|\s*%s\s*\|(.+)$" % role, text, re.M)
        if row:
            found[role] = row.group(1).split("|")[0].strip()
    missing = [r for r in ROLES if is_blank(found.get(r, ""))]
    if missing:
        ng("G0.3", "角色映射缺或未填 <- %s" % ", ".join(missing))
    else:
        ok("G0.3", "5 个角色均已映射")
        if found.get("reviewer") == found.get("builder"):
            ng("G0.3b", "reviewer 与 builder 同名 <- %s（审查不得由生产者兼任）" % found["reviewer"])
        else:
            ok("G0.3b", "reviewer 与 builder 不同")

    sec = re.search(r"##\s*5\.[^\n]*\n(.*?)(?=\n##\s|\Z)", text, re.S)
    if not sec:
        ng("G0.6", "找不到第 5 节「攻击面」")
    else:
        items = [i for i in re.findall(r"^\s*\d+\.\s*(\S.*)$", sec.group(1), re.M)
                 if not is_blank(i.strip())]
        if len(items) >= 5:
            ok("G0.6", "攻击面 %d 条" % len(items))
        else:
            ng("G0.6", "攻击面不足 5 条 <- 现有 %d 条（本领域特有，不得照抄）" % len(items))

    if re.search(r"- \[[xX]\]\s*G0\.8", text):
        ok("G0.8", "用户已确认（G0.8 已勾选）")
    else:
        ng("G0.8", "G0.8 未勾选：领域须经用户确认后才能进入 Stage 1")

    check_g09(run, dom)


def _section_body(text: str, keyword: str):
    """取某个标题（2-4 级）下的正文，止于下一个任意级别标题。"""
    m = re.search(r"#{2,4}[^\n]*" + re.escape(keyword) + r"[^\n]*\n(.*?)(?=\n#{1,4}\s|\Z)",
                  text, re.S)
    return m.group(1) if m else None


def _section_rows(text: str, keyword: str):
    """取某节下 markdown 表格的数据行（去掉表头与分隔行，过滤空模板行）。"""
    body = _section_body(text, keyword)
    if body is None:
        return None
    lines = [l.strip() for l in body.splitlines() if l.strip().startswith("|")]
    if len(lines) < 2:
        return []
    rows = []
    for line in lines[1:]:
        cells = split_md_row(line)
        if cells and all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
            continue
        if all(is_blank(c) for c in cells):
            continue
        rows.append(cells)
    return rows


def _has_real_ac(text: str) -> bool:
    """判据表里是否已有真正填写过的 AC 行（空模板行不算）。"""
    for cells in _section_rows(text, "判据表") or []:
        if len(cells) >= 4 and re.match(r"AC[\w-]+", cells[0]) \
                and not is_blank(cells[2]) and not is_blank(cells[3]):
            return True
    return False


def check_g09(run: Path, dom: str) -> None:
    """陌生领域取证门禁（仅 domain=custom 时生效）。"""
    if dom != "custom":
        ok("G0.9", "不适用（domain=%s，走预设领域包）" % (dom or "未判"))
        return

    p = run / "00c-领域取证.md"
    if not (p.is_file() and p.stat().st_size > 0):
        ng("G0.9.0", "domain=custom 但缺 00c-领域取证.md（陌生领域未取证，不许进 Stage 1）")
        return
    ok("G0.9.0", "存在 00c-领域取证.md")

    text = p.read_text(encoding="utf-8", errors="replace")

    # G0.9.1 四节齐全
    need = ("证据台账", "未取证清单", "架构适配假设", "取证能力")
    miss = [k for k in need if _section_body(text, k) is None]
    if miss:
        ng("G0.9.1", "00c 缺节 <- %s" % "、".join(miss))
    else:
        ok("G0.9.1", "四节齐全（台账/未取证/适配假设/取证能力）")

    # G0.9.2 台账有数据且等级合法
    rows = _section_rows(text, "证据台账") or []
    if not rows:
        ng("G0.9.2", "证据台账无数据行（一份为空台账的取证等于没取证）")
    else:
        bad = []
        for cells in rows:
            lv = cells[1] if len(cells) > 1 else ""
            if not re.match(r"E[0-3]\b", lv):
                bad.append(lv or "(空)")
        if bad:
            ng("G0.9.2", "台账等级不合法 <- %s（只允许 E0/E1/E2/E3）" % ", ".join(bad[:3]))
        else:
            ok("G0.9.2", "台账 %d 行，等级均合法" % len(rows))

    # G0.9.3 E1 必须可核验（含条号或标准年份）
    e1 = [c for c in rows if len(c) > 1 and c[1].startswith("E1")]
    if not e1:
        ng("G0.9.3", "无 E1 证据：陌生领域的 AC 判据必须能追到可核验标准")
    else:
        weak = [c[0] for c in e1
                if not (re.search(r"第\s*[\d.]+\s*条", " ".join(c)) or re.search(r"(19|20)\d{2}", " ".join(c)))]
        if weak:
            ng("G0.9.3", "E1 缺条号或年份 <- %s（写不出条号应降级为 E2）" % ", ".join(weak[:3]))
        else:
            ok("G0.9.3", "E1 证据 %d 条，均可核验" % len(e1))

    # G0.9.4 未取证清单非空（诚实性检查）
    unv = _section_rows(text, "未取证清单")
    if unv is None:
        ng("G0.9.4", "找不到未取证清单")
    elif not unv:
        ng("G0.9.4", "未取证清单为空：陌生领域必然存在未核实的推测，空清单说明取证在自欺")
    else:
        ok("G0.9.4", "未取证清单 %d 条" % len(unv))

    # G0.9.5 取证能力声明（未替换的 <占位符> 视为未填）
    c04 = _section_body(text, "取证能力") or ""
    m = re.search(r"取证能力\s*[:：]\s*([^\n]+)", c04)
    cap = m.group(1).strip() if m else ""
    if not cap or "<" in cap or "未填" in cap or "待定" in cap:
        ng("G0.9.5", "未声明取证能力 <- %r（须写明 联网+知识库/仅联网/仅知识库/无）" % cap[:30])
    elif re.fullmatch(r"无[。.]?", cap):
        # 只看「未覆盖」字段，不在全文搜关键词 —— 模板本身含"用户已接受豁免"字样，全文搜会假通过
        m2 = re.search(r"未覆盖\s*[:：]\s*([^\n]+)", c04)
        uncov = m2.group(1).strip() if m2 else ""
        if "<" not in uncov and "用户已接受豁免" in uncov and "原话" in uncov:
            ok("G0.9.5", "取证能力=无，用户豁免已记录")
        else:
            ng("G0.9.5", "取证能力为『无』但未覆盖字段未记录用户豁免原话（不许把推测当规范用）")
    else:
        ok("G0.9.5", "取证能力已声明 <- %s" % cap[:30])

    # G0.9.6 证据引用一致性（AC 尚未写时不判，由 G1 阶段复查）
    ac = run / "02-验收标准.md"
    if ac.is_file():
        atext = ac.read_text(encoding="utf-8", errors="replace")
        if not _has_real_ac(atext):
            ok("G0.9.6", "02 尚未写 AC（进入 Stage 1 后由 G1 复查证据引用）")
        elif re.search(r"\[E3[-\]]", atext):
            ng("G0.9.6", "02 的判据里出现 [E3]（模型推测不得作验收判据）")
        else:
            ids = set(re.findall(r"\|\s*(EV-\d+)\s*\|", text))
            refs = set(re.findall(r"(EV-\d+)", atext))
            ghost = sorted(refs - ids)
            if ghost:
                ng("G0.9.6", "02 引用了不存在的证据 <- %s" % ", ".join(ghost[:5]))
            elif not refs:
                ng("G0.9.6", "02 的 AC 判据未引用任何 EV 编号（陌生领域判据必须可溯源）")
            else:
                ok("G0.9.6", "AC 判据证据引用一致（%d 处）" % len(refs))


# ---------------------------------------------------------------- G0.10 场景门禁

SC_IDS = ("SC1", "SC2", "SC3", "SC4", "SC5", "SC6", "SC7", "SC8")
PLACEHOLDER = ("待定", "视情况", "根据实际", "待确认", "待补充", "参考行业", "结合具体")
# N/A 必须带理由：N/A: <理由>
NA_OK = re.compile(r"^N/?A\s*[:：\-]\s*\S{2,}")


def check_g010(run: Path) -> None:
    """场景门禁（G0.10.1-0.10.8）。参考 references/core/scenario.md。"""
    p = run / "00d-场景工况.md"
    if not (p.is_file() and p.stat().st_size > 0):
        ng("G0.10.0", "缺 00d-场景工况.md（场景未定，不许进 Stage 1 —— I11）")
        return
    ok("G0.10.0", "存在 00d-场景工况.md")
    text = p.read_text(encoding="utf-8", errors="replace")

    # 0.10.1 八槽位
    rows = _section_rows(text, "场景八槽位") or []
    got = {}
    for cells in rows:
        if cells and cells[0].strip().upper() in SC_IDS:
            got[cells[0].strip().upper()] = cells[2] if len(cells) > 2 else ""
    missing = [s for s in SC_IDS if s not in got]
    if missing:
        ng("G0.10.1", "槽位缺行 <- %s" % ", ".join(missing))
    else:
        bad = []
        for s in SC_IDS:
            v = got[s].strip()
            if not v:
                bad.append("%s 空" % s)
            elif v.startswith("N/A") or v.startswith("NA"):
                if not NA_OK.match(v):
                    bad.append("%s N/A 无理由" % s)
            elif any(w in v for w in PLACEHOLDER):
                bad.append("%s 占位「%s」" % (s, v[:10]))
        if bad:
            ng("G0.10.1", "槽位未给具体值 <- %s" % "; ".join(bad[:4]))
        else:
            ok("G0.10.1", "SC1-SC8 均已给具体值")

    # 0.10.2 OP 表（至少 3 行含数值；其余可为枚举型，但须标来源）
    ops = _section_rows(text, "工况参数") or []
    bad_op, numeric = [], 0
    for cells in ops:
        val = cells[2] if len(cells) > 2 else ""
        src = cells[3] if len(cells) > 3 else ""
        if not val.strip():
            bad_op.append("%s 无值" % (cells[0] if cells else "?"))
        elif not src.strip():
            bad_op.append("%s 未标来自哪个 SC" % cells[0])
        elif re.search(r"\d", val):
            numeric += 1
    if len(ops) < 3:
        ng("G0.10.2", "OP 不足 3 行 <- 现有 %d 行" % len(ops))
    elif bad_op:
        ng("G0.10.2", "OP 缺值或缺来源 <- %s" % "; ".join(bad_op[:4]))
    elif numeric < 3:
        ng("G0.10.2", "OP 含数值的不足 3 行 <- 现有 %d 行（定性描述不是工况参数）" % numeric)
    else:
        ok("G0.10.2", "OP %d 行（含数值 %d 行），来源齐全" % (len(ops), numeric))

    # 0.10.3 DC 表挂来源（RULE-/EV-；纯项目自定约束可挂 SC#，但数值型不行）
    dcs = _section_rows(text, "设计约束") or []
    NUMERIC = re.compile(r"\d+\s*(mm|cm|℃|°C|%|h|s|min|N·?m|N|Hz|V|A|kg|MPa|次|线)")
    no_src = []
    for cells in dcs:
        src = cells[2] if len(cells) > 2 else ""
        txt = cells[1] if len(cells) > 1 else ""
        has_std = bool(re.search(r"RULE-|EV-", src))
        has_sc = bool(re.search(r"SC\d", src))
        if not (has_std or has_sc):
            no_src.append(cells[0] if cells else "?")
        elif has_sc and not has_std and NUMERIC.search(txt):
            no_src.append("%s 数值型约束只挂 SC" % cells[0])
    if len(dcs) < 3:
        ng("G0.10.3", "DC 不足 3 行 <- 现有 %d 行（经验值不算设计约束）" % len(dcs))
    elif no_src:
        ng("G0.10.3", "DC 未挂 RULE-/EV- <- %s" % ", ".join(no_src[:5]))
    else:
        ok("G0.10.3", "DC %d 行均挂判据来源" % len(dcs))

    # 0.10.4 DC 有落点 DF
    no_df = [c[0] for c in dcs if len(c) < 5 or is_blank(c[4])]
    if dcs and no_df:
        ng("G0.10.4", "DC 无落点 DF <- %s" % ", ".join(no_df[:5]))
    elif dcs:
        ok("G0.10.4", "每条 DC 均有落点 DF")

    # 0.10.5/0.10.6 假设登记
    ah = _section_rows(text, "假设登记") or []
    bad_ah = []
    for cells in ah:
        if len(cells) < 7:
            bad_ah.append("%s 列不足 7" % cells[0])
            continue
        lv, cost, who, redo = cells[2], cells[4], cells[5], cells[6]
        if not re.match(r"E[0-3]", lv.strip()):
            bad_ah.append("%s 依据等级非法" % cells[0])
        elif not ("偏保守" in cost or "偏冒险" in cost or "无影响" in cost):
            bad_ah.append("%s 代价未写方向" % cells[0])
        elif is_blank(who) or is_blank(redo):
            bad_ah.append("%s 缺谁确认/返工点" % cells[0])

    level = "M"
    r7 = read(run / "07-裁决记录.md")
    m = re.search(r"级别\s*[:：]\s*\**\s*([SML])\b", r7)
    if m:
        level = m.group(1)
    cap = {"S": 2, "M": 5, "L": 8}[level]

    if bad_ah:
        ng("G0.10.5", "假设表不合格 <- %s" % "; ".join(bad_ah[:4]))
    elif ah:
        ok("G0.10.5", "假设 %d 条，四列齐" % len(ah))
    else:
        gap = re.search(r"输入缺口[^\n]*[:：]\s*([^\n]*)", text)
        if gap and gap.group(1).strip():
            ok("G0.10.5", "无假设，且已声明输入缺口 <- %s" % gap.group(1).strip()[:20])
        else:
            ng("G0.10.5", "无假设表也未声明「输入缺口: 无」（不许留空当无事）")

    if len(ah) > cap:
        ng("G0.10.6", "假设 %d 条超 %s 级上限 %d <- 需求没聊清楚，回去问" % (len(ah), level, cap))
    else:
        ok("G0.10.6", "假设 %d 条 ≤ %s 级上限 %d" % (len(ah), level, cap))

    # 0.10.7 场景标签
    m = re.search(r"场景标签[^\n]*", text)
    tag = m.group(0) if m else ""
    if tag.count("×") >= 3:
        ok("G0.10.7", "场景标签已给出（四域）")
    else:
        ng("G0.10.7", "场景标签缺失或未用四域组合 <- %r" % tag[:40])

    # 0.10.8 用户确认
    if re.search(r"- \[[xX]\]\s*G0\.10\.8", text):
        ok("G0.10.8", "用户已确认场景（G0.10.8 已勾选）")
    else:
        ng("G0.10.8", "G0.10.8 未勾选：场景须经用户确认后才能进入 Stage 1")


# ---------------------------------------------------------------- 结构

def check_structure(run: Path, stage: str) -> None:
    need = ["00-原文.md"]
    if stage in ("g0", "g1", "all"):
        need += ["00d-场景工况.md"]
    if stage in ("g1", "all"):
        need += ["01-需求规格.md", "02-验收标准.md"]
    if stage in ("g2", "all"):
        need += ["03-架构方案.md", "04-实施路径.md"]
    if stage in ("g3", "all"):
        need += ["06-盲审报告.md", "07-裁决记录.md", "08-追溯矩阵.md"]
    for name in need:
        p = run / name
        cid = "S." + name.split("-")[0].split(".")[0]
        if p.is_file() and p.stat().st_size > 0:
            ok(cid, "存在 %s" % name)
        else:
            ng(cid, "缺失或为空 %s" % name)

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

    # G1.8 需求来源必须能追到工程来源（I11）：SC/OP、RULE-、EV-、[假设A#]
    # 仅当 00d 存在时启用：没有场景文件说明是 v2 老 run，不追溯加严
    SRC_OK = re.compile(r"00|SC\d|OP\d|RULE-|EV-|\[?\s*A\d+\s*\]?|假设")
    has_scene = (run / "00d-场景工况.md").is_file()
    unsourced = []
    for cells in table_rows(r1):
        if cells and re.fullmatch(r"R\d+", cells[0]):
            src = cells[2] if len(cells) > 2 else ""
            if src.strip() and not SRC_OK.search(src):
                unsourced.append("%s:%s" % (cells[0], src[:12]))
    if not has_scene:
        ok("G1.8", "不适用（无 00d，按 v2 口径）")
    elif unsourced:
        ng("G1.8", "需求来源非工程来源 <- %s" % "; ".join(unsourced[:4]))
    elif req_ids:
        ok("G1.8", "需求来源均可追到 SC/OP/RULE/EV/假设")


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

    # G2.9 规则包引用（仅 00d 存在时启用，避免加严老 run）
    if not (run / "00d-场景工况.md").is_file():
        ok("G2.9", "不适用（无 00d，按 v2 口径）")
        ok("G2.10", "不适用（无 00d，按 v2 口径）")
        return

    seg_rp = _section_body(r3, "规则包") or ""
    packs = re.findall(r"@\d+\.\d+\.\d+", seg_rp)  # 表格里 pack 与版本常分两列
    if not seg_rp.strip():
        ng("G2.9", "03 缺「规则包引用」段（每条 DC 必须挂 RULE-/EV-）")
    elif not packs:
        ng("G2.9", "规则包未锁版本 <- 需写 pack@x.y.z，不许 latest 或裸名")
    elif re.search(r"@latest|@\*", seg_rp):
        ng("G2.9", "规则包版本写 latest/*（不可重现）")
    else:
        draft = read(run / "00d-场景工况.md")
        declared = set(re.findall(r"(RULE-[A-Za-z0-9\-]+)", draft))
        cited = set(re.findall(r"(RULE-[A-Za-z0-9\-]+)", r3))
        ghost = sorted(cited - declared - set())
        if ghost and not (run.parent / "rulepacks").is_dir():
            # 00d 里没声明、也找不到包文件：只提示不判否（包可能在 skill 目录）
            ok("G2.9", "规则包 %d 个已锁版本；%d 条 RULE 引用待核对" % (len(packs), len(cited)))
        else:
            ok("G2.9", "规则包 %d 个已锁版本，RULE 引用 %d 处" % (len(packs), len(cited)))

    # G2.10 分层落点（L2/L3/L4 都要写到，允许合并声明）
    both = r3 + "\n" + r4
    miss_layer = [lv for lv in ("L2", "L3", "L4") if not re.search(r"\b%s\b" % lv, both)]
    if miss_layer:
        ng("G2.10", "分层缺落点 <- %s（可合并，不可省略）" % ", ".join(miss_layer))
    elif not re.search(r"\bL5\b|05-实现", r4):
        ng("G2.10", "04 未映射到 L5（实现）")
    elif not re.search(r"\bL6\b|验证|测试", r4):
        ng("G2.10", "04 未映射到 L6（验证）")
    else:
        ok("G2.10", "L2-L4 有落点，04 覆盖 L5/L6")


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

    # 逐级别取数：有 `P0=2` 这类显式写法就信它，没有就数问题清单表里的行
    levels = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    rows_cache = table_rows(r6)
    for lv in levels:
        mm = re.search(lv + r"\s*[=:：]\s*(\d+)", r6)
        if mm:
            levels[lv] = int(mm.group(1))
        else:
            levels[lv] = sum(1 for cells in rows_cache
                             if any(c.strip() == lv for c in cells))
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
        seg_atk = section(r6, "攻击点")
        # 攻击点可以是表格行、加粗小标题、三级标题或编号列表 —— 不能只认表格
        atk = len([c for c in table_rows(seg_atk)
                   if c and len(c) > 1 and not is_blank(c[1])])
        atk = max(atk, len(re.findall(r"^\s*(?:\*\*[^*\n]{1,30}\*\*|[A-Z]?\d+[\.、)）]\s|#{3,4}\s)", seg_atk, re.M)))
        # 兜底：节内有 ≥3 处真实执行痕迹（命令行或退出码），也算有攻击过程
        if atk < 3 and len(re.findall(r"rc=|\$ |Traceback|>>>", seg_atk)) >= 3:
            atk = 3
        if atk >= 3:
            ok("G3.7", "零问题但有 %d 个攻击点实证" % atk)
        else:
            ng("G3.7", "零问题且攻击点不足 3 个", "判为无效审查")
    else:
        ok("G3.7", "有问题清单，非空审查（P0=%d P1=%d P2=%d）"
           % (levels["P0"], levels["P1"], levels["P2"]))

    if re.search(r"G1\s*\|", r7) or "G1" in r7:
        ok("G3.5", "07 有门禁判定记录")
    else:
        ng("G3.5", "07 无门禁判定记录")
    if re.search(r"[Ss]/[Mm]/[Ll]|级别[:：]\s*(S|M|L)", r7):
        ok("G3.6", "07 有判级记录")
    else:
        ng("G3.6", "07 缺判级记录", "lead 第一个动作是判级")

    # G3.8 追溯矩阵闭合（仅 00d 存在时启用）
    if not (run / "00d-场景工况.md").is_file():
        ok("G3.8", "不适用（无 00d，按 v2 口径）")
        ok("G3.9", "不适用（无 00d，按 v2 口径）")
        return

    r8 = read(run / "08-追溯矩阵.md")
    if not r8.strip():
        ng("G3.8", "缺 08-追溯矩阵.md（全链路未闭合）")
    else:
        orph = _section_rows(r8, "孤儿统计") or []
        nz, closed = [], []
        for cells in orph:
            num = cells[1] if len(cells) > 1 else ""
            tail = " ".join(cells[2:]) if len(cells) > 2 else ""
            m = re.search(r"\d+", num)
            if m and int(m.group()) > 0:
                dm = re.search(r"D\d+", tail)
                if dm and re.search(re.escape(dm.group()) + r"\s*\|", r7):
                    # 已裁决：门禁仍判否（I5 布尔），但交付口径为「带缺陷交付」
                    nz.append("%s=%s@%s" % (cells[0][:8], m.group(), dm.group()))
                else:
                    nz.append("%s=%s" % (cells[0][:8], m.group()))
        layer = _section_rows(r8, "分层覆盖") or []
        miss_l = []
        for lv in ("L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7"):
            row = [c for c in layer if c and c[0].startswith(lv)]
            if not row or len(row[0]) < 2 or is_blank(row[0][1]):
                miss_l.append(lv)
        if nz:
            ng("G3.8", "追溯矩阵有孤儿 <- %s（带 D# 者结论须标「带缺陷交付」）" % ", ".join(nz))
        elif miss_l:
            ng("G3.8", "分层覆盖缺落点 <- %s" % ", ".join(miss_l))
        elif len(orph) < 5:
            ng("G3.8", "孤儿统计不足 5 类（需求/设计/未验/无源参数/场景）")
        else:
            ok("G3.8", "五类孤儿为 0，L0-L7 全覆盖")

    # G3.9 无绕过痕迹
    bad = []
    if re.search(r"VOID-", r7):
        bad.append("07 有未处置的 VOID 记录")
    m = re.search(r"级别\s*[:：]\s*\**\s*S\b", r7)
    r1 = read(run / "01-需求规格.md")
    n_r = len({c[0] for c in table_rows(r1) if c and re.fullmatch(r"R\d+", c[0])})
    if m and n_r > 6:
        bad.append("判 S 但有 %d 条需求（疑似 B7 拆小逃避）" % n_r)
    ds = [c for c in table_rows(r7) if c and re.fullmatch(r"D\d+", c[0])]
    incomplete = [c[0] for c in ds if sum(1 for x in c[1:] if not is_blank(x)) < 4]
    if incomplete:
        bad.append("裁决不完整 %s（需 主张/理由/裁决/代价/复核）" % ",".join(incomplete[:3]))
    if bad:
        ng("G3.9", "存在绕过痕迹 <- %s" % "; ".join(bad))
    else:
        ok("G3.9", "无 VOID/无拆小逃避/裁决完整")


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
        # "空实现"只认"函数/类体里只有 pass"，不认 except 分支里的 legit pass
        for pat, label in ((r"\bTODO\b|\bFIXME\b", "TODO"),
                           (r"\braise\s+NotImplementedError\b", "未实现"),
                           (r"(?:def\s+\w+\([^)]*\)[^\n]*:|class\s+\w+[^\n]*:)\s*\n\s*(?:#[^\n]*\n\s*)*pass\s*(?:\n|$)", "空实现 pass")):
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
    ap.add_argument("--stage", default="all", choices=["g0", "g1", "g2", "g3", "all"])
    args = ap.parse_args()

    run = Path(args.run).expanduser().resolve()
    if not run.is_dir():
        print("错误: 不是目录 %s" % run)
        return 2

    check_structure(run, args.stage)
    if args.stage in ("g0", "all"):
        check_g0(run)
        check_g010(run)
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
