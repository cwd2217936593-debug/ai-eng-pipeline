# CLAUDE.md

本仓库是一套**不绑定平台的工程流水线**（纯 Markdown + Python），不是代码库。

## 入口

先读 `AGENTS.md`（通用约定），再读 `SKILL.md`（主流程）与 `references/core/invariants.md`（9 条不变量）。

## Claude Code 特有

### 盲审用 Task 工具

```python
Task(
  subagent_type="general-purpose",
  description="独立盲审",
  prompt="""
你是独立审查者，与被审作者零上下文共享。
只能读这三个路径：<交付实体目录>、<02-验收标准.md>、<00-原文.md>
严禁读取 01/03/04/06/07 及任何已有审查报告。
<其余按 references/core/blind-review.md 的模板>
""")
```

Task 子代理有独立上下文，这是最干净的 `blinded` 模式。
不要用"在同一会话里换个角度想想"冒充审查 —— 那会让审查者替作者找理由。

### 文件操作

产物落盘到 `run-YYYYMMDD-NN/`，用 `init_run.py` 初始化。
不要用对话传递中间结论，一律写文件。

### 权限

`scripts/` 里的脚本只读写 `run-` 目录，不碰其他路径。
`init_run.py` 会执行 `git init`，如不需要加 `--no-git`。

## 常见误用

| 误用 | 后果 |
|---|---|
| 跳过 Stage 0 直接拆需求 | 用错领域的验证标准，后面全废 |
| 验收标准写在方案之后 | 设计出"刚好能过"的测试 |
| 自己审查自己的产出 | 审查永远通过，你不知道自己在裸奔 |
| 把结论留在对话里 | 5 环后偏差约 40%，且无法定位 |
| 门禁"基本满足"就放行 | 流程变成表演 |
