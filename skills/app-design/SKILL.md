---
name: app-design
description: "当用户要求应用设计、架构设计、数据库设计，或需要把本体模型推进成规格文档时使用。基于本体图谱生成 app-design.md、db-schema.sql、app-contract.yaml。"
---

# 应用设计

将已有业务本体和需求基线转化为应用架构、数据库设计、接口/规则/SOP 契约。

<HARD-GATE>
当本 skill 被用于应用设计、架构设计、数据库设计或规格生成时，在展示应用设计并获得用户批准之前，不要调用实现技能、编写业务代码、搭建项目或生成实现。
</HARD-GATE>

## 产物

| 产物 | 路径 | 说明 |
|---|---|---|
| 应用设计文档 | `docs/app-design.md` | 人类可读设计说明 |
| 权威 DDL | `docs/contracts/db-schema.sql` | 可执行 MySQL DDL |
| 数据库说明 | `docs/db-schema.md` | 指向 DDL 的说明文档 |
| 应用契约 | `docs/contracts/app-contract.yaml` | 代码生成的机器可消费契约 |

## 必读与按需参考

先读本文件，再按场景读取 references：

| 场景 | 读取 |
|---|---|
| 确认后端语言与技术栈 | `references/backend-tech-guidelines.md`，再按语言读取 `backend-java-tech-guidelines.md` 或 `backend-python-tech-guidelines.md` |
| 设计数据库或生成 DDL | `references/db-design-rules.md` |
| 生成接口、规则、SOP 映射 | `references/ontology-mapping-rules.md` |
| 生成或校验应用契约 | `references/app-contract-template.yaml`、`references/app-contract.schema.json` |
| 规范自审与通用设计质量检查 | `references/design-review-checklist.md` |

只读取当前任务需要的 reference，不要一次性加载所有细节。

## 工作流程

### 1. 探索上下文

- 检查项目文件、已有 `docs/` 产物和最近设计材料。
- 读取 `docs/ontology_schema.json`、`docs/brd.md`、`docs/requirements-baseline.json`、`docs/contracts/acceptance-tests.yaml`。
- 如果缺少本体或需求基线，提示用户先回到 ontology-modeling；不要凭空设计。

### 2. 确认技术规范

- 先读取 `references/backend-tech-guidelines.md`。
- 从现有项目、构建文件、用户要求中判断后端语言。
- 若无法判断，向用户确认 Java/Spring Boot 或 Python/FastAPI；该问题计入最多 3 个澄清问题。
- 只读取所选语言的专用规范。
- 在 `docs/app-design.md` 和 `docs/contracts/app-contract.yaml` 中记录后端语言。

### 3. 逐步澄清

最多问 3 个关键问题。优先确认：

- 成功标准和范围边界
- 后端语言或技术约束
- 会影响数据库/接口契约的关键业务口径

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
3. 数据库设计 -> `docs/contracts/db-schema.sql` + `docs/db-schema.md`
4. 行为/接口、规则、SOP 映射 -> `docs/contracts/app-contract.yaml` + `docs/app-design.md`
5. 错误处理、状态流转、测试策略 -> `docs/app-design.md`

数据库设计必须读取并遵守 `references/db-design-rules.md`。

接口与逻辑映射必须读取并遵守 `references/ontology-mapping-rules.md`。

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

`docs/contracts/app-contract.yaml` 是 code-generation 的权威输入，必须包含：

- `project`：后端语言、basePackage、模块列表等项目元信息
- `objects[]`：本体对象到表、行为、Controller/Biz/Service 的映射
- `rules[]`：本体规则到代码位置的映射
- `sops[]`：SOP 到 Biz 编排方法的映射

Markdown 表格只是人读视图，必须与 YAML 保持一致。

## 准出门禁

设计完成后读取 `references/design-review-checklist.md`，并完成以下检查：

1. `docs/app-design.md` 无 TBD/TODO、无明显矛盾、范围清晰。
2. `docs/contracts/db-schema.sql` 满足数据库规约。
3. `docs/contracts/app-contract.yaml` 可解析，且符合 schema。
4. `app-contract.yaml` 覆盖 `ontology_schema.json` 中全部 objects、rules、sop_flows。
5. `app-contract.yaml` 的表名与 `db-schema.sql` 一致。
6. 覆盖率不达 100% 不得进入 code-generation。

最终向用户汇报：

```text
设计文档已完成并保存到 docs/app-design.md。
结构化契约已生成：DDL 在 docs/contracts/db-schema.sql，接口/规则/SOP 映射在 docs/contracts/app-contract.yaml。
契约覆盖率：对象 X/X，规则 Y/Y，SOP Z/Z。
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
