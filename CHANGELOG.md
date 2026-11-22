# Changelog

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。
格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

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
