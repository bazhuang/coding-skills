---
name: ontology-modeling
description: Guide business teams through ontology modeling and BRD generation using Object-Behavior-Rules methodology. Use when users need to model business domains, design system architecture, create entity-relationship definitions, continue an existing ontology/BRD, extract a domain model from business materials, or generate business requirement documents.
---

# 本体论建模与 BRD 生成

使用**对象(Object)、行为(Behavior)、规则(Rules)**三要素方法论，通过业务访谈持续产出跨 coding agent 通用的需求规格文件：

1. `docs/ontology_schema.json` — 结构化业务领域模型（权威规格）
2. `docs/brd.md` — 结构化业务需求文档（人读派生视图）
3. `docs/requirements-baseline.json` — 已冻结需求基线（Requirements Gate 后的权威规格）

建模交互必须边聊边写文件。回复只输出摘要、下一步问题和文件路径；除非用户明确要求，不要在回复里粘贴完整 JSON 或完整 BRD。

## 必读与按需参考

先读本文件，按场景再读取 references：

| 场景 | 读取 |
|---|---|
| 需要确认文件路径、读写规则、回复格式、平台 artifact 兼容规则 | `references/output-contract.md` |
| 需要细化对象/行为/规则/SOP 建模方法、提问策略、常见误区 | `references/modeling-methodology.md` |
| 需要写入或校验 `docs/ontology_schema.json` 结构 | `references/schema-contract.md`，必要时查看 `references/ontology_schema.schema.json` |
| 准备标记 Requirements 阶段完成、进入 app-design/code-verification | `references/requirements-gate.md` |
| 需要示例辅助理解，但当前任务信息不足 | `examples.md` |

脚本：

- 校验 schema：`python3 skills/ontology-modeling/scripts/validate_ontology.py docs/ontology_schema.json`

## 核心原则

1. **文件优先**：建模阶段以 `docs/ontology_schema.json` 为领域模型权威源；Requirements Gate 通过后以 `docs/requirements-baseline.json` 为冻结需求权威源；`docs/brd.md` 是人读视图。
2. **持续更新**：从识别出第一个对象开始，每次回复前都要写入完整当前版本，非增量片段。
3. **对象优先**：先定义存在什么对象，再定义行为和规则。
4. **行为改变状态**：每个行为应导致至少一个对象的属性或状态变化；查询行为除外，但要明确其读取目的。
5. **规则只保留高价值**：只提取后续代码无法自然推断、会影响算法/流程/跨实体一致性的领域规则。
6. **渐进访谈**：不要一次性抛出所有问题；每次问最能推进建模的一组问题。

## 产物分层

| 产物 | 文件路径 | 默认时机 |
|---|---|---|
| Ontology Schema（权威规格） | `docs/ontology_schema.json` | 每次交互结束前更新 |
| BRD 文档（派生视图） | `docs/brd.md` | 每次交互结束前更新 |
| 需求基线（权威规格） | `docs/requirements-baseline.json` | Requirements Gate 通过后生成并批准 |
| 验收测试视图（派生导出） | `docs/contracts/acceptance-tests.yaml` | 需要自动验收、接口冒烟或测试 runner 对接时，从需求基线导出 |

建模交互过程中的通用默认产物只要求前两份。只有在准备进入下游阶段时，才生成并批准需求基线；`acceptance-tests.yaml` 不是第二个需求事实源，只是基线验收标准的测试视图。

**多场景迭代下的产物边界**：`ontology_schema.json` 与 `requirements-baseline.json` 是系统态制品，跨场景累积演进；`brd.md` 采用「主文档 + 历史场景索引」结构——系统态章节累积维护，§4 只保留当前活跃场景的需求明细，已交付场景收敛为摘要行并链接归档（由 `sdd-archive` skill 在交付时收敛）。新场景的 F-xxx 编号在既有最大编号后递增，不复用已交付编号。

## 启动流程

当用户提出建模、BRD、领域模型、业务对象梳理、继续上次建模等需求时，按以下顺序执行。

### 0. 恢复上下文

1. 检查 `docs/sdd-state.yaml` 是否有 `archives:` 列表（或存在 `docs/archive/index.md`）。
   - 有：说明系统已有已交付场景。向用户播报「系统已有 N 个已交付场景：<场景列表>，本次将在已有系统模型上**增量建模**」，历史需求明细按需查 `docs/archive/<场景>/views/brd.md`，不要整体读入。
2. 检查 `docs/ontology_schema.json` 是否存在。
   - 存在且有已交付场景：读取文件，作为**系统累积域模型**加载（不是"未完成的上次进度"），摘要展示已有对象、关系、规则、SOP，新建模在其上增量扩展。
   - 存在且无归档记录：读取文件，告知用户已加载上次建模进度，摘要展示。
   - 不存在：准备从零开始。
3. 检查 `docs/brd.md` 是否存在。
   - 存在：读取文件，摘要展示已完成章节；若含「历史场景索引」章节，本次场景的需求写入 §4，不改写已交付场景的摘要行。
   - 不存在：准备从零开始。
4. 检查当前目录下是否有业务材料文件，如 `db.schema`、`business_scenario.md`、`requirements.md`、DDL、流程说明等。
   - 存在：读取材料，提取对象、属性、关系、流程、规则，并与现有产物合并。
   - 冲突：不要覆盖已有内容，向用户确认保留或合并方式。

### 1. 需求理解

如果业务领域仍不清楚，先问：

- 要建模的业务领域或功能模块是什么？
- 主要解决什么业务问题？
- 涉及哪些主要业务实体、角色或流程？

同时从用户描述中推理初步对象、行为、规则，并明确哪些是用户确认的信息、哪些是建议补充的信息。

产出更新：

- `docs/ontology_schema.json`：初始化 `domain`、`biz_logic`、初步 `objects`
- `docs/brd.md`：更新 §1 项目概述、§2 业务范围

### 2. 对象建模

识别核心对象、实体对象、引用对象和对象关系。详细分类、提问方式和常见误区见 `references/modeling-methodology.md`。

产出更新：

- `docs/ontology_schema.json`：更新 `objects[]`、`edges[]`
- `docs/brd.md`：更新 §3 利益相关方、§6 数据需求

### 3. 行为与 SOP 建模

围绕核心对象识别 Create、Update、Query、Delete、Derive 五类行为，并把关键业务路径组织为 `sop_flows[]`。

产出更新：

- `docs/ontology_schema.json`：在 `biz_logic` 中记录行为信息，更新 `sop_flows[]`
- `docs/brd.md`：更新 §4.1 功能需求、§5 业务流程

### 4. 高价值规则建模

只提取对后续应用代码有直接影响的规则。不要把字段必填、正数校验、枚举范围、标准外键存在性这类基础校验塞进 `rules[]`。

优先提取：

- 业务计算公式
- 跨对象约束
- 跨实体一致性
- 影响流程分支或算法优先级的领域决策

产出更新：

- `docs/ontology_schema.json`：更新 `rules[]`
- `docs/brd.md`：更新 §7 业务规则、§4.2 非功能需求

详细过滤标准和示例见 `references/modeling-methodology.md`。

### 5. 自检与补全

在用户准备结束建模、或你判断产物已基本完整时，做快速自检：

- 所有核心对象是否都有必要行为？
- 对象关系是否有明确方向和约束？
- 高价值规则是否排除了基础校验噪音？
- BRD 目标、范围、流程、数据、规则、术语是否一致？
- `biz_logic` 是否保留了足够的业务上下文，方便下游理解？

产出更新：

- `docs/brd.md`：补齐 §8 约束与假设、§9 风险分析、§10 术语表
- `docs/ontology_schema.json`：确保结构完整、code 稳定

### 6. Requirements Gate

只有当用户要求进入下游 app-design/code-generation/code-verification，或要把 Requirements 阶段标记为完成时，执行 Requirements Gate。

此时必须读取 `references/requirements-gate.md`，并至少完成：

1. 运行 `validate_ontology.py`，修复所有 ERROR。
2. 确保 BRD §4 的每个 Must Have 功能有稳定 ID、可测试验收标准、来源 ontology code。
3. 生成 `docs/requirements-baseline.json`；如需要自动验收或接口冒烟，再从 baseline 导出 `docs/contracts/acceptance-tests.yaml`。
4. 用户确认后，将 `requirements-baseline.json` 中 `approved` 置为 `true`。

Gate 不通过不得进入下游 app-design。

## 每轮回复要求

每次回复用户前，先把最新完整产物写入本地文件。回复包含：

1. 对用户输入的理解和建模判断
2. 本轮更新摘要，例如 `objects=3, edges=2, rules=1, sop_flows=1`
3. 已更新文件路径
4. 下一步最关键的问题

示例：

```text
已更新 docs/ontology_schema.json（objects=3, edges=2, rules=1）。
已更新 docs/brd.md（补充了 §4 业务需求、§6 数据需求）。
下一步我需要确认：合同从草稿到生效之间有哪些审批或状态变化？
```

## 写入规则

- `docs/ontology_schema.json` 必须是纯 JSON，不带 Markdown 代码块、XML、HTML、artifact/card wrapper。
- `docs/brd.md` 必须是普通 Markdown，不写入平台专用展示协议。
- 每次覆盖写入完整当前版本，确保文件可以被其他 agent 直接接手。
- 只有用户明确要求 MCP 持久化，或当前环境必须通过 MCP 服务写文件时，才改用 `mcp__graph__data_write`。

## 交互风格

- 一次推进一个建模焦点，不要一次抛出完整问卷。
- 对不完整信息可以合理推理，但必须标注为推理并让用户确认。
- 发现建模问题时给出建议和原因，不直接替用户做高风险业务决定。
- 用户要求查看全文时，读取文件后展示相关片段；默认只展示摘要。
