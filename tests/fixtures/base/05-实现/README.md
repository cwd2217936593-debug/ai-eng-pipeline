# 05 实现说明

- run: run-20261122-01
- 版本: 0.2.0（r3 盲审 P0×2 / P1×3 修复后）

## 1. 运行方式

```
cd 05-实现
python mdtable2csv.py <file.md>      # 输出 CSV 到 stdout
python test_mdtable2csv.py           # 跑全部 AC 与失败模式测试
```

环境：Python 3.9+（用到 `sys.stdout.reconfigure`）。
退出码：0 成功 / 2 参数或文件读取错误 / 3 无表格 / 4 列数不一致。

## 2. AC → 测试映射（直接跑 AC 原文夹具，非临时文件）

| AC | 测试名 | 夹具 | 结果 |
|---|---|---|---|
| AC1 | `test_AC1_basic_table` | t1.md | ok（stdout 字节 === `a,b\n1,2\n`） |
| AC2 | `test_AC2_escaped_pipe` | t2.md | ok（2 字段，首字段 `a\|b`） |
| AC3 | `test_AC3_file_not_found` | nope.md | ok（rc=2，首行 `file not found: nope.md`，无 Traceback） |
| AC4 | `test_AC4_ignore_surrounding_text` | t4.md | ok（3 行，无 `# 报告`） |
| AC5 | `test_AC5_header_first` | t1.md | ok（首行 `a,b`） |
| AC6 | `test_AC6_no_table` | t6.md | ok（rc=3，首行精确等于 `no table found: t6.md`） |

`Ran 27 tests ... OK`。

## 3. 失败模式

| 失败模式 | 代码位置 | 退出码 | stderr 首行 |
|---|---|---|---|
| F1 列数不一致 | `main()` 校验分支 | 4 | `column count mismatch at line N` |
| F2 行尾/连续反斜杠 | `split_row()` | 0 | — |
| F3 CRLF / BOM | `read_lines()`（`utf-8-sig` + `re.split(r"\r\n\|\r\|\n")`） | 0 | — |
| F4 空文件/无表格 | `main()` | 3 | `no table found: <path>` |
| F5 非 UTF-8 | `read_lines()` | 2 | `not valid utf-8: <path>` |
| F6 路径是目录 | `read_lines()`（`os.path.isdir` 前置判定） | 2 | `not a regular file: <path>` |
| F7 权限不足 | `read_lines()` | 2 | `permission denied: <path>` |

所有错误路径均**不打印 Traceback**，退出码与 stderr 首行确定。

## 4. r3 盲审（blinded）问题闭环

| ID | 级别 | 问题 | 修复 | 回归测试 |
|---|---|---|---|---|
| P0-1 | P0 | 非 UTF-8 文件 `UnicodeDecodeError` 未捕获，抛 Traceback | `read_lines()` 捕获 `UnicodeDecodeError` → `not valid utf-8`，rc=2 | `test_p0_non_utf8_no_traceback` |
| P0-2 | P0 | 分隔行按**内容**判定（`set(s) <= set("|-: ")`），表体中 `\| - \| - \|` 被静默丢弃 | 改为**结构+位置**判定：`_SEP_CELL` 校验每格形如 `:?-+:?`，且只吃表头后紧邻一行（`sep_allowed` 标志） | `test_p0_dash_only_data_row_kept`、`test_p0_separator_only_once` |
| P1-1 | P1 | AC 指定夹具缺失：`t1.md`/`t6.md` 不存在、`t4.md` 为 0 字节 | 补齐三份夹具；新增 `test_fixtures_exist_and_nonempty` 守住 | 同左 |
| P1-2 | P1 | 所有 `OSError` 统一报 `file not found`，目录/权限错误被误报 | 分类处理：`isdir` / `IsADirectoryError` / `PermissionError` / `UnicodeDecodeError` / 兜底 `OSError` | `test_p1_directory_error_distinct` |
| P1-3 | P1 | AC6 断言用 `startswith`，弱于判据"stderr 首行精确等于" | 改为 `assertEqual(err.splitlines()[0], ...)` | `test_AC6_no_table` |
| P2-1 | P2 | AC2 期望值 `a\|b` 未区分"保留反斜杠"与"还原为竖线" | 不改 AC（已冻结），按 D4 裁决判定为**还原为字面竖线** | `test_AC2_escaped_pipe` |
| P2-2 | P2 | 无外层竖线的表格写法（`a \| b`）不识别 | 不修，判定为设计取舍（D5）：无外层竖线时无法与正文含竖线的普通行区分 | — |

## 5. r4 盲审（blinded）问题闭环

| ID | 级别 | 问题 | 修复 | 回归测试 |
|---|---|---|---|---|
| P0-1 | P0 | `\` 后接非 `\|` 时反斜杠被丢弃（`\d+`→`d+`、`C:\temp`→`C:temp`），静默数据损坏 | `split_row` 改为只认 `\|` 与 `\\` 两种转义，其余 `\x` 原样保留 | `test_p0_backslash_before_other_char_preserved`、`test_p0_backslash_at_end_preserved` |
| P1-1 | P1 | AC4 断言用 `strip()` 后计数，弱于判据 | 改为字节级 `out == b"a,b\n1,2\n3,4\n"` | `test_AC4_ignore_surrounding_text` |
| P2-1 | P2 | 首行即分隔行时仍被当表头，输出 `---,---` | 首行为分隔行 → 该行不构成表格，继续向后找 | `test_p2_stray_separator_is_not_table` |
| P2-2 | P2 | 围栏代码块（```）里演示的表格被当真表格 | `scan_table` 跟踪围栏状态，围栏内不解析 | `test_p2_fenced_code_block_skipped` |
| P2-3 | P2 | Windows 下 stderr 用 CRLF，stdout 用 LF，不一致 | `stdout` 与 `stderr` 均 `reconfigure(newline="\n")` | `test_p2_stderr_uses_lf` |
| P3-1 | P3 | 列数错误报表内序号，非文件行号 | `scan_table` 返回 `(行号, 原文)`，报绝对行号 | `test_p3_mismatch_reports_absolute_line` |

## 6. r5 盲审（blinded）问题闭环

| ID | 级别 | 问题 | 修复 | 回归测试 |
|---|---|---|---|---|
| P1-1 | P1 | `str.splitlines()` 还会按 `\x0b \x0c \x1c \x1d \x1e \x85 \u2028 \u2029` 切行，单元格含这些字符时表格被劈开、后续行静默丢失，rc 仍为 0 | 改用 `re.split(r"\r\n|\r|\n", text)`，只认三种真实行尾 | `test_p1_unicode_line_separators_do_not_split`（4 个分隔符各测一次） |
| P2-1 | P2 | 表体中缺尾竖线的行导致后续行被 `break` 丢弃，无任何提示 | `scan_table` 返回 `truncated_at`，`main` 向 stderr 打 `warning: table ended at line N ...`（rc 仍 0，stdout 不受污染） | `test_p2_missing_trailing_pipe_warns` |
| P3-1 | P3 | README 写 `Ran 14 tests` 与实测不符 | 已更新为 25 | — |
| P3-2 | P3 | 分隔行判定不与表头比格数，`\| a \| b \|` 后跟 `\| --- \|` 会被当分隔行吃掉 | 分隔行格数须等于表头格数，否则按数据行处理 → 走列数校验报 rc=4 | `test_p3_separator_cell_count_must_match_header` |
| P3-3 | P3 | 夹具 `t3.md`、`t5.md` 无人引用 | 各补一条用例 | `test_fixture_t3_column_mismatch`、`test_fixture_t5_crlf` |

## 7. r6 盲审（blinded）问题闭环

| ID | 级别 | 问题 | 修复 | 回归测试 |
|---|---|---|---|---|
| P1-1 | P1 | 表头缺尾竖线（`\| a \| b`）被静默丢弃，第一行数据升格为表头 —— **输出错值且 rc=0、stderr 为空**，是最坏的一类错误 | 扫到分隔行时回看上一行：若以 `\|` 开头且非分隔行，补作表头（`scan_table`） | `test_p1_header_missing_trailing_pipe_not_dropped`、`test_p1_header_missing_pipe_keeps_column_check` |
| P3-1 | P3 | README 的 F3 行仍写 `splitlines`，与实际不符 | 已改为 `re.split(r"\r\n\|\r\|\n")` | — |
| P3-2 | P3 | 单元格含控制字符时不按 CSV 规范加引号 | 不修：AC 未要求，且加引号会改变 stdout 字节 | 已写入已知限制 |
| P3-3 | P3 | UNC 路径 `\\srv\share` 输出为 `\srv\share` | 不修：与 CommonMark「反斜杠只转义标点」一致，是正确行为 | 已写入已知限制 |

## 8. 第 1 轮（unblinded）问题闭环

| ID | 级别 | 修复 |
|---|---|---|
| I1 | P0 | `split_row` 改为逐字符状态机，`\` 后一字符无条件入 buf |
| I2 | P0 | 文件读取加异常处理，输出 `file not found: <path>`，exit 2 |
| I3 | P1 | AC2 测试改为断言字段数=2 且首字段内容 |
| I4 | P1 | `sys.stdout.reconfigure(newline="\n")`，AC1 改为字节级断言 |
| I5 | P2 | 增加表头列数校验，exit 4 |

## 9. 已知限制

1. **只识别带外层竖线的表格**（`| a | b |`）。无外层竖线写法（`a | b`）不识别，理由见 D5。
2. **表头可缺尾竖线**（`| a | b` 后跟分隔行会被正确识别），但**表体行不行** —— 表体缺尾竖线会被当表格结束并打 warning。
3. **只输出第一个表格**，多表场景不覆盖（AC 未要求）。
4. **表头后必须紧跟分隔行**。若表头后没有分隔行，同宽的行仍会被当数据 —— 宽松解析，不误报，但可能把正文行并入。
5. 不处理跨行单元格、单元格内换行、HTML 标签混排。
6. 围栏代码块识别只认行首 ``` / ~~~，不处理缩进围栏与嵌套围栏。
7. `permission denied` 分支在 Windows 管理员账号下难以构造，未实测（`not a regular file` 已实测）。
8. 单元格含 `\x0b`/`\u2028` 等控制字符时原样写入 stdout，不按 CSV 规范加引号（AC 未要求）。
9. UNC 路径 `\\srv\share` 输出 `\srv\share`：与 CommonMark「反斜杠只转义 `` `*_{}[]()#+-.!| `` 」一致，属规范行为而非缺陷。
