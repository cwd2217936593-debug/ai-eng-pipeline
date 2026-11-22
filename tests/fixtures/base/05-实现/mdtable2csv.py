#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mdtable2csv - 把 markdown 文件的第一个表格转成 CSV 输出到 stdout。

退出码：0 成功 / 2 参数或文件读取错误 / 3 无表格 / 4 列数不一致

已知限制：只识别带外层竖线的表格（`| a | b |`）。无外层竖线的写法
（`a | b`）无法与正文中含竖线的普通行区分，不识别。见 README 第 6 节。
"""

import os
import re
import sys

# 合法分隔单元格：可选左对齐冒号 + 至少一个短横 + 可选右对齐冒号
_SEP_CELL = re.compile(r"^:?-+:?$")


def split_row(line):
    """按未转义的竖线切分单元格。

    转义只认两种（与 Markdown 表格的语义一致）：
      `\\|` -> `|`      竖线字面量
      `\\\\` -> `\\`     反斜杠字面量
    其余 `\\x` **保留反斜杠**（`\\d+` 仍是 `\\\\d+`，`C:\\temp` 仍是 `C:\\temp`）。
    早期版本无条件吞掉反斜杠，导致正则与 Windows 路径被静默改写 —— 那是数据损坏。
    """
    s = line.strip()
    n = len(s)
    i = 1 if s.startswith("|") else 0
    cells, buf = [], []
    while i < n:
        ch = s[i]
        if ch == "\\" and i + 1 < n:
            nxt = s[i + 1]
            if nxt in "\\|":
                buf.append(nxt)          # 仅这两种是转义
            else:
                buf.append(ch)           # 其余保留反斜杠原样
                buf.append(nxt)
            i += 2
            continue
        if ch == "|":
            cells.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail or not cells:
        cells.append(tail)
    return cells


def is_separator_row(s):
    """结构判定：每格都形如 `:?-+:?`，且至少一格。"""
    body = s.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    cells = [c.strip() for c in body.split("|")]
    return bool(cells) and all(_SEP_CELL.match(c) for c in cells)


def scan_table(lines):
    """收集第一个表格块，返回 (rows, truncated_at)。

    rows 为 [(行号, 原文), ...]；truncated_at 非 None 表示表格被一行
    "以 | 开头但缺尾部 |"的内容打断 —— 那种情况可能丢了数据，要告警。

    四条结构规则（都是位置/结构判定，不看内容特征）：
    1. 围栏代码块（``` / ~~~）内的内容一律不算表格
    2. 表头行本身不能是分隔行；孤立的分隔行不构成表格
    3. 分隔行只在表头之后紧邻一行生效，且只吃一次
    4. 分隔行的格数必须与表头一致，否则它不是分隔行（会走列数校验报错）
    """
    rows = []
    started = False
    sep_allowed = False  # 仅表头后紧邻的一行可以吃分隔行
    in_fence = False
    truncated_at = None
    for lineno, line in enumerate(lines, start=1):
        s = line.strip()
        if s.startswith("```") or s.startswith("~~~"):
            in_fence = not in_fence
            if started:
                break  # 表格块被围栏打断
            continue
        if in_fence:
            continue
        if s.startswith("|") and s.endswith("|"):
            if not started:
                if is_separator_row(s):
                    # 回看上一行：若它是"以 | 开头但缺尾 |"，那就是残缺表头，补进来。
                    # 不补的话它会被静默丢弃、第一行数据升格为表头 ——
                    # 输出的是错值却报成功，比报错危险得多。
                    prev = lines[lineno - 2].strip() if lineno >= 2 else ""
                    if prev.startswith("|") and not is_separator_row(prev):
                        started = True
                        rows.append((lineno - 1, prev))
                        sep_allowed = False
                        continue
                    continue  # 孤立分隔行不是表格，继续找后面的真表格
                started = True
                rows.append((lineno, s))
                sep_allowed = True
                continue
            if sep_allowed and is_separator_row(s):
                if len(split_row(s)) == len(split_row(rows[0][1])):
                    sep_allowed = False
                    continue
                # 格数不符：不是分隔行，当数据行处理 → 由列数校验报 rc=4
            sep_allowed = False
            rows.append((lineno, s))
        elif started:
            if s.startswith("|"):
                truncated_at = lineno  # 疑似残缺表格行，可能丢数据
            break
    return rows, truncated_at


def join_csv(cells):
    out = []
    for c in cells:
        if "," in c or '"' in c or "\n" in c:
            out.append('"' + c.replace('"', '""') + '"')
        else:
            out.append(c)
    return ",".join(out)


def read_lines(path):
    """读文件为行列表。返回 (lines, err_msg)；err_msg 非 None 表示失败。

    **只用 `\\r\\n` / `\\r` / `\\n` 切行**，不用 `str.splitlines()`：
    后者还会按 `\\x0b \\x0c \\x1c \\x1d \\x1e \\x85 \\u2028 \\u2029` 切，
    单元格里含换页符或 Unicode 行分隔符时，表格会被凭空劈开、后续行全部丢失，
    而且退出码仍是 0 —— 用户完全无从察觉。
    """
    # 目录判定优先：Windows 上 open(目录) 抛 PermissionError，与权限问题混淆
    if os.path.isdir(path):
        return None, "not a regular file: %s" % path
    try:
        with open(path, encoding="utf-8-sig") as f:
            text = f.read()
        return re.split(r"\r\n|\r|\n", text), None
    except FileNotFoundError:
        return None, "file not found: %s" % path
    except IsADirectoryError:
        return None, "not a regular file: %s" % path
    except PermissionError:
        return None, "permission denied: %s" % path
    except UnicodeDecodeError:
        return None, "not valid utf-8: %s" % path
    except OSError as exc:
        return None, "cannot read %s: %s" % (path, exc.strerror or exc)


def main(argv):
    # stdout 与 stderr 都强制 LF：Windows 下 stderr 默认 CRLF，会让判据断言失败
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(newline="\n")
        except (AttributeError, ValueError):
            pass

    if len(argv) != 2:
        sys.stderr.write("usage: mdtable2csv <file.md>\n")
        return 2
    path = argv[1]

    lines, err = read_lines(path)
    if err is not None:
        sys.stderr.write(err + "\n")
        return 2

    rows, truncated_at = scan_table(lines)
    if not rows:
        sys.stderr.write("no table found: %s\n" % path)
        return 3

    if truncated_at is not None:
        # 静默丢行是数据丢失，宁可吵一声也不许无声
        sys.stderr.write(
            'warning: table ended at line %d (leading "|" without trailing "|"), '
            "later rows not converted\n" % truncated_at)

    header = None
    out = []
    for lineno, raw in rows:
        cells = split_row(raw)
        if header is None:
            header = cells
        elif len(cells) != len(header):
            # 报文件绝对行号，不报表内序号 —— 便于直接跳到出错位置
            sys.stderr.write("column count mismatch at line %d\n" % lineno)
            return 4
        out.append(join_csv(cells))

    sys.stdout.write("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
