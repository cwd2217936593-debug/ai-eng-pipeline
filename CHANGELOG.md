# Changelog

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。
格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [2.1.0] - 2026-11-22

### 新增（MINOR）

**陌生领域取证（Stage 0.5 + G0.9）** —— 补上 `custom` 领域原本的空白：能识别陌生行业，但填不出可信的槽位。

- 新增 `references/core/domain-discovery.md`：E0-E3 四级证据体系 + 三条取证通道 + 跨 AI 降级阶梯
- 新增 `assets/templates/00c-领域取证.md`：证据台账 / 未取证清单 / 架构适配假设 / 取证能力声明
- 新增 G0.9 门禁（7 项布尔判断）：仅 `domain: custom` 生效
- `init_run.py`：`--domain custom|未判` 时额外铺 `00c`；提示语增加取证步骤
- `check_run.py`：新增 `check_g09`；`--stage all` 现在也跑 G0（此前只在 g0 单独跑）
- `_template.md`：区分「沉淀成领域包」与「一次性陌生领域」两条用法，后者要求槽位 2/4/6/7 引证据 ID
- `AGENTS.md` / `CLAUDE.md` / `PROMPT.md`：各自补陌生领域处置段

### 设计要点

1. **E3 只能产问题，不能产判据**。模型自身的行业知识是幻觉高发区 ——
   编造的 API 会被 import 拦下，编造的 GB 号会一路走到施工。
2. **E1 必须给条号**。标准号可以瞎编，条号内容要自洽，后者才是有成本的检验。
3. **未取证清单不许为空**。空了不是"查清了"，是"没查"。
4. **取证能力不足就停下**。无联网无知识库只能到 E3，此时向用户索取材料，
   或由用户签署豁免（须记录原话），不许拿猜测当规范。

### 修复

- `G0.9.5` 初版把模板里的"用户已接受豁免"字样当成了真实豁免，全文搜索导致假通过 → 改为只看 4.4 节的「未覆盖」字段
- `G0.9.6` 初版在 AC 尚未写时误报 → 增加"是否已有真实填写过的 AC 行"判定

### 验证

- `init_run --domain custom` 铺出 00c，`--domain software` 不铺
- G0.9 正向：建筑钢结构样例 6 项全过（E1 带条号、未取证清单 3 条）
- G0.9 负向：空台账拦 4 项；幽灵证据 EV-99 拦；取证能力占位符拦；`无` 且无豁免拦

---

## [2.0.0] - 2026-11-22

### 重大变更（MAJOR）

流水线从"软件专用"升级为"领域可插拔"，并新增前置段。**不兼容 1.x**。

#### 新增
- **`references/core/invariants.md`**：9 条不变量（I1–I9），跨领域跨平台不可变。这是 2.x 的地基。
- **两段式流程**：新增 Stage 0「领域实例化」，产出 `00b-领域实例.md`，并新增门禁 **G0**。
  理由：同一流程套到不同领域，失败原因完全不同；不先定"用哪套标准"，后续越努力越错。
- **领域包机制**：`references/domains/` 下新增 `software` / `hardware` / `hr` / `_template`。
  领域包只提供 8 个槽位（交付实体/验证方式/方案载体/攻击面/角色映射/合规/判定用语/判级门槛），不得覆盖不变量。
- **跨平台入口**：`AGENTS.md`（通用）、`CLAUDE.md`（Claude Code，含 Task 盲审写法）、`PROMPT.md`（单文件版，给 ChatGPT 类无文件系统环境）。
- **`references/core/stage0-instantiate.md`**：领域识别信号表、混合领域处理、判错代价。
- **`tests/t5/`**：端到端案例，含三轮审查对照（self-PASS → blinded-FAIL）。

#### 变更
- `SKILL.md`：重写为两段式，加 G0，description 从"软件需求"改为"需求"，覆盖三领域。
- 目录重组：`references/{contracts,gates,sizing,blind-review}.md` → `references/core/`。
- 版本策略写入 README：改不变量 = MAJOR，加领域包 = MINOR。

#### 修复
- 修正 1.x 的定位偏差：原版把 `architect` 的"考虑什么点"当作软件专属，实际应随领域变化。

---

## [1.0.0] - 2026-11-22

### 首个版本（软件专用）

- 5 角色：lead / spec / architect / builder / reviewer
- 8 份产物契约（`00`–`07`），含字数上限与正反例
- 3 道门禁：G1 需求 / G2 方案 / G3 交付
- 盲审协议：`blinded` / `degraded` / `unblinded` 三级降级阶梯
- 脚本：`init_run.py`（建目录）、`check_run.py`（49 项机械校验）、`bump.py`（版本与 CHANGELOG）
- 核心设计：产物优先于角色、下游只读文件、可验证性前置、审查隔离

### 已知问题
- 全流程按软件场景设计，硬套到硬件或人力资源会产出正确的废话。
- `check_run.py` 的 G3.4 在特定表格列名下会误报"证据表缺 AC"（方向安全：宁可误拦不放行）。
