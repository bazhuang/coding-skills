---
name: or-ontology-time-discretization-adaptation
description: Adapt an or_ontology to time-discretized data schema. Use when Codex needs to convert an existing or_ontology into a period-level or_ontology aligned to data that has been time-discretized, while preserving modeling semantics and exposing any unresolved schema gaps.
---

# OR Ontology Time Discretization Adaptation

## 职责与边界

本 skill 只做一件事：基于 `or_ontology` 和 `discretized_schema`，把原始 `or_ontology` 适配为与时间离散后数据 schema 对齐的时段级 `or_ontology_time_discretized`。

术语口径：

- 业务本体：`business_ontology`
- `or_ontology`：运筹建模本体
- 运筹 DSL：`or_dsl`

这里的“适配”专指：原本按较粗时间粒度组织的数据被离散为时段级表达后，同步调整 `or_ontology` 的对象绑定、字段引用、粒度描述、目标引用和约束引用。业务语义必须保持不变，只能改变数据承载、时间粒度和字段引用。

本 skill 是 `or_ontology` 适配器，不是业务重建器、schema 生成器、数据处理器、求解器代码生成器或运行时执行器。

## 输入与引用

适用输入：

- `or_ontology`：原始 `or_ontology`，应包含问题框架、算法对象、目标系统、约束系统、映射依据和待确认问题。
- `discretized_schema`：时间离散后的数据表 schema，可以是 SQL DDL、表结构清单或字段级 schema 描述。

读取顺序：

1. [execution_plan.yaml](execution_plan.yaml)：内部执行阶段定义
2. [references/time-discretization-adaptation-rules.md](references/time-discretization-adaptation-rules.md)：适配规则
3. [references/input_or_ontology.schema.json](references/input_or_ontology.schema.json)：输入本体约束
4. [references/discretization_adaptation_notes.schema.json](references/discretization_adaptation_notes.schema.json)：中间适配分析结果 schema
5. [references/or_ontology_time_discretized.schema.json](references/or_ontology_time_discretized.schema.json)：最终输出 schema

中间适配分析结果记录离散表 schema 清单、适配依据、对象映射、字段替换和未解决缺口；最终输出只保留可供后续建模使用的 `or_ontology_time_discretized` 结果，不内嵌中间推理过程。

## 执行边界

必须做：

- 识别离散化后的时间轴、时段字段、来源标识字段和时段化数值字段
- 判断原 `or_ontology` 中每个对象与离散后表的映射关系
- 把对象绑定、目标引用、约束引用和粒度描述调整为时段级表达
- 对所有映射到离散化主表的对象，用 `discretized_schema` 中的目标表结构完整重建 `table_schema`
- `table_schema.fields[*].type` 必须保留 `discretized_schema` 中字段的原始数据库类型文本，不做通用类型归一化
- `table_schema.unique_keys` 必须从 `discretized_schema` 中目标离散化表的唯一键证据继承；没有目标表唯一键证据时不要补造
- 保留业务对象角色、目标含义和约束语义
- 显式暴露无法稳定适配的对象、字段和规则缺口

不得做：

- 重新发明业务对象体系，或静默删除原 `or_ontology` 中的重要对象、目标或约束
- 输出 `or_ontology` 之外的实现形态，例如离散化 SQL、运行时代码或求解结果
- 读取实例数据，执行实例数据展开、数值求解或结果计算
- 凭空编造离散化表、字段或时间粒度
- 处理与时间离散无关的泛化数据改造任务
- 把 `table_schema` 写成补丁式调整结果，例如只列新增时段字段、只保留关键字段或只保留被替换字段
- 从原始 `or_ontology.table_schema.fields` 搬运目标离散化表中不存在的字段

## 适配原则

- 语义优先：原 `or_ontology` 的业务目标、对象角色和约束含义优先保留；只调整数据粒度、字段引用、表绑定和时间描述。
- schema 证据优先：只根据 `discretized_schema` 中可见的表和字段完成适配，不能假设不存在于输入中的离散化结构。
- 时段表优先：原 `or_ontology` 中 `attached` 或 `referenced` 的 `node`、`edge` 对象，只要能稳定识别对应的离散化主表，就应改写到离散化表。
- 完整 schema 重建：若对象在输出中仍为 `attached` 且已映射到离散化主表，其 `table_schema` 必须按 `discretized_schema` 中目标表完整重建；完整性以目标离散化表为准，不以原始粗粒度表为准。
- 类型完整性也是完整 schema 的一部分：`varchar(64)`、`bigint(20) unsigned`、`decimal(20,4)`、`datetime`、`date` 等类型文本应与目标表证据一致。
- 唯一键继承：`unique_keys` 与字段、主键一样，以 `discretized_schema` 中目标离散化表的结构证据为准；没有目标表唯一键证据时不要补造。
- 时间粒度一致：`problem_frame.time_granularity`、`algorithm_objects.objects[*].grain`、目标和约束中的 `related_tables` / `related_fields` 必须同步更新。
- 时段字段优先：总量、需求量、供给量、处理量优先映射到时段分摊数值字段；最低量优先映射到时段下限字段；能力或容量上限优先映射到时段能力字段；起止日期、覆盖区间或计划周期优先收敛到时段标识字段。
- schema 引用闭环：最终 `table_schema.fields`、`primary_key`、`unique_keys` 只能来自中间分析中的目标表 schema 证据；目标表中不存在的字段不得在最终表 schema 中出现。
- 保守表达缺口：若只能确认字段被时段化但无法稳定判断具体替换关系，先记录到中间分析结果，再在最终 `open_questions` 中保守表达。

## 工作流程

按下面顺序工作，不要跳步。

### 1. 校验输入结构

- 用输入 schema 检查原 `or_ontology` 顶层结构是否完整
- 识别 `discretized_schema` 中的离散化表、字段、主键、唯一键和注释

### 2. 提取离散化适配信号

- 把 `discretized_schema` 中每张表解析成 `schema_inventory`，记录完整字段、主键、唯一键和表注释证据
- 识别原对象到离散化表的候选映射
- 为每个候选对象输出 `target_schema_evidence`，明确最终表 schema 允许使用的目标表字段全集
- 识别时间字段、来源字段和时段化数值字段
- 判断哪些目标项和约束项需要更新数据引用

这一阶段输出中间分析结果，不直接生成最终 `or_ontology_time_discretized`。

### 3. 生成适配草案

- 基于中间分析结果改写问题框架、对象、目标、约束
- 对映射到离散化主表的 attached 对象，按 `target_schema_evidence` 完整重建 `table_schema`
- 对 `table_schema.unique_keys`，按 `discretized_schema` 中目标离散化表的唯一键证据继承；不要沿用原 `or_ontology` 的旧唯一键，也不要自行重算或补造
- 不在最终结果中内嵌中间推理细节；适配依据、对象映射、字段替换和改写范围保留在中间分析 artifact 中
- 对无法稳定适配的部分保留到最终结果的 `open_questions`
- 对所有保留 `attached` 绑定的对象，必须输出完整 `table_schema`，不能以“仅保留关键字段”的方式压缩结果
- 不得把目标表中的原始数据库类型改写为 `string`、`float`、`boolean` 等抽象类型

### 4. 校验 schema 对齐

- 逐个检查最终 `table_schema.table_name` 是否有明确目标表证据
- 逐个检查 `table_schema.fields[*].name` 是否与目标表字段集合一致
- 逐个检查 `table_schema.fields[*].type` 是否与目标表字段的原始数据库类型文本一致
- 删除目标离散化表中不存在的旧字段，补齐目标离散化表中遗漏的字段
- 检查目标、约束、`supporting_fields` 和 `related_fields` 是否引用目标表中真实存在的字段
- 无法找到目标字段时写入 `open_questions`，不要引用不存在字段

## 输出要求

- 输出一个中间分析 artifact 和一个最终适配后的 `or_ontology_time_discretized`
- 最终输出必须符合 [references/or_ontology_time_discretized.schema.json](references/or_ontology_time_discretized.schema.json)
- 最终输出保持 `or_ontology` 结构，不改写成其他表达形态
- 最终输出中映射到离散化主表的 `table_schema` 必须与 `discretized_schema` 的目标表结构一致
- 最终输出不包含中间推理字段；无法稳定适配的问题通过 `open_questions` 表达
