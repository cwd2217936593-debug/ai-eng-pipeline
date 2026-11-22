---
name: ai-eng-pipeline
description: "把模糊需求带到可交付：先判定领域（软件/硬件/人力/自定义）并实例化对应流水线，再拆需求、定可判真假的验收标准、出方案与路径、产出实体、由独立子代理盲审、判定能否交付。当用户说「帮我做个 XX」「这个需求怎么落地」「评估一下这个功能怎么做」「做个完整方案」「把这个功能从头做完」时使用。不用于：纯概念解释或技术问答、单行改动与改错别字、既有代码的单点 review 咨询、只做 UI 视觉稿、纯聊天。"
agent_created: true
---

# AI 工程流水线

## 1. 用途

把一句口语化的需求，走成一套可验收、可追溯、可回滚的交付物。
与普通"帮我做个东西"的根本区别：**先定"这次要用哪套标准"，再开始干活。**

领域：`software` 软件 / `hardware` 硬件 / `hr` 人力与制度 / `custom` 自定义。
领域只改变"怎么验证"，不改变"必须有验证"。

## 2. 触发与不触发

**触发**：帮我做个 XX / 这个需求怎么落地 / 评估一下这个功能怎么做 / 做个完整方案 / 把这个功能从头做完 / 我想加个功能但没想清楚 / 帮我把这个想法做成能用的东西 / 帮我设计一套制度或流程

**不触发**：解释概念 / 报错怎么修 / 这段代码什么意思 / 单文件小改 / 改文案 / 写周报 / 纯聊天

不确定时：先判级。判为 S 就不开流水线，直接做 + 自检。

## 3. 流程总览（两段）

```
输入：用户口语需求
   |
=== Stage 0 · 领域实例化（AI 用得少，决策最重）===
   |  lead 识别领域 -> 读 domains/<x>.md -> 写 00b-领域实例.md
   |  G0 --否--> 重写 00b（领域错了后面全废）
   |  用户确认
=== Stage 1+ · 施工（按 00b 实例化角色）===
   |
   |  spec 写 01 需求规格 + 02 验收标准   <- 02 前置于方案
   |  G1 --否--> 退回 spec（带失败项+编号+反例）
   |  architect 写 03 方案 + 04 路径
   |  G2 --否--> 退回 architect
   |  builder 写 05 交付实体
   |  reviewer（独立子代理）写 06 盲审
   |  G3 --否--> 退回 builder（同一问题 ≤3 轮）--> 超轮 lead 裁决写 07
   |
交付：能交/不能交 + 每条 AC 证据 + 遗留清单
```

## 4. 每阶段动作

**开工**：`python scripts/init_run.py "<需求原文>" --domain software --root .`
建运行目录与 8 份空壳（含 git init）。

| 阶段 | 动作 | 读哪个 reference |
|---|---|---|
| 0 领域 | 判领域、填 7 槽位、写 `00b`、请用户确认 | `references/core/stage0-instantiate.md` + `domains/<x>.md` |
| 判级 | 判 S/M/L，写 `07` 第 1 节；模糊则升一级 | `references/core/sizing.md` |
| 需求 | 拆 R、写 AC（输入→动作→可观测输出）、划边界、报冲突 | `references/roles/spec.md` + `references/core/contracts.md` §2-3 |
| 方案 | 从 AC 倒推、取舍三段式、失败模式、排步骤 | `references/roles/architect.md` + `references/core/contracts.md` §4-5 |
| 产出 | 按 04 顺序、AC 全覆盖、失败模式落到可观测行为 | `references/roles/builder.md` + `references/core/contracts.md` §6 |
| 盲审 | 起独立子代理，只传 产物/02/00 三个路径 | `references/core/blind-review.md` + `references/roles/reviewer.md` |
| 裁决 | 判门禁、裁冲突、记代价 | `references/roles/lead.md` + `references/core/gates.md` |

五条硬规则，违反即返工：

1. **下游只读文件，不读对话**。产物必须落盘，靠对话传递的理解 5 环后偏差约 40%。
2. **architect 不读 00，reviewer 不读 03**。前者保证"验收标准够不够用"被真检验，后者保证审查不给作者找理由。
3. **lead 只做三件事**：判级、选链、裁决。一干具体活就成幻觉源。
4. **领域不能边干边换**。判错就回 Stage 0，`01`–`03` 作废，`07` 记裁决。
5. **不变量不能因领域而变**。见 `references/core/invariants.md` 的 I1–I9。

机械校验：`python scripts/check_run.py <run目录> --stage g0|g1|g2|g3`
版本与提交：`python scripts/bump.py --run <目录> --type feat --scope build --message "..." --commit`

## 5. 门禁摘要

- **G0 领域**：标识明确 / 5 角色映射齐 / 攻击面 ≥5 条且本领域特有 / 用户已确认
- **G1 需求**：每条 R 可追溯 / 每条 AC 可判真假 / 边界清晰 / 无未决冲突 / 无不可测词
- **G2 方案**：取舍有放弃项+理由+代价 / 失败模式 ≥2 / 每个 AC 有验证路径 / 依赖已确认
- **G3 交付**：盲审 blinded 且 P0=P1=0 / 每条 AC 有证据 / 变更已提交 / 遗留已登记

全部门禁是布尔判断，出现"较好""基本满足"即不通过。
逐条检查项与退回时该带什么：`references/core/gates.md`。产物字段、字数上限、正反例：`references/core/contracts.md`。

## 6. 失败处理

- 门禁不过：按 `references/core/gates.md` 指定位置退回，带"失败项 ID + 对应 R/AC 编号 + 一个具体反例"，不许说"整体重写"。
- 同一问题最多 3 轮。第 3 轮不过 → lead 裁决，写 `07`：谁主张、反方理由、裁决、代价、待复核条件。
- 裁决只有三种：修需求（回 G1）/ 修实现（回 builder）/ 带缺陷交付（写明用户可见影响与代价）。
- 不允许第 4 轮，不允许静默把 P1 降 P2 放行（降级本身是裁决）。
- 环境无子代理：按 `references/core/blind-review.md` 阶梯降级，`REVIEW_MODE` 必须如实标注。**不许把 unblinded 写成 blinded。**
- 审查报告全 0 问题时，必须有 3 个攻击点的实际执行结果，否则视为无效审查。

## 7. 跨平台

纯 Markdown + Python，不依赖特定平台。
其他 AI 入口：`AGENTS.md`（通用）/ `CLAUDE.md`（Claude Code）/ `PROMPT.md`（纯粘贴，给 ChatGPT 类）。
