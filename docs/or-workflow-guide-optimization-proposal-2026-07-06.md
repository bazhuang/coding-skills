# or-workflow-guide 优化方案

日期：2026-07-06
目标技能：`or-workflow-guide`（路由器 + 进度账本管理者）
目标文件：`skills/or-workflow-guide/SKILL.md`（项目源文件；运行时副本 `~/.zcode/skills/or-workflow-guide/SKILL.md` 与之保持一致）

## 1. 背景

`or-workflow-guide` 是所有用户请求的默认入口技能，核心职责是：识别意图 → 引导本体建模 → 路由到下游专业技能（app-design / code-generation / code-verification）。它通过进度账本文件 `docs/workflow-progress.md` 记录工作流状态，支持跨会话恢复。

本方案基于对该技能 `workflow-progress.md` 格式定义与 `SKILL.md` 本身的系统审查，梳理出格式定义层面的缺陷与技能可优化点，并给出分优先级的整改清单。

**关键事实**：进度账本并非纯人读文档——下游 `code-generation` 的 preflight（`skills/code-generation/SKILL.md:49-53`）已经在机器读取它，依赖 `waived` 与 `complete`（gate=passed）两个字面值做分支判断。因此账本格式的任何改动都构成**对外契约变更**，必须保持向后兼容。

## 2. 已识别问题总览

### 2.1 `workflow-progress.md` 格式定义的问题

| 编号 | 问题 | 严重度 |
|---|---|---|
| F1 | 阶段键是中文，与下游契约引用（skill 英文名）不一致，三种叫法并存 | 高 |
| F2 | 行级格式无正式语法，字段分隔符与聚合语法不统一（空格/逗号/`+`/花括号混用） | 高 |
| F3 | `gate` 取值无闭合枚举，`impl-plan-approved` 是 `passed` 的别名还是子状态语义模糊 | 高 |
| F4 | `waived` 的 4 个结构化字段未定义分隔符与转义规则 | 中 |
| F5 | 缺少账本格式版本号、写入时间/会话 id，无法支撑"信任账本"的核心承诺 | 中 |
| F6 | 与 `spec-versions.json` 职责重叠且边界模糊，"门禁通过时所基于的指纹"无完整记录 | 中 |
| F7 | 恢复语义（"第一个非 complete 的阶段"）对 `waived` 无定义，二者冲突 | 高 |

### 2.2 `SKILL.md` 本身的可优化点

| 编号 | 问题 | 严重度 |
|---|---|---|
| S1 | `brd-generation` 被引用但该 skill 不存在（死引用） | 高 |
| S2 | `description` 写"不允许直接使用大模型回答"，行为禁令污染路由匹配信号 | 低 |
| S3 | `triggers` 含"未明确指定 skill 的请求"，catch-all 与其他技能抢占 | 低 |
| S4 | 各阶段准出门禁散落 4 处描述同一件事，措辞略有出入 | 中 |
| S5 | "单向依赖无回溯补救"与"spec-gap 回流到上游"表述矛盾 | 中 |
| S6 | 恢复语义只覆盖 complete/非 complete，未覆盖 waived / gate≠passed / 指纹漂移 | 高 |
| S7 | `references/runtime-assumptions.md` 何时应被注入上下文未说明 | 低 |
| S8 | 缺少账本自愈/审计规则（账本与实际制品不一致时信谁未定义） | 低 |

## 3. 整改清单与状态

> 状态图例：✅ 已完成 / ⏳ 待实施 / ⏸️ 已部分完成

### 第一批（高优先级，已完成）

| 项 | 对应问题 | 状态 |
|---|---|---|
| **A. 修复 `brd-generation` 死引用** | S1 | ✅ |
| **B. 阶段键统一为稳定英文标识符** | F1 | ✅ |
| **C. `gate` 取值收敛为闭合枚举** | F3 | ✅ |
| **D. 补全恢复语义为显式决策树** | F7, S6 | ✅ |

#### A. 修复 `brd-generation` 死引用（S1）— ✅ 已完成

**改动**：`SKILL.md:19` 删除对不存在 skill `brd-generation` 的引用整句。核实结论：`brd.md` 产物的真实归属是 `ontology-modeling`（它自己就列 brd.md 为核心产物），不存在"只产文档不产 schema"的独立入口。把"用户只要文档"场景改为挂到真实存在的 `ontology-modeling`（在该 skill 内做轻量建模并止于 brd.md）。

**验证**：`or-workflow-guide/SKILL.md` 与整个 `skills/` 目录均无 `brd-generation` 残留。

#### B. 阶段键统一为稳定英文标识符（F1）— ✅ 已完成

**改动**：在「进度账本」区新增「阶段标识符」权威表，定义 4 个稳定键：

| 标识符（权威键） | 显示别名 | 对应 skill |
|---|---|---|
| `ontology_modeling` | 本体建模 | ontology-modeling |
| `app_design` | 应用设计 | app-design |
| `code_generation` | 代码生成 | code-generation |
| `code_verification` | 代码验证 | code-verification |

- 账本示例 7 行全部改用新键；明确"下游技能按字面值匹配，不得改写为中文"。
- **向后兼容**：旧中文键按表映射回归一，老账本仍可读。

**验证**：账本权威键无中文残留；`code-generation` preflight 依赖的 `waived`/`complete` 字面值未变，契约未被破坏。

#### C. `gate` 收敛为闭合枚举（F3）— ✅ 已完成

**改动**：在「进度账本」区定义 `gate` 闭集（单一来源）：`{passed, failed, blocked, n/a}`，并绑定规则"`status=complete` 当且仅当 `gate=passed`"。

消除 `gate=impl-plan-approved` 这个模糊值——它是代码生成阶段的**子进度**，移入专属字段 `substage=impl-plan-approved`；门禁表（`SKILL.md:108-111`）与工作流图同步更新。

**向后兼容**：旧值 `gate=impl-plan-approved` 归一为 `gate=failed, substage=impl-plan-approved`（impl-plan 已批准但代码未生成完 = 门禁未通过）；`in progress`（带空格）归一为 `in_progress`。

**验证**：所有 `gate=` 取值均在闭集内；`gate=impl-plan-approved` 仅存于向后兼容说明。

#### D. 补全恢复语义为显式决策树（F7, S6）— ✅ 已完成

**改动**：把原"从第一个非 complete 的阶段恢复"这句含糊规则，替换为「启动恢复决策树」（`SKILL.md` 进度账本 → 账本规则）：

1. **指纹漂移优先**：先重算各规格制品指纹与 `spec-versions.json` 比对，漂移则走规格变更分支。
2. 遍历阶段，对第一个非 `complete` 的阶段按 `status`/`gate` 处置：
   - `pending` → 执行
   - `in_progress` + `gate=passed` → 异常状态，回该阶段重检门禁
   - `in_progress` + `gate∈{failed,blocked}`/缺失 → 回补门禁，不从下游续跑
   - `waived` → 视为已放行不重跑，但**必须复述 risk/remediation** 并对下游降级
   - `in_progress` + `gate=n/a` → 视同 `waived`
3. 已 `complete` 的阶段绝不重复执行。

同步在「交互规范」启动检查项（原 `SKILL.md:191`）引用该决策树。

### 第二批（中优先级，待实施）

#### E. 账本升级为结构化格式 + 与 spec-versions 指纹锚点合并（F2, F4, F5, F6）— ⏳ 待实施

**问题**：当前账本是"人读自由文本 + 机器读取契约"混合体，字段分隔符不统一、无转义规则、无格式版本号/时间戳，且与 `spec-versions.json` 割裂（门禁状态在 .md、指纹在 .json，"门禁通过时所基于的指纹"无处记录）。

**建议方案（推荐方向 1，低迁移成本）**：保留 `.md` 但定义为严格可解析的 YAML front-matter + 简表，自由文字只放注释块：

```yaml
---
schema_version: 2
updated_at: 2026-07-06T10:00:00+08:00
stages:
  ontology_modeling:
    status: complete
    gate: passed
    artifacts: [ontology_schema.json, brd.md, requirements-baseline.json, contracts/acceptance-tests.yaml]
    coverage: {objects: 8/8, behaviors: 40/40, rules: 5/5}
    waived: null          # {reason, missing, risk, remediation} 仅 waived 时填
  app_design:
    status: complete
    gate: passed
    generated_against:    # 把 spec-versions 的锚点直接挂进来，消除两文件割裂
      ontology_schema.json: a1b2c3d4
---
# 进度说明（人读自由文本，不参与解析）
```

一次性解决 F2（语法）、F4（waived 结构化）、F5（版本/时间戳）、F6（指纹锚点合一）。

**备选方向 2**：直接用 `workflow-progress.json`（与 `spec-versions.json` 同构），另用 `workflow-progress.md` 只做人类摘要。会增文件数但解析最稳。

**风险**：此改动改变账本文件格式本身，需同步评估 `code-generation` preflight 的读取方式（当前是语义指代，理论上兼容，但需回归测试），并设计旧 .md → 新格式的迁移/兼容读取路径。

#### F. 门禁规范单一来源 + 消除"单向依赖 vs 回流"表述冲突（S4, S5）— ⏸️ 已部分完成

**已完成部分**：第一批 C 已把 `gate` 闭集收敛到单一来源定义。

**待完成部分**：
- S4：各阶段准出门禁仍散落在「进度账本说明」「准出门禁表」「完整工作流图」「各步判断依据」4 处。建议定义**单一处「门禁规范」**，其余位置只引用。
- S5：`code-generation` 视角的"app-design → code-generation 之间单向依赖，无回溯补救通道"与本技能"spec-gap 回流到上游修订"矛盾。需拆开定义两个概念：
  - 「执行链路单向」= 不自动反向调用 skill（成立）
  - 「人工回流修订」= spec-gap 触发重跑上游（也成立）
  两者不冲突，是被同一句"单向依赖"搅在一起。

### 第三批（低优先级，待实施）

#### G. `description` 移除行为禁令；`triggers` 收敛 catch-all（S2, S3）— ⏳ 待实施

- S2：`description` 字段语义本是"技能用途说明，供路由匹配"，但当前写"不允许直接使用大模型回答"——这是对 router 行为的强约束，会污染路由匹配信号。应移入正文「核心原则」。
- S3：`triggers` 第 5 条"未明确指定 skill 的请求" + 开篇"所有用户请求的默认入口"使该技能成为 catch-all，会与 `using-superpowers` 等元技能及显式 `/skill` 调用抢占。建议收敛触发条件，避免吞掉本应直达其他技能的请求。

#### H. `references` 注入说明 + 账本自愈（S7, S8）— ⏸️ 已部分完成

**已完成部分**：第一批 D 已补「账本自愈」规则（以实际制品存在性 + 指纹校验账本，不盲信字面值；不一致时以制品为准并回写账本）。

**待完成部分**：
- S7：正文末尾引用 `references/runtime-assumptions.md` 并标注"代码级改动属高风险"，但未说明该文件何时应被注入上下文。需明确：涉及 `finish_ontology.py` / `agents/openai.yaml` 改动时，router 应主动 `Read references/runtime-assumptions.md`。

## 4. 优先级总表

| 优先级 | 项 | 对应问题 | 状态 |
|---|---|---|---|
| 🔴 高 | A. 修复 `brd-generation` 死引用 | S1 | ✅ |
| 🔴 高 | B. 阶段键统一为稳定标识符 | F1 | ✅ |
| 🔴 高 | C. `gate` 取值收敛为闭合枚举 | F3 | ✅ |
| 🔴 高 | D. 恢复语义补全为决策树 | F7, S6 | ✅ |
| 🟡 中 | E. 账本升级为结构化格式 + 指纹锚点合并 | F2, F4, F5, F6 | ⏳ |
| 🟡 中 | F. 门禁单一来源 + 消除表述冲突（残余部分） | S4, S5 | ⏸️ |
| 🟢 低 | G. description/triggers 规范化 | S2, S3 | ⏳ |
| 🟢 低 | H. references 注入说明（残余部分） | S7 | ⏸️ |

## 5. 向后兼容性原则

所有账本相关改动遵循以下兼容原则（已在第一批落实，后续批次须延续）：

1. **下游硬依赖的字面值不变**：`waived`、`complete`、`gate=passed` 这三个被 `code-generation` preflight 依赖的字面值保持原样。
2. **旧格式可读**：旧中文键、旧 gate 值、旧 status 值均提供归一映射，老账本仍可被读取恢复。
3. **改动前先核对下游**：任何账本格式变更前，先检查 `code-generation`（及其他可能读取账本的技能）的 preflight 逻辑，确认契约未被破坏。

## 6. 后续推进建议

1. **第二批 E（账本结构化）** 是下一个最有价值的改动，但风险也最高（改变文件格式）。建议先在一个真实项目里试跑当前已修复的 .md 格式，确认第一批修复稳定后再推进结构化迁移。
2. **第二批 F** 可与 E 解耦独立推进——门禁单一来源是纯文档重组，无契约风险。
3. 第三批 G/H 属于打磨项，可随其他改动顺手处理。

---

## 附录：第一批改动的文件差异摘要

目标文件：`skills/or-workflow-guide/SKILL.md`

1. **第 19 行**（A）：删除 `brd-generation` 死引用整句，改为挂到 `ontology-modeling`。
2. **第 25–58 行 → 重写为 25–95 行**（B/C/D）：「进度账本」区重构为 5 个子节——阶段标识符表、状态与门禁闭集、账本格式、waived 状态、规格版本记录、账本规则（含启动恢复决策树 + 账本自愈）。
3. **第 60–71 行**（C）：门禁表标题与跳过阶段提示对齐新 gate 闭集；代码生成门禁拆出 `substage=impl-plan-approved`。
4. **第 89 行**（C）：工作流图代码生成门禁 `gate=impl-plan-approved` → `substage=impl-plan-approved 且代码全量生成完成 → gate=passed`。
5. **第 191 行 → 第 243 行**（D）：交互规范启动检查项引用新的恢复决策树。

运行时副本 `~/.zcode/skills/or-workflow-guide/SKILL.md` 与项目源文件保持一致（已核实 `diff` 完全相同）。
