---
name: ai-eng-pipeline
description: "把模糊需求带到可交付：先判定领域（软件/硬件/人力/自定义）并实例化对应流水线，再拆需求、定可判真假的验收标准、出方案与路径、产出实体、由独立子代理盲审、判定能否交付。当用户说「帮我做个 XX」「这个需求怎么落地」「评估一下这个功能怎么做」「做个完整方案」「把这个功能从头做完」时使用。不用于：纯概念解释或技术问答、单行改动与改错别字、既有代码的单点 review 咨询、只做 UI 视觉稿、纯聊天。"
agent_created: true
---

# AI 工程流水线

## 1. 用途

把一句口语化的需求，走成一套可验收、可追溯、可回滚的交付物。
与普通"帮我做个东西"的根本区别：**先定"这次要用哪套标准"，再开始干活。**

领域：`software` 软件 / `hardware` 硬件 / `hr` 人力与制度 / `custom` 陌生领域。
领域只改变"怎么验证"，不改变"必须有验证"。
**陌生领域（建筑、机械、医疗、法律、物流…）不是不支持，是要先取证**：编造的行业规范不会有任何东西报错，所以判据必须追到证据编号。

## 2. 触发与不触发

**触发**：帮我做个 XX / 这个需求怎么落地 / 评估一下这个功能怎么做 / 做个完整方案 / 把这个功能从头做完 / 我想加个功能但没想清楚 / 帮我把这个想法做成能用的东西 / 帮我设计一套制度或流程

**不触发**：解释概念 / 报错怎么修 / 这段代码什么意思 / 单文件小改 / 改文案 / 写周报 / 纯聊天

不确定时：先判级。判为 S 就不开流水线，直接做 + 自检。

## 3. 流程总览（两段）

```
输入：用户口语需求
   |
=== Stage 0 · 元设计（AI 用得少，决策最重）===
   |  lead 识别领域 -> 命中预设包 domains/<x>.md
   |    `-- custom（陌生领域）-> 取证 E0-E3 -> 写 00c -> G0.9
   |         `-- 取证能力不足 -> 停下，向用户索取材料或确认豁免
   |  写 00b-领域实例.md（用哪套尺子）
   |  写 00d-场景工况.md（量什么尺寸）<- 三级推导 SC->OP->DC
   |    `-- 用户给不出参数 -> 分「知识缺口/输入缺口」-> 假设登记（有上限）
   |  挂规则包 rulepacks/<pack>@<ver>
   |  写 00a-意图主线.md（提炼一条冻结的锚点，I0 最高优先级）
   |  G0 + G0.10 --否--> 重写 00b/00d（领域或场景错了后面全废）
   |  用户确认
=== Stage 1+ · 施工（按 00b 实例化角色，按 L0-L7 往下走）===
   |
   |  spec 写 01 需求规格 + 02 验收标准   <- 02 前置于方案
   |  G1 --否--> 退回 spec（带失败项+编号+反例）
   |  architect 写 03 方案（含规则包引用）+ 04 路径
   |  G2 --否--> 退回 architect
   |  builder 写 05 交付实体
   |  reviewer（独立子代理）写 06 盲审 + 08 追溯矩阵
   |  G3 --否--> 退回 builder（同一问题 ≤3 轮）--> 超轮 lead 裁决写 07
   |  每棒产物头部写「主线回指 + 偏移分」，累计偏移 >1.0 回 Stage 0（I0）
   |
交付：能交/不能交 + 每条 AC 证据 + 追溯闭合 + 遗留清单
```

**L0–L7 八层**：场景 → 需求 → 总体 → 分系统 → 详细 → 实现 → 验证 → 交付运维。
允许合并，不允许跳过。落点见 `references/core/e2e-spine.md`。

## 4. 每阶段动作

**开工**：`python scripts/init_run.py "<需求原文>" --domain software --root .`
建运行目录与 11 份空壳（`custom` 额外铺 `00c`，含 git init）。

| 阶段 | 动作 | 读哪个 reference |
|---|---|---|
| 0 主线 | 从 `00` 提炼一条意图主线，写 `00a`，用户确认后冻结（I0） | `references/core/intent-anchor.md` |
| 0 领域 | 判领域、填 8 槽位、写 `00b`、请用户确认 | `references/core/stage0-instantiate.md` + `domains/<x>.md` |
| 0b 取证 | **仅 custom**：三级通道取证、写 `00c`、过 G0.9 | `references/core/domain-discovery.md` |
| 0c 场景 | 填 SC1–SC8、推 OP、定 DC、登记假设、写 `00d`、过 G0.10 | `references/core/scenario.md` |
| 0d 规则 | 按场景标签挂 `rulepacks/<pack>@<ver>`，裁剪后写入 `00b` | `references/core/rulepack.md` |
| 判级 | 判 S/M/L，写 `07` 第 1 节；模糊则升一级 | `references/core/sizing.md` |
| 需求 | 拆 R、写 AC（输入→动作→可观测输出）、划边界、报冲突 | `references/roles/spec.md` + `references/core/contracts.md` §2-3 |
| 方案 | 从 AC 倒推、取舍三段式、失败模式、排步骤 | `references/roles/architect.md` + `references/core/contracts.md` §4-5 |
| 产出 | 按 04 顺序、AC 全覆盖、失败模式落到可观测行为 | `references/roles/builder.md` + `references/core/contracts.md` §6 |
| 盲审 | 起独立子代理，只传 产物/02/00/00d 四个路径 | `references/core/blind-review.md` + `references/roles/reviewer.md` |
| 追溯 | 建 `08` 五列矩阵，扫五类孤儿，层覆盖 L0–L7 | `references/core/e2e-spine.md` |
| 裁决 | 判门禁、裁冲突、记代价 | `references/roles/lead.md` + `references/core/gates.md` |
| 防绕过 | 判"是"之前过自检三问；发现 B1–B7 → VOID | `references/core/anti-bypass.md` |

五条硬规则，违反即返工：

1. **意图先于一切（I0）**：Stage 0 先提炼一条冻结的意图主线，每个产物头部回指它。回指不上即偏移。
2. **下游只读文件，不读对话**。产物必须落盘，靠对话传递的理解 5 环后偏差约 40%。
3. **architect 不读 00，reviewer 不读 03**。前者保证"验收标准够不够用"被真检验，后者保证审查不给作者找理由。
4. **lead 只做三件事**：判级、选链、裁决。一干具体活就成幻觉源。
5. **领域与场景都不能边干边换**。判错就回 Stage 0，`01`–`03` 作废，`07` 记裁决。
6. **不变量不能因领域而变**。见 `references/core/invariants.md` 的 I0–I11。

第六条规定动作：**判"是"之前先自问三句**（可复现吗 / 判否我会损失什么 / 我是不是早就知道答案）。
详见 `references/core/anti-bypass.md`。绕过形态 B1–B7 里，B1/B2/B3/B5 判 `VOID`，不是返工。

机械校验：`python scripts/check_run.py <run目录> --stage g0|g1|g2|g3`
版本与提交：`python scripts/bump.py --run <目录> --type feat --scope build --message "..." --commit`

## 5. 门禁摘要

- **G0 领域**：标识明确 / 5 角色映射齐 / 攻击面 ≥5 条且本领域特有 / 用户已确认
- **G0.9 取证**（仅 custom）：四节齐 / AC 判据追得到 E0/E1 / 无 E3 当判据 / 未取证清单非空
- **G0.10 场景**：SC1–SC8 有值 / OP ≥3 带单位 / DC ≥3 挂 RULE 或 EV / 假设四列齐且不超上限 / 用户已确认
- **G1 需求**：每条 R 可追溯（到 SC/OP/RULE/假设）/ 每条 AC 可判真假 / 边界清晰 / 无未决冲突
- **G2 方案**：取舍有放弃项+理由+代价 / 失败模式 ≥2 / 每个 AC 有验证路径 / 规则包锁版本且无 R3 当判据 / L2–L4 有落点
- **G3 交付**：盲审 blinded 且 P0=P1=0 / 每条 AC 有证据 / 追溯矩阵五类孤儿为 0 / 无绕过痕迹 / 遗留已登记

全部门禁是布尔判断，出现"较好""基本满足"即不通过。
逐条检查项与退回时该带什么：`references/core/gates.md`。产物字段、字数上限、正反例：`references/core/contracts.md`。

## 6. 失败处理

- 门禁不过：按 `references/core/gates.md` 指定位置退回，带"失败项 ID + 对应 R/AC 编号 + 一个具体反例"，不许说"整体重写"。
- 同一问题最多 3 轮。第 3 轮不过 → lead 裁决，写 `07`：谁主张、反方理由、裁决、代价、待复核条件。
- 裁决只有三种：修需求（回 G1）/ 修实现（回 builder）/ 带缺陷交付（写明用户可见影响与代价）。
- 不允许第 4 轮，不允许静默把 P1 降 P2 放行（降级本身是裁决）。
- 环境无子代理：按 `references/core/blind-review.md` 阶梯降级，`REVIEW_MODE` 必须如实标注。**不许把 unblinded 写成 blinded。**
- 审查报告全 0 问题时，必须有 3 个攻击点的实际执行结果，否则视为无效审查。
- 用户给不出场景参数：分「知识缺口（去查）/ 输入缺口（登记假设）」，假设超上限就停下问。**不许自己编一个数值然后当它有依据。**
- 用户没有图纸/规范/标准号：先把缺口列出来给用户看，能查的去查，查不到的登记为假设并标 `E3`。
  一份诚实的"缺 6 项输入"比一份编全的方案有用。

## 7. 交付口径

| 情形 | 结论 | 必须附带 |
|---|---|---|
| 无未确认假设，全部门禁绿 | `PASS` | AC 证据摘要 + 遗留清单 |
| 有未确认假设 | `PASS-WITH-ASSUMPTIONS` | 假设清单 + 每条返工点 |
| 有未闭环 P1 | `FAIL` | 未闭环项 + 复现命令 |
| 发现绕过（B1/B2/B3/B5） | `VOID` | 形态 + 证据 + 重开 run |

**不许在有未确认假设时给无条件 `PASS`。** 用户有权知道"这份交付在什么前提下成立"。

## 8. 跨平台

纯 Markdown + Python，不依赖特定平台。
其他 AI 入口：`AGENTS.md`（通用）/ `CLAUDE.md`（Claude Code）/ `PROMPT.md`（纯粘贴，给 ChatGPT 类）。

## 9. 文件地图

| 想问什么 | 看哪里 |
|---|---|
| 哪些规则绝不能变 | `references/core/invariants.md`（I0–I11） |
| 这次用什么标准验证 | `references/core/stage0-instantiate.md` + `domains/` |
| 这个场景该怎么设计 | `references/core/scenario.md` |
| 合格线在哪、出处是什么 | `references/core/rulepack.md` + `rulepacks/` |
| 陌生行业怎么取证 | `references/core/domain-discovery.md` |
| 从头到尾每层做什么 | `references/core/e2e-spine.md` |
| 怎么防止它糊弄过去 | `references/core/anti-bypass.md` |
| 每道门禁查什么 | `references/core/gates.md` |
| 产物写多少字、什么格式 | `references/core/contracts.md` |
