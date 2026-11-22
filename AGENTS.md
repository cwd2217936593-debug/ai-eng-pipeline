# AGENTS.md

> 本文件是所有 AI 编码助手的通用入口（Codex / Cursor / Windsurf / Gemini CLI / 其他支持 AGENTS.md 约定的工具）。
> Claude Code 请另看 `CLAUDE.md`；只能粘贴文本的对话式 AI 请用 `PROMPT.md`。

## 这是什么

一套**不绑定平台的工程流水线**：把口语需求变成可验收交付物。

它不是代码库，是一套工作规程。你不"运行"它，你"照着它做事"。

## 你该先读什么

按顺序，读到够用就停：

1. `SKILL.md` —— 主流程（约 2000 字）。**必读。**
2. `references/core/invariants.md` —— 11 条不变量。**必读**，违反任何一条流程就失效。
3. `references/core/stage0-instantiate.md` —— 第一段怎么定领域。
4. `references/domains/<domain>.md` —— 当前任务的领域包（software / hardware / hr / _template）。
5. `references/core/scenario.md` —— 场景实例化（SC→OP→DC）。**和领域包同等重要**：
   领域定"用哪套尺子"，场景定"量什么尺寸"。冷库螺丝与空调螺丝是两个零件。
6. **若是陌生领域**（不在上面三个内，如建筑/机械/医疗/法律/物流）：必读 `references/core/domain-discovery.md`，先取证再填 `00b`，产出 `00c`。
7. `references/core/rulepack.md` —— 规则包协议。要把"符合行业规范"换成"符合 RULE-xxx，出处某标准某条"。
   注意：GitHub 上的 checklist 属 R3，**只能提建议，不能当拒收判据**。
8. 干活时按需读：`references/core/contracts.md`（产物契约）、`references/core/gates.md`（门禁）、`references/core/e2e-spine.md`（L0-L7 与追溯矩阵）、`references/core/anti-bypass.md`（防绕过）、`references/core/blind-review.md`（审查协议）、`references/roles/*.md`（角色卡）。

不要一次性全读。按阶段加载，避免上下文被塞满。

## 两个阶段，不能省 Stage 0

```
Stage 0  定领域、定场景、定角色、定验证方式
         →  产出 00b-领域实例.md + 00d-场景工况.md  →  G0 + G0.10  →  用户确认
         └ 陌生领域：取证 E0-E3 → 00c-领域取证.md → G0.9 →（取证能力不足则停下）
         └ 挂规则包：按场景标签选 rulepacks/<pack>@<ver>
Stage 1+ 拆需求、定验收、出方案、产出实体、独立盲审  →  G1/G2/G3  →  交付
```

**Stage 0 是不可跳过的。** 跳过它，你会用"软件的验证方式"去审一份硬件方案或人力资源制度，产出正确的废话。

**陌生领域不能凭印象填。** 编造的规范号、公差等级、合规条款不会有任何东西报错 ——
这是整套流程里唯一"错了也没人发现"的失败模式。所以陌生领域的 AC 判据必须追到
证据编号（E0/E1），模型自己的知识（E3）只能用来提问题，不能当判据。

## 五个动作要点

1. **先判级，再决定开不开流水线。** S 级（单点小改）直接做，不要套全套流程。
2. **验收标准写在方案之前，且之后冻结。** 写不出可判真假的验收标准 = 需求不成立，退回。
3. **产物必须落盘。** 只存在于对话里的结论视为不存在，下游只读文件。
4. **审查者必须独立上下文。** 你的平台怎么做见下节。
5. **同一问题最多 3 轮。** 不过就升级裁决，留记录。
6. **判"是"之前问三句**：别人能只看文件复现我的判断吗？判否我会损失什么？我是不是早就知道答案？
   第三问答"是"即为确认偏误，该条判否。详见 `references/core/anti-bypass.md`。
7. **用户给不出参数很正常。** 分「知识缺口（去查）/ 输入缺口（登记假设）」，
   假设必须给具体值 + 若错代价与方向 + 谁确认 + 返工点，且数量有上限。**不许编一个数然后当它有依据。**

## 盲审在你的平台上怎么做

| 你的能力 | 做法 | 报告里记 |
|---|---|---|
| 能起子代理（Codex task / Claude Task / 支持 subagent） | 起一个全新子代理，prompt 只给四个路径 | `REVIEW_MODE: blinded` |
| 能起新进程 / 有 CLI | 用 CLI 单次 prompt 调用另一个模型，只传四个路径 | `REVIEW_MODE: degraded` |
| 都没有（单会话） | 只能自审。必须把所有攻击点的真实命令与输出贴全 | `REVIEW_MODE: unblinded`，且 G3 判否 |

**绝对禁止**：不声明模式就交付；把 `unblinded` 写成 `blinded`。

四个路径 = 交付实体目录 + 验收标准 + 原始需求 + 场景工况（`00d`）。**不给**需求规格、方案、路径、任何已有审查报告。

## 脚本

```bash
python scripts/init_run.py "<需求原文>" --domain software --root .   # 建运行目录
python scripts/check_run.py <run目录> --stage g0|g1|g2|g3            # 门禁机械校验
python scripts/bump.py --run <目录> --type feat --scope build --message "..." --commit
```

脚本只做机械可判的事（结构、字数、编号追溯）。语义判断（需求是否合理、方案是否成立）必须由角色完成，脚本兜不住。

## 交付时必须给用户

- 能不能交（能 / 不能 / 有条件）
- 每条 AC 的证据（命令 + 实际输出摘要）
- 未闭环问题清单（带级别与影响）
- 遗留项的触发条件
- `07-裁决记录.md` 里的所有裁决

## 版本

当前内核 `v2.x`。不变量变更 = MAJOR。领域包可独立演进 = MINOR。
详见 `VERSION` 与 `CHANGELOG.md`。
