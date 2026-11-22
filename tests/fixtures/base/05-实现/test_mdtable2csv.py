#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AC 测试：每条 AC 一个用例。断言到字节/字段级，不做 normalize。

两类用例：
- TestACCommand：严格按 `02-验收标准.md` 原文的命令、夹具名执行（AC 字面可复现）
- TestFailureMode：失败模式与门禁回归（含 r3 盲审发现的 P0/P1）
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "mdtable2csv.py"


def run_path(path, cwd=HERE):
    p = subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True, cwd=str(cwd),
    )
    return p.returncode, p.stdout, p.stderr.decode("utf-8", "replace")


def run_bytes(content):
    tmp = Path(tempfile.mkdtemp()) / "t.md"
    tmp.write_text(content, encoding="utf-8")
    return run_path(tmp)


class TestACCommand(unittest.TestCase):
    """AC 原文指定的夹具必须真实存在，且原文命令必须能跑出原文结果。"""

    def test_fixtures_exist_and_nonempty(self):
        # r3 盲审 P1：t1/t6 缺失、t4 为 0 字节，AC 原文命令无法复现
        for name, min_bytes in [("t1.md", 1), ("t2.md", 1), ("t4.md", 1), ("t6.md", 1)]:
            f = HERE / name
            self.assertTrue(f.exists(), "%s 不存在" % name)
            self.assertGreaterEqual(f.stat().st_size, min_bytes, "%s 为空" % name)

    def test_AC1_basic_table(self):
        rc, out, err = run_path("t1.md")
        self.assertEqual(rc, 0, err)
        self.assertEqual(out, b"a,b\n1,2\n")

    def test_AC2_escaped_pipe(self):
        rc, out, err = run_path("t2.md")
        self.assertEqual(rc, 0, err)
        fields = out.decode("utf-8").split("\n")[0].split(",")
        self.assertEqual(len(fields), 2)
        self.assertEqual(fields[0], "a|b")  # 还原为字面竖线，不保留反斜杠

    def test_AC3_file_not_found(self):
        rc, out, err = run_path("nope.md")
        self.assertEqual(rc, 2)
        self.assertEqual(err.splitlines()[0], "file not found: nope.md")
        self.assertNotIn("Traceback", err)
        self.assertEqual(out, b"")

    def test_AC4_ignore_surrounding_text(self):
        rc, out, err = run_path("t4.md")
        self.assertEqual(rc, 0, err)
        # 字节级断言：3 行 = 表头+2 行数据，首尾无多余空行
        self.assertEqual(out, b"a,b\n1,2\n3,4\n")
        self.assertNotIn(b"# \xe6\x8a\xa5\xe5\x91\x8a", out)

    def test_AC5_header_first(self):
        rc, out, err = run_path("t1.md")
        self.assertEqual(rc, 0, err)
        self.assertEqual(out.decode("utf-8").splitlines()[0], "a,b")

    def test_AC6_no_table(self):
        rc, out, err = run_path("t6.md")
        self.assertEqual(rc, 3)
        self.assertEqual(err.splitlines()[0], "no table found: t6.md")
        self.assertEqual(out, b"")


class TestFailureMode(unittest.TestCase):

    def test_F1_column_mismatch(self):
        rc, out, err = run_bytes("| a | b |\n| --- | --- |\n| 1 |\n")
        self.assertEqual(rc, 4)
        self.assertIn("column count mismatch", err)
        self.assertEqual(out, b"")

    def test_F2_escaped_backslash(self):
        rc, out, _ = run_bytes("| a\\\\b | c |\n| --- | --- |\n")
        self.assertEqual(rc, 0)
        self.assertEqual(out.decode("utf-8").split("\n")[0], "a\\b,c")

    # ---- r3 盲审 P0 回归 ----

    def test_p0_non_utf8_no_traceback(self):
        """P0-1：非 UTF-8 文件不得抛 Traceback，必须给确定性错误与退出码 2。"""
        tmp = Path(tempfile.mkdtemp()) / "gbk.md"
        tmp.write_bytes(b"| \xd6\xd0 | b |\n| --- | --- |\n")
        rc, out, err = run_path(tmp)
        self.assertEqual(rc, 2, "退出码应为 2，实际 %d" % rc)
        self.assertNotIn("Traceback", err)
        self.assertEqual(err.splitlines()[0], "not valid utf-8: %s" % tmp)
        self.assertEqual(out, b"")

    def test_p0_dash_only_data_row_kept(self):
        """P0-2：`| - | - |` 出现在表体是数据行，不得被当作分隔行丢弃。"""
        rc, out, err = run_bytes(
            "| a | b |\n| --- | --- |\n| - | - |\n| : | : |\n| 1 | 2 |\n")
        self.assertEqual(rc, 0, err)
        self.assertEqual(out.decode("utf-8").strip().splitlines(),
                         ["a,b", "-,-", ":,:", "1,2"])

    def test_p0_separator_only_once(self):
        """分隔行只吃表头后紧邻的一行；表体第二次出现必须当数据。"""
        rc, out, err = run_bytes(
            "| h1 | h2 |\n| --- | --- |\n| --- | --- |\n| x | y |\n")
        self.assertEqual(rc, 0, err)
        self.assertEqual(out.decode("utf-8").strip().splitlines(),
                         ["h1,h2", "---,---", "x,y"])

    # ---- r4 盲审 P0 回归 ----

    def test_p0_backslash_before_other_char_preserved(self):
        """P0(r4)：`\\` 后接非 `|`/`\\` 时反斜杠必须保留，不得吞掉。

        `\\d+` -> `d+`、`C:\\temp` -> `C:temp` 是静默数据损坏，
        正则在文档里极常见，Windows 路径更常见。
        """
        tmp = Path(tempfile.mkdtemp()) / "t.md"
        tmp.write_text("| a\\d+ | C:\\temp |\n| --- | --- |\n", encoding="utf-8")
        rc, out, err = run_path(tmp)
        self.assertEqual(rc, 0, err)
        self.assertEqual(out, b"a\\d+,C:\\temp\n")

    def test_p0_backslash_at_end_preserved(self):
        """行尾孤立反斜杠也不得被吞。"""
        tmp = Path(tempfile.mkdtemp()) / "t.md"
        tmp.write_text("| x\\ | y |\n| --- | --- |\n", encoding="utf-8")
        rc, out, err = run_path(tmp)
        self.assertEqual(rc, 0, err)
        self.assertEqual(out, b"x\\,y\n")

    # ---- r4 盲审 P2/P3 回归 ----

    def test_p2_fenced_code_block_skipped(self):
        """P2(r4)：围栏代码块里演示的表格不得被当成真表格。"""
        src = ("# doc\n\n```\n| x | y |\n| --- | --- |\n| 9 | 9 |\n```\n\n"
               "| a | b |\n| --- | --- |\n| 1 | 2 |\n")
        rc, out, err = run_bytes(src)
        self.assertEqual(rc, 0, err)
        self.assertEqual(out, b"a,b\n1,2\n")

    def test_p2_stray_separator_is_not_table(self):
        """P2(r4)：孤立分隔行不构成表格（分隔行不能当表头）。"""
        rc, out, err = run_bytes("| --- | --- |\n")
        self.assertEqual(rc, 3, "应判无表格，实际 rc=%d" % rc)
        self.assertEqual(out, b"")
        self.assertTrue(err.startswith("no table found: "), err)

    def test_p3_mismatch_reports_absolute_line(self):
        """P3(r4)：列数不一致报文件绝对行号，不是表内序号。"""
        tmp = Path(tempfile.mkdtemp()) / "t.md"
        tmp.write_text("正文\n\n| a | b |\n| --- | --- |\n| 1 |\n", encoding="utf-8")
        rc, out, err = run_path(tmp)
        self.assertEqual(rc, 4)
        self.assertEqual(err.splitlines()[0], "column count mismatch at line 5")

    def test_p2_stderr_uses_lf(self):
        """P2(r4)：stderr 也不得带 CR（Windows 默认 CRLF）。"""
        tmp = Path(tempfile.mkdtemp()) / "gbk.md"
        tmp.write_bytes(b"| \xd6\xd0 |\n| --- |\n")
        rc, out, err = run_path(tmp)
        self.assertEqual(rc, 2)
        self.assertNotIn("\r", err)

    def test_p1_directory_error_distinct(self):
        """P1：目录不是文件，错误信息不得误报 file not found。"""
        rc, out, err = run_path(".")
        self.assertEqual(rc, 2)
        self.assertEqual(err.splitlines()[0], "not a regular file: .")
        self.assertNotIn("Traceback", err)

    def test_p1_missing_file_message_exact(self):
        """AC3 措辞在回归中保持不变（补丁不得改已有判据）。"""
        rc, _, err = run_path("nope.md")
        self.assertEqual(err.strip(), "file not found: nope.md")

    # ---- r5 盲审 P1/P2/P3 回归 ----

    def test_p1_unicode_line_separators_do_not_split(self):
        """P1(r5)：`str.splitlines()` 会按 \\x0b/\\f/\\u2028 切行，把表格劈开且 rc=0。

        单元格里含换页符或 Unicode 行分隔符时，后续行会整块丢失，用户无从察觉。
        """
        for ch in ("\x0b", "\x0c", "\u2028", "\u2029"):
            with self.subTest(sep=repr(ch)):
                rc, out, err = run_bytes(
                    "| a%sb | c |\n| --- | --- |\n| 1 | 2 |\n" % ch)
                self.assertEqual(rc, 0, err)
                self.assertEqual(len(out.decode("utf-8").strip().split("\n")), 2,
                                 "单元格含 %r 时行数不对：%r" % (ch, out))

    def test_p2_missing_trailing_pipe_warns(self):
        """P2(r5)：缺尾竖线导致后续行被丢时，必须告警，不许静默。"""
        rc, out, err = run_bytes(
            "| a | b |\n| --- | --- |\n| 1 | 2 |\n| 3 | 4\n| 5 | 6 |\n")
        self.assertEqual(rc, 0, err)
        self.assertEqual(out, b"a,b\n1,2\n")
        self.assertIn("warning:", err)
        self.assertIn("line 4", err)

    def test_p3_separator_cell_count_must_match_header(self):
        """P3-2(r5)：分隔行格数与表头不符时，不得当分隔行吃掉。"""
        rc, out, err = run_bytes("| a | b |\n| --- |\n| 1 | 2 |\n")
        self.assertEqual(rc, 4, "应报列数不一致，实际 rc=%d out=%r" % (rc, out))
        self.assertIn("column count mismatch", err)

    def test_fixture_t3_column_mismatch(self):
        """P3-3(r5)：t3.md 是列数不一致夹具，此前无人引用。"""
        rc, out, err = run_path("t3.md")
        self.assertEqual(rc, 4)
        self.assertEqual(out, b"")
        self.assertIn("column count mismatch", err)

    def test_fixture_t5_crlf(self):
        """P3-3(r5)：t5.md 是 CRLF 夹具，此前无人引用。"""
        rc, out, err = run_path("t5.md")
        self.assertEqual(rc, 0, err)
        self.assertNotIn(b"\r", out)
        self.assertEqual(out, b"a,b\n1,2\n")

    # ---- r6 盲审 P1 回归 ----

    def test_p1_header_missing_trailing_pipe_not_dropped(self):
        """P1(r6)：表头缺尾竖线时不得被丢弃、让数据行升格为表头。

        这是最坏的一类错误：输出是错值，rc=0，stderr 为空，用户无从察觉。
        """
        rc, out, err = run_bytes(
            "| a | b\n| --- | --- |\n| 1 | 2 |\n| 3 | 4 |\n")
        self.assertEqual(rc, 0, err)
        self.assertEqual(out, b"a,b\n1,2\n3,4\n")

    def test_p1_header_missing_pipe_keeps_column_check(self):
        """表头残缺但列数仍要对得上，不可因宽松而放过列数不一致。"""
        rc, out, err = run_bytes("| a | b\n| --- | --- |\n| 1 |\n")
        self.assertEqual(rc, 4, "应报列数不一致，实际 rc=%d out=%r" % (rc, out))
        self.assertIn("column count mismatch", err)


if __name__ == "__main__":
    unittest.main(verbosity=2)
