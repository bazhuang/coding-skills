# 输出契约与读写规则

本文件定义 ontology-modeling 的跨 agent 产物约定。生成、恢复、交接、平台展示适配时读取。

## 权威文件

每次生成的 Ontology Schema 和 BRD 文档默认写入本地 `docs/` 目录，后续交互在已有数据基础上进行增量修改。**文件是唯一权威产物**：Codex、ZCode、Claude Code 等 agent 只需要读写这些标准文件即可继续工作或交给下游 skill。

对话回复只输出摘要、下一步问题和文件路径，不在回复里内嵌完整 JSON/Markdown。只有当用户或特定平台明确要求时，才额外输出平台专用的 artifact/card 标记；这些标记不得作为跨 agent 的主契约。

## 文件路径约定

| 产出物 | 文件路径 | 格式 |
|--------|---------|------|
| Ontology Schema | `docs/ontology_schema.json` | JSON（符合 `Ontology` 接口定义，且须通过 `scripts/validate_ontology.py` 校验） |
| BRD 文档 | `docs/brd.md` | Markdown（符合 BRD 模板结构） |

> Requirements 阶段准备进入下游 app-design / code-verification 时，可按 `requirements-gate.md` 额外生成 `docs/requirements-baseline.json` 与 `docs/contracts/acceptance-tests.yaml`。建模交互过程中的通用默认产物仍只要求上述两份文件。

## 读写规则

1. **建模开始前**：检查 `docs/` 目录下是否已存在 `ontology_schema.json` 和 `brd.md`。
   - 如果存在：读取现有文件内容，作为当前建模的基础，在对话中告知用户“已加载上次的建模进度”。
   - 如果不存在：从零开始生成。

2. **每次交互结束前**：将最新的 Schema 和 BRD 默认直接写入本地对应文件。
   - 将完整的 Ontology Schema JSON 字符串写入 `docs/ontology_schema.json`。
   - 将完整的 BRD Markdown 内容写入 `docs/brd.md`。
   - 每次覆盖写入完整内容（非增量），确保文件始终是最新状态。
   - 只有当用户明确要求使用 MCP 持久化，或当前运行环境必须通过 MCP 服务写文件时，才改用 `mcp__graph__data_write`。

3. **跨会话延续**：不同 coding agent 会话可以通过读取本地文件恢复建模进度。
   - 用户可以说“继续上次的本体建模”，skill 读取文件后从中断处继续。
   - 用户也可以提供新的业务场景文件（如 `db.schema`、`business_scenario.md`），skill 读取后与现有 schema/BRD 合并更新。

## 与已有业务材料的整合

当用户提供已有业务材料（如数据库 DDL、业务场景文档等）时：

- 读取材料内容，提取其中的对象、属性、关系信息。
- 与现有的 `docs/ontology_schema.json` 和 `docs/brd.md` 进行合并。
- 新发现的对象、属性、规则补充到现有文件中，不覆盖已有内容。
- 如果存在冲突（如同名对象但定义不同），向用户确认后决定保留哪个版本。

## BRD 文档结构

在访谈过程中同步生成的 BRD 文档包含以下章节，各章节与建模步骤的对应关系如下：

| BRD 章节 | 对应建模步骤 | 内容说明 |
|---------|------------|---------|
| §1 项目概述 | 步骤1 | 项目背景、目标、预期收益 |
| §2 业务范围 | 步骤1 | 包含/不包含范围、系统边界 |
| §3 利益相关方 | 步骤2 | 参与角色、部门、职责 |
| §4 业务需求 | 步骤3 | 功能需求（必须有/应该有/可选）+ 非功能需求 |
| §5 业务流程 | 步骤3 | 主流程、异常流程、审批流程 |
| §6 数据需求 | 步骤2 | 核心实体、属性、关系、数据生命周期 |
| §7 业务规则 | 步骤4 | 数据校验、流程流转、权限、计算规则 |
| §8 约束与假设 | 步骤5 | 技术约束、业务约束、前置假设 |
| §9 风险分析 | 步骤5 | 业务风险、技术风险、应对策略 |
| §10 术语表 | 步骤5 | 业务术语定义、缩写对照 |

详细的 BRD 模板参见 `references/brd-template.md`。

## 回复结构

每次回复应包含：

1. 对用户输入的回应和建模判断。
2. 下一步需要用户确认的问题。
3. 已更新文件的路径和摘要统计。

除非用户明确要求，不要在聊天回复里粘贴完整 BRD 或完整 Schema，避免让不同 agent 依赖私有消息解析。

## 平台专用渲染的兼容规则

如果某个运行环境明确要求 artifact/card 渲染，可以在写入标准文件后额外输出该平台需要的标记。但必须遵守：

1. 标准文件仍是唯一权威产物，artifact/card 只是展示层副本。
2. artifact/card 内容不得与 `docs/ontology_schema.json`、`docs/brd.md` 不一致。
3. 不要把 `<artifact>`、HTML、自定义 XML 或卡片协议写入 `docs/ontology_schema.json` / `docs/brd.md`。
4. 给用户说明这些标记是当前平台的可选展示适配，不是 skill 的通用契约。
