# 规则包目录（rulepacks/）

> 这里是**判据库**，不是方法论。方法论在 `references/domains/`。
> 格式与门禁见 `references/core/rulepack.md`。

---

## ⚠️ 先读这一条

**本目录下的 `example-*` 与 `_template` 仅供格式演示，不得直接用作拒收判据。**

原因：写规则包的人（包括 AI）很容易"凭记忆填条号"。编一个标准号很容易，
编对条号的内容很难 —— 而错的标准号会让整条判据失效，且不会有任何东西报错。

所以每个包里有 `clause_verified` 字段：

| 值 | 含义 | 能否作判据 |
|---|---|---|
| `true` | 逐条核对过标准正文，条号与摘录均准确 | 能 |
| `false` | 只知道标准存在与大致内容，条号未核 | **不能**，只能用于发现问题 |

新建包时**默认写 `false`**，核完一条改一条。**不许整包一次改成 `true`。**

---

## 目录约定

```
rulepacks/
  README.md                      # 本文件
  _template/rulepack.yaml        # 复制它开始写新包
  example-hw-fastener-cold/      # 示例：低温紧固件（clause_verified: false）
  example-sw-web-baseline/       # 示例：Web 应用基线（部分 true）
```

命名：`<域>-<主题>`，小写连字符。`hw-` 硬件 / `sw-` 软件 / `hr-` 人力 / `mfg-` 制造工艺。

## 一个领域挂多个包

规则包按主题切，不按领域切。硬件项目通常同时挂：
`hw-fastener-cold`（紧固件）+ `hw-surface-treatment`（表面处理）+ `hw-emc`（电磁兼容）+ `hw-safety`（安规）

Stage 0 按场景标签裁剪，只挂命中的。裁剪结果与未挂理由都写进 `00b`。

## 版本与升级

- 包版本独立于 skill 版本（`pack@1.2.0` 与 `ai-eng-pipeline v3.0.0` 无关）
- 规则变更 → 改包版本；**引用了旧版本的 run 不自动升级**
- 标准改版（如 GB/T 3098.1 出新版）→ 新建版本号，旧版保留，`deprecated: <日期>` 标记

## 贡献一条规则的检查单

- [ ] `id` 唯一且带域前缀
- [ ] `source` 能定位到具体文件（标准号+年份 / URL+日期）
- [ ] `clause` 有章节号；没核过就写 `待核` 并置 `clause_verified: false`
- [ ] `level` 是 R0/R1/R2/R3 之一
- [ ] `severity_if_fail` 与 `level` 匹配（R3 只能 `advise`）
- [ ] `check` 写了怎么验（写不出 check 的规则是口号）
- [ ] `evidence_needed` 写了要什么材料
