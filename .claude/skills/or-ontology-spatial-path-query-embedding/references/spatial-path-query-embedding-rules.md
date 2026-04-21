# Spatial Path Query Embedding Rules

本文件定义“时间离散后的运筹算法本体 `or_ont_time_discretized` + 图数据库建模 SQL -> 嵌入可行路径查询的 `or_ont_path_query_embedded`”的核心规则。

## 1. 总体目标

- 保持已有 `or_ont` 语义稳定
- 为后续空间离散化补充可执行的图数据库路径查询定义
- 查询定义只表达运行时如何取路径，不执行路径搜索
- 图数据库建模 SQL 只服务新增路径查询模块，不参与改写 `or_ont` 主体

## 1.0 双数据库系统

本 skill 涉及两套数据库系统：

1. 业务数据系统
   - 主系统
   - 由 `or_ont_time_discretized.algorithm_objects.objects[*].table_schema` 等字段体现
   - 支撑 `or_ont` 中的业务对象、目标、约束、数值字段和时间离散字段
   - 后续建模、`or_dsl` 转换、模型代码生成和运行时数值计算以这套 schema 为准
2. 图数据库系统
   - 辅助路径系统
   - 由 `graph_modeling_sql` 体现
   - 只用于查询供给节点到需求节点之间的可行路径
   - 只提供连通性、节点标签、边类型和路径级版本过滤，不提供建模数值

两套系统可以共享业务含义，但不能混用职责。图数据库系统的表名、标签名、边类型和属性路径只能进入 `graph_path_query_system`；业务数据系统的 schema 继续留在 `or_ont` 主体中，不能被图数据库 schema 覆盖。

## 1.1 Schema 边界

`or_ont` 主体以 `or_ont_time_discretized` 中已经存在的表 schema 为准。图数据库建模 SQL 通常基于未离散的原始 schema 生成，可能存在：

- 表名与 `or_ont` 中离散化表名不同
- 图标签或边类型与 `or_ont` 对象名不同
- 节点属性路径使用原始表名或图建模中的属性命名空间

这些差异不得导致 `or_ont` 主体发生调整。最终输出只能新增 `graph_path_query_system`；除非只是逐字复制原输入，不能修改：

- `problem_frame`
- `algorithm_objects`
- `objective_system`
- `constraint_system`
- `mapping_rationale`
- 原有 `open_questions`

图 SQL 的表名、标签名、边类型和属性路径只允许出现在路径查询模块及其中的来源依据字段中。

## 2. 对象识别规则

从 `or_ont_time_discretized` 的 `algorithm_objects.objects` 中识别：

- 起点候选：`object_type = supply_node`
- 终点候选：`object_type = demand_node`
- 可经过边候选：`object_type = transport` 或 `object_type = link`

对起点和终点候选，必须先收集 `or_ont_time_discretized` 中可见的表名列表：

- `table_schema.table_name`
- `supporting_tables`

这一步产生的是 `or_ont` 侧的供给表名列表和需求表名列表，用于确认路径查询服务的是哪类本体对象。图查询构件本身优先由图数据库建模 SQL 的 comment 中的 `table_type` 决定。

不要把 `resource`、普通节点或约束项当作图边。若一个对象的类型、图标签或边类型不明确，应写入 `unresolved_gaps`。

## 3. SQL 证据提取规则

从 `graph_modeling_sql` 中提取以下信息：

- `CREATE TAG` / `CREATE EDGE` 语句 comment 中的 `table_type`
- 节点标签：图数据库节点的 label 或 tag 名称
- 边类型：图数据库 relationship type 或 edge type 名称
- 属性承载：节点属性、边属性与图建模 SQL 中表名或属性命名空间的对应关系
- 版本字段：节点属性和边属性中的 `version_id`
- 跳数范围：SQL 或注释中明确出现的路径长度限制

若 SQL 使用不同图数据库方言，应把语义归一为查询定义字段，但查询文本仍优先使用 Cypher 风格输出，除非输入明确要求其他方言。

提取 SQL 证据时，不要把 SQL 中的未离散表名反向替换到 `or_ont` 的 `table_schema.table_name`、`supporting_tables` 或目标/约束引用中。
不要从图数据库字段中抽取供给量、需求量、价格、能力、最小量等建模数值；这些数值字段属于业务数据系统。

## 4. table_type 驱动的图构件识别规则

图建模 SQL 的 comment 中若存在 `table_type`，它是识别图构件角色的最高优先级证据。典型 NebulaGraph 形式：

```sql
CREATE TAG IF NOT EXISTS `monthly_resource_pool` (...) comment='table_type:supply_node';
CREATE EDGE IF NOT EXISTS `monthly_transport_pool` (...) comment='table_type:transport';
```

识别规则：

- `CREATE TAG ... comment='table_type:supply_node'` -> 起点标签集合
- `CREATE TAG ... comment='table_type:demand_node'` -> 终点标签集合
- `CREATE EDGE ... comment='table_type:transport'` -> 可经过边集合
- `CREATE EDGE ... comment='table_type:link'` -> 可经过边集合
- 其他 `table_type`，例如 `passthrough_node`，不是起点或终点，但可以作为路径经过的节点标签证据，不放入边类型集合

`or_ont` 中的表名列表用于校验路径查询角色是否与本体对象一致，而不是决定图构件角色的第一来源。

优先证据顺序：

1. SQL comment 中的 `table_type`
2. `CREATE TAG` / `CREATE EDGE` 的名称
3. `or_ont` 对象的 `table_schema.table_name` 或 `supporting_tables`
4. `or_ont` 对象的 `source_business_entities`
5. `or_ont` 对象的 `object_name`、`object_type` 和 `business_role`

若 `table_type` 能稳定识别多个供给或需求标签，应全部保留到 `start_node.labels` 或 `end_node.labels`。若 `table_type` 缺失，才退回到表名、对象名和业务角色辅助映射；此时查询可以生成结构化草案，但必须标记 `confidence = low` 或 `medium`，并写入缺口。

`or_ont` 的离散化表名是本体角色校验依据，但不自动成为查询语句中的图标签。查询语句中的命名必须遵循 `graph_modeling_sql`：

- 若图 SQL 中 `table_type:supply_node` 的 tag 名为 `monthly_resource_pool`，起点标签列表使用 `monthly_resource_pool`
- 若图 SQL 中 `table_type:demand_node` 的 tag 名为 `monthly_demand_pool`，终点标签列表使用 `monthly_demand_pool`
- 若只能识别 `or_ont` 表名，无法识别图 SQL 的 `table_type` 或标签，应写入 `unresolved_gaps`

## 5. 边类型规则

路径中允许经过的边类型只来自：

- SQL 中 `CREATE EDGE ... comment='table_type:transport'` 的边
- SQL 中 `CREATE EDGE ... comment='table_type:link'` 的边
- 在 comment 缺失时，才使用 `or_ont` 中 `transport` / `link` 对象与 SQL 边名的辅助映射

若 SQL 中有多个可用边类型，查询语句中应使用 `:edge_a|edge_b` 形式组合。不要加入版本、审计、元数据或与供需路径无关的边。

## 6. version_id 占位符规则

最终查询语句必须满足：

- 所有节点版本过滤使用 `{version_id}`
- 所有路径边版本过滤使用 `{version_id}`
- 不得出现具体版本值
- 至少包含边过滤：`ALL(e IN relationships(p) WHERE e.version_id == {version_id})`

若 SQL 证据显示节点属性挂在源表属性命名空间下，可以使用：

```cypher
s.source_table.version_id == {version_id}
d.target_table.version_id == {version_id}
```

若属性直接挂在节点上，可以使用：

```cypher
s.version_id == {version_id}
d.version_id == {version_id}
```

无法判断属性路径时，保守生成结构化字段并把属性路径缺口写入 `unresolved_gaps`。

节点版本过滤中的属性路径必须遵循图数据库建模 SQL。即使 `or_ont` 中已使用离散化表名，查询语句也不得把离散化表名强行写入图查询，除非图 SQL 本身如此建模。

## 7. 跳数范围规则

- 默认跳数范围为 `1..10`
- 若输入明确给出跳数范围，按输入覆盖默认值
- 最终结果不单独输出跳数字段；跳数范围直接体现在 `query_template` 中
- 不要把默认跳数视为业务证据；如需说明，只能在最终 `notes` 中简短写明“未发现输入跳数，使用默认 1..10”

## 8. 最终 or_ont 扩展规则

最终输出必须原样保留原 `or_ont_time_discretized` 顶层结构，并新增：

- `graph_path_query_system.query_language`
- `graph_path_query_system.version_id_placeholder`
- `graph_path_query_system.path_queries`
- `graph_path_query_system.unresolved_gaps`

不要输出 `ontology_preservation_policy` 这类 skill 执行约束字段。原样保留 `or_ont` 主体是生成过程必须遵循的规则，不是最终运筹算法本体需要携带的信息。

每条 `path_queries` 至少描述：

- 查询名称
- `path_parameters.start_nodes`
- `path_parameters.end_nodes`
- `path_parameters.path_edges`
- 查询模板
- 版本过滤策略
- 必要注解

`path_parameters` 是最终路径查询的核心参数组，三项在结构上并列：

- `start_nodes`：起点图 tag / label 列表
- `end_nodes`：终点图 tag / label 列表
- `path_edges`：中间可经过图 edge type 列表

三项都使用相同的参数结构：`graph_type`、`values`，必要时补 `version_filter` 和极简 `notes`。不要在子对象内部重复写 `parameter_name`，因为 `start_nodes`、`end_nodes`、`path_edges` 这些 key 已经表达参数名；不要把起点和终点写成对象详情、把边写成裸数组。

不要把中间分析过程、长篇解释或调试说明写入既有 `objective_system`、`constraint_system` 或 `mapping_rationale`。

详细推理过程只能保存在中间 artifact `graph_path_query_analysis` 中，包括：

- `mapping_basis`
- `derivation_basis`
- `table_type_evidence`
- SQL 证据清单
- 详细 schema 差异说明

最终 `or_ont_path_query_embedded` 不能重复这些内容。若确实需要在最终结果说明图 SQL 与 `or_ont` schema 的关系，只能写入 `path_queries[*].notes`，且应控制为简短结果说明，不展开推理链。

最终 `path_queries` 不输出面向下游的工作定位字段，例如 `downstream_usage`。下游用途、路径查询为何存在、如何辅助空间离散化等说明属于 skill 自身定位或中间分析内容，不进入最终 `or_ont`。

## 9. 不确定性处理

以下情况必须暴露：

- 起点或终点标签无法稳定识别
- transport/link 对象无法映射到图边类型
- 节点或边的 `version_id` 属性路径不明确
- 跳数范围缺少业务依据
- SQL 方言无法稳定转换为 Cypher 查询
- 图 SQL 表名与 `or_ont` 表名存在差异，且缺少稳定映射证据

不确定性不应阻止输出完整 `or_ont_path_query_embedded`，但应降低对应查询的 `confidence`。
