# Time Discretization Adaptation Rules

本文件定义“原运筹算法本体 `or_ont` -> 适配时间离散后 schema 的 `or_ont_time_discretized`”的核心规则。

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

若表注释中明确出现“时间拆分结果”“按时间分配”“按时间分摊”等描述，应作为强证据。

## 3. 对象适配规则

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
- `table_schema` 必须输出离散化后的完整主表 schema，而不是只保留关键时段字段与数值字段
- 若原输入 `or_ont` 已为该对象保留了主表 schema，适配后不得把 `table_schema` 压缩成更短的字段子集
- 字段顺序、`primary_key`、可稳定识别的 `indexes` 与 `foreign_keys` 应整体保留
- 输出口径应是“完整重写后的主表 schema”，不要采用补丁式增删说明

### referenced 对象

- `supporting_tables` 优先替换为离散化表名
- `supporting_fields` 优先替换为时段字段和分摊字段

## 4. 字段替换规则

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

## 5. 目标适配规则

- `objective_terms` 的 `business_meaning` 原则上保持不变
- `related_tables` 和 `related_fields` 必须切换到离散化后的数据来源
- 若目标原本是月度总目标，适配后应表达为“跨时段聚合的总目标”或“逐时段累计的总目标”
- 不要把 `or_ont` 直接重写成求解器公式

## 6. 约束适配规则

- 原约束的业务含义优先保留
- 约束的数据引用要改为时段级表与字段
- 若原约束适用于整月总量，适配后通常应明确其是：
  - 单时段约束
  - 跨时段累计约束
  - 兼具时段内与跨时段含义的规则
- 若 `time_period` 是适配成立的必要条件，应将其反映到 `business_meaning` 或 `notes`

## 7. 不确定性处理

遇到以下情况时，不要强行完成适配：

- 找不到稳定的离散化主表
- 只能猜测字段对应关系
- 原约束在离散化后究竟是逐时段还是跨时段累计，缺乏足够证据
- 原对象在离散化后被拆成多张表，但分工不清

这类问题应通过以下位置显式暴露：

- 中间产物里的 `unresolved_gaps`
- 最终产物里的 `open_questions`

适配依据、对象映射、字段替换和改写范围属于中间解释信息，应保留在中间产物中，不内嵌到最终适配后的 `or_ont_time_discretized`。
