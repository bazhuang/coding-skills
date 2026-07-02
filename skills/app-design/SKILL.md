---
name: app-design
description: "当用户要求应用设计、架构设计、数据库设计、现有应用功能设计，或需要把本体模型推进成规格文档时使用。基于本体图谱和需求基线生成 app-design.md、按目标类型裁剪的数据库产物、app-contract.yaml；支持 Java/Spring Boot、Python/FastAPI、Electron/Vue、纯前端和现有项目增量设计。"
---

# 应用设计

将已有业务本体和需求基线转化为应用架构、持久化决策、应用表面映射、规则/SOP 契约。

<HARD-GATE>
当本 skill 被用于应用设计、架构设计、数据库设计或规格生成时，在展示应用设计并获得用户批准之前，不要调用实现技能、编写业务代码、搭建项目或生成实现。

默认允许一次性生成完整 draft，但必须在文档末尾列出「当前审批点」。用户明确要求逐步设计/边聊边确认时，按章节展示并等待批准。无论哪种模式，未获得用户明确批准前不得进入实现。
</HARD-GATE>

## 产物

| 产物 | 路径 | 说明 |
|---|---|---|
| 应用设计文档 | `docs/app-design.md` | 人类可读设计说明 |
| 应用契约 | `docs/contracts/app-contract.yaml` | 结构化追溯契约；后端 target 可作为 code-generation 输入 |
| 权威 DDL | `docs/contracts/db-schema.sql` | 仅在新增/修改数据库表，或兼容下游明确需要 no-op SQL 时生成 |
| 数据库说明 | `docs/db-schema.md` | 仅在生成 DDL 时生成；指向权威 DDL，不重复维护第二份 SQL |

按 `target_kind` 裁剪产物：

| target_kind | 必需产物 |
|---|---|
| `backend-java` / `backend-python` | `docs/app-design.md`、`docs/contracts/db-schema.sql`、`docs/db-schema.md`、`docs/contracts/app-contract.yaml` |
| `desktop-electron-feature` | `docs/app-design.md`、`docs/contracts/app-contract.yaml`；DB 文件按持久化决策生成 |
| `frontend-only-feature` / `existing-app-feature` | `docs/app-design.md`、`docs/contracts/app-contract.yaml`；DB 文件按需生成 |
| `docs-or-process` | `docs/app-design.md`；结构化契约可选 |

## 必读与按需参考

先读本文件，再按场景读取 references：

| 场景 | 读取 |
|---|---|
| 确认设计目标类型与技术规范 | `references/implementation-target-guidelines.md` |
| Java/Python 后端 target | `references/backend-tech-guidelines.md`，再按语言读取 `backend-java-tech-guidelines.md` 或 `backend-python-tech-guidelines.md` |
| Electron/Vue 桌面端功能 | `references/mapping-electron-vue.md` |
| 设计数据库或生成 DDL | `references/db-design-rules.md` |
| 生成接口、规则、SOP 映射 | `references/ontology-mapping-rules.md` |
| 生成或校验后端契约 | `references/app-contract-template.yaml`、`references/app-contract.schema.json` |
| 生成或校验非后端 traceability 契约 | `references/app-contract-v2-template.yaml`、`references/app-contract-v2.schema.json` |
| 规范自审与通用设计质量检查 | `references/design-review-checklist.md` |

只读取当前任务需要的 reference，不要一次性加载所有细节。

## 工作流程

### 1. 探索上下文

- 检查项目文件、已有 `docs/` 产物和最近设计材料。
- 读取 `docs/ontology_schema.json`、`docs/brd.md`、`docs/requirements-baseline.json`、`docs/contracts/acceptance-tests.yaml`。
- 如果缺少本体或需求基线，提示用户先回到 ontology-modeling；不要凭空设计。

### 2. 确认设计目标类型与技术规范

- 先读取 `references/implementation-target-guidelines.md`。
- 从用户请求、现有项目、构建文件、`AGENTS.md`、历史设计材料中判断 `target_kind`。
- 只有 `target_kind` 是 `backend-java` 或 `backend-python`，才要求确认 Java/Spring Boot 或 Python/FastAPI，并读取对应后端规范。
- `existing-app-feature` 必须优先遵循现有项目技术栈、模块边界和仓库内规范；不要为了适配模板强行改技术栈。
- 在 `docs/app-design.md` 和 `docs/contracts/app-contract.yaml` 中记录 `target_kind`、实现语言/框架、采用的 guideline。

### 3. 逐步澄清

最多问 3 个关键问题。优先确认：

- 成功标准和范围边界
- 设计目标类型或现有项目技术约束
- 会影响持久化、应用表面映射、接口/IPC/UI 契约的关键业务口径

其余细节从本体和需求基线推断，并在设计中标注。

### 4. 提出设计方案

提出 2-3 种应用设计方案，聚焦业务分解和数据流，不重新争论已被技术规范锁定的框架选型。

推荐方案应说明：

- 模块边界
- 数据流
- 是否需要异步任务、快照、汇总读模型
- 主要权衡

### 5. 边设计边写文档

按以下顺序同步生成和更新文件：

1. 架构与模块设计 -> `docs/app-design.md`
2. 数据流与关键业务流程 -> `docs/app-design.md`
3. 持久化决策与数据库设计 -> `docs/app-design.md`，必要时 `docs/contracts/db-schema.sql` + `docs/db-schema.md`
4. 行为/应用表面、规则、SOP 映射 -> `docs/contracts/app-contract.yaml` + `docs/app-design.md`
5. 错误处理、状态流转、测试策略 -> `docs/app-design.md`

涉及持久化判断、数据库设计或 DB 产物时必须读取并遵守 `references/db-design-rules.md`。

应用表面与逻辑映射必须读取并遵守 `references/ontology-mapping-rules.md`。Electron/Vue target 还必须读取 `references/mapping-electron-vue.md`。

## 设计重点

基于本体推导设计，但不要机械 CRUD 化。需要判断是否存在：

- 数据维护模块与业务编排模块分离
- 多轮迭代与历史版本保留
- 输入快照与结果可复现
- 长耗时生成任务的异步执行
- 明细结果之外的汇总读模型
- 目标函数策略化
- 主数据编码与名称展示分离
- 单位、税价、统计口径结构化

这些检查项的完整列表见 `references/design-review-checklist.md`。

## 结构化契约要求

结构化契约根据 `target_kind` 选择格式：

- `backend-java` / `backend-python`：使用现有 Java/Python contract 模板，作为后端 code-generation 的权威输入。
- `desktop-electron-feature` / `frontend-only-feature` / `existing-app-feature`：使用 app-contract v2 traceability 模板，记录对象、行为、规则、SOP 到 UI/service/IPC/helper/API 的映射；该契约默认不直接交给后端 code-generation。

后端 legacy contract 必须包含：

- `project`：后端语言、basePackage、模块列表等项目元信息
- `objects[]`：本体对象到表、行为、Controller/Biz/Service 的映射
- `rules[]`：本体规则到代码位置的映射
- `sops[]`：SOP 到 Biz 编排方法的映射

v2 traceability contract 必须包含：

- `version: 2`
- `project.targetKind` 与 `project.implementation`
- `objects[]`：对象、可选表名、`persistence`、行为到 `surfaces` 的映射
- `rules[]`：规则到 `Module.method()`、`Component.method()` 或 `file:function` 的映射
- `sops[]`：SOP 到跨 UI/service/IPC/main/external 的调用链映射

Markdown 表格只是人读视图，必须与 YAML 保持一致。

## 准出门禁

设计完成后读取 `references/design-review-checklist.md`，并完成以下检查：

1. `docs/app-design.md` 无 TBD/TODO、无明显矛盾、范围清晰。
2. 每个对象都有持久化决策；若生成 `docs/contracts/db-schema.sql`，必须满足数据库规约。
3. `docs/contracts/app-contract.yaml` 可解析，且符合 schema。
4. `app-contract.yaml` 覆盖 `ontology_schema.json` 中全部 objects、rules、sop_flows。
5. 需要建表的对象，`app-contract.yaml` 的表名与 `db-schema.sql` 一致；无需建表的对象必须说明 `persistence` 与原因。
6. 覆盖率不达 100% 不得进入实现。非后端 v2 契约不得直接进入后端 code-generation。
7. `docs/app-design.md` 末尾列出「当前审批点」，并明确用户批准后才能进入实现。

最终向用户汇报：

```text
设计文档已完成并保存到 docs/app-design.md。
结构化契约已生成：应用表面/规则/SOP 映射在 docs/contracts/app-contract.yaml。
契约覆盖率：对象 X/X，规则 Y/Y，SOP Z/Z。
数据库影响：有/无（如有，DDL 在 docs/contracts/db-schema.sql）。
请审查完整规范与契约，确认后再进入实现。
```

## 可视化伴侣

如果设计内容明显涉及架构图、ER 图、流程图、本体图谱或界面布局，可以单独询问用户是否需要可视化伴侣。

该询问必须单独成句，不与澄清问题混在一起。用户拒绝时，继续文本设计。

## 关键原则

- 本体优先，契约准出。
- 少问问题，多用已有文件推断。
- 设计和文档同步写入。
- 不把实现细节提前到设计阶段。
- 保持 skill 主文件短小，细则放 references。
