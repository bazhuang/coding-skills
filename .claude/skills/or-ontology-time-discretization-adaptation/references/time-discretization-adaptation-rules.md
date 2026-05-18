# Time Discretization Adaptation Rules

本文件定义“原 `or_ontology` -> 适配时间离散后 schema 的 `or_ontology_time_discretized`”的核心规则。

## 1. 总体目标

- 保持业务建模语义稳定
- 将数据承载切换到离散后的时段表
- 让后续建模直接面向 period-level 数据

## 2. 典型离散化证据

在 `discretized_schema` 中，以下字段通常代表离散化已经发生：

- `time_period`
  - 时段起点或时窗标识
- `source_id`
  - 指回原始粗粒度记录的来源主键
- `allocated_*`
  - 原总量字段被按时段分摊后的数值字段
- `discretized_*`
  - 原总量、最低量、能力或容量字段被按时段拆分后的数值字段

若表注释中明确出现“时间拆分结果”“按时间分配”“按时间分摊”等描述，应作为强证据。

## 3. schema 证据抽取规则

在生成最终 `or_ontology_time_discretized` 之前，必须先把 `discretized_schema` 转成可引用的 `schema_inventory`：

- 每张离散化表必须记录 `table_name`、完整 `fields`、`primary_key`、可识别的 `unique_keys` 和 `schema_source`
- `schema_source` 来自 `discretized_schema` 的表才可作为离散化主表证据
- `fields[*].name` 是最终 `table_schema.fields` 的允许字段全集
- `primary_key` 和 `unique_keys` 应来自同一张目标表，不能沿用原始表的主键或唯一键
- `unique_keys` 应从 `discretized_schema` 中目标离散化表的 `UNIQUE KEY`、唯一索引或等价唯一约束抽取；如果目标表没有唯一键证据，最终 `table_schema.unique_keys` 应省略或为空，不要从原始 `or_ontology` 补造
- 若原对象只能保留为未离散化维表或静态参考表，必须把原因写入 object mapping 的缺口或说明，不得伪装成离散化主表

`field_rewrites` 只描述业务语义引用如何从旧字段转到新字段，不能作为最终表 schema 的字段来源。
最终表 schema 的字段来源只能是 `schema_inventory` 中对应目标表的字段清单。唯一键字段组合也只能引用目标表字段清单中存在的字段。

## 4. 对象适配规则

### problem_frame

- `time_granularity` 必须改为离散后的时段粒度表达
- `problem_type`、`optimization_goal`、`business_scope` 原则上保持不变

### algorithm_objects

- `object_category` 与 `object_type` 原则上保持不变
- `grain` 必须改写为时段级对象粒度
- 若原对象对应离散化主表，应优先更新：
  - `schema_binding_status`
  - `supporting_tables`
  - `supporting_fields`
  - `table_schema`
- `resource` 对象即使没有 `table_schema`，也应在 `grain`、`business_role` 和约束/目标引用中体现 period-level 语义

### attached 对象

- 若能稳定识别离散化主表，`table_schema` 应切换到离散化表
- `table_schema` 必须输出目标离散化表的完整 schema，而不是只保留关键时段字段与数值字段
- “完整”指完整保留 `discretized_schema` 中目标表的字段、字段类型文本、主键、唯一键和注释证据，不是完整保留原始 `or_ontology.table_schema`
- 目标离散化表中不存在的原始字段不得进入最终 `table_schema.fields`
- 原日期区间字段如果已经被离散化时段字段替代，且目标表中没有保留原字段，应从 `table_schema.fields` 删除，并通过字段替换、业务含义或 `open_questions` 解释其语义去向
- 字段顺序、`primary_key`、可稳定识别的 `unique_keys` 与 `foreign_keys` 应按目标离散化表整体保留
- `unique_keys` 不得沿用原始粗粒度表的旧唯一键；只有目标离散化表中可稳定识别的唯一键字段组合才能进入最终输出
- 输出口径应是“基于目标表 schema 的完整重建”，不要采用补丁式增删说明

### referenced 对象

- `supporting_tables` 优先替换为离散化表名
- `supporting_fields` 优先替换为时段字段和分摊字段

## 5. 字段替换规则

优先保留字段语义，再完成字段名切换。

常见替换模式包括：

- 总量类语义 -> 对应的时段分摊数值字段
- 最低量类语义 -> 对应的时段下限字段
- 能力上限类语义 -> 对应的时段能力字段
- 原日期区间类语义 -> 对应的时段标识字段

这里强调的是语义映射，不是固定命名映射。
不要把 demo、样例库或某个场景里的字段名直接当成 skill 的通用规则。

如果离散化表同时保留原字段和分摊字段：

- 面向运筹建模的数量、能力、最小量约束，优先引用分摊字段
- 说明性字段、维表字段和身份字段仍可保留原语义字段
- 这种“优先引用分摊字段”只作用于 `related_fields`、`supporting_fields` 和语义引用，不意味着可以删减 `table_schema` 中仍然有效的其他字段

## 6. table_schema 对齐校验

生成最终 `or_ontology_time_discretized` 前，必须执行以下一致性检查：

- 对每个已映射到离散化主表的 attached 对象，`table_schema.table_name` 必须等于 `target_schema_evidence.table_name`
- `table_schema.fields[*].name` 集合必须等于 `target_schema_evidence.allowed_fields`；不能多出旧字段，也不能漏掉目标表字段
- `table_schema.fields[*].type` 必须与目标表 schema 证据中的原始数据库类型文本一致；不能把 `varchar(64)` 重写成 `string`，也不能把 `decimal(20,4)` 重写成 `float`
- `table_schema.primary_key` 必须等于目标表证据中的 `primary_key`
- `table_schema.unique_keys` 若输出，必须等于目标表证据中的 `unique_keys`，且其中每个字段都必须存在于目标表字段集合中
- `related_fields`、`supporting_fields`、目标项和约束项引用的字段必须存在于目标表证据中；不存在时不得引用，应进入 `open_questions`
- 若某个原字段在 `excluded_source_fields` 中，它不得出现在最终 `table_schema.fields` 中

这一步是最终输出的一部分，不是外部执行器补救逻辑。

## 7. 目标适配规则

- `objective_terms` 的 `business_meaning` 原则上保持不变
- `related_tables` 和 `related_fields` 必须切换到离散化后的数据来源
- 若目标原本是月度总目标，适配后应表达为“跨时段聚合的总目标”或“逐时段累计的总目标”
- 不要把 `or_ontology` 直接重写成求解器公式

## 8. 约束适配规则

- 原约束的业务含义优先保留
- 约束的数据引用要改为时段级表与字段
- 若原约束适用于整月总量，适配后通常应明确其是：
  - 单时段约束
  - 跨时段累计约束
  - 兼具时段内与跨时段含义的规则
- 若 `time_period` 是适配成立的必要条件，应将其反映到 `business_meaning` 或 `notes`

## 9. 不确定性处理

遇到以下情况时，不要强行完成适配：

- 找不到稳定的离散化主表
- 只能猜测字段对应关系
- 原约束在离散化后究竟是逐时段还是跨时段累计，缺乏足够证据
- 原对象在离散化后被拆成多张表，但分工不清

这类问题应通过以下位置显式暴露：

- 中间产物里的 `unresolved_gaps`
- 最终产物里的 `open_questions`

适配依据、对象映射、字段替换和改写范围属于中间解释信息，应保留在中间产物中，不内嵌到最终适配后的 `or_ontology_time_discretized`。
