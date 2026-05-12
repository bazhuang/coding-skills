# Spatial Path Query Rules

本文件定义“图数据库建模 SQL -> 独立可行路径查询定义 `graph_path_queries`”的核心规则。

## 1. 总体目标

- 只基于 `graph_modeling_sql` 形成路径查询定义
- 查询定义只表达运行时如何取路径，不执行路径搜索
- `graph_modeling_sql` 必须自带图构件语义角色
- 输出独立的 `graph_path_queries`

## 2. SQL 证据提取规则

从 `graph_modeling_sql` 中提取以下信息：

- `CREATE TAG` / `CREATE EDGE` 语句 comment 中的 `table_type`
- 节点标签：图数据库节点的 label 或 tag 名称
- 边类型：图数据库 relationship type 或 edge type 名称
- 属性承载：节点属性、边属性与图建模 SQL 中表名或属性命名空间的对应关系
- 版本字段：节点属性和边属性中的 `version_id`
- 跳数范围：SQL 或注释中明确出现的路径长度限制

若 SQL 使用不同图数据库方言，应把语义归一为查询定义字段，但查询文本仍优先使用 Cypher 风格输出，除非输入明确要求其他方言。

不要从图数据库字段中抽取供给量、需求量、价格、能力、最小量等建模数值；这些数值字段不属于路径查询定义。

## 3. table_type 驱动的图构件识别规则

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

优先证据顺序：

1. SQL comment 中的 `table_type`
2. `CREATE TAG` / `CREATE EDGE` 的名称
3. SQL comment 中的其他业务说明
4. SQL 中的属性名、属性命名空间和索引名

若 `table_type` 能稳定识别多个供给或需求标签，应全部保留到 `path_parameters.start_nodes.values` 或 `path_parameters.end_nodes.values`。若 `table_type` 缺失，才退回到 tag、edge 名称和 SQL 注释做辅助判断；此时查询可以形成结构化草案，但必须在 `unresolved_gaps` 中说明角色证据不足。

查询语句中的命名必须遵循 `graph_modeling_sql`：

- 若图 SQL 中 `table_type:supply_node` 的 tag 名为 `monthly_resource_pool`，起点标签列表使用 `monthly_resource_pool`
- 若图 SQL 中 `table_type:demand_node` 的 tag 名为 `monthly_demand_pool`，终点标签列表使用 `monthly_demand_pool`
- 若无法识别图 SQL 的 `table_type` 或标签，应写入 `unresolved_gaps`

## 4. 边类型规则

路径中允许经过的边类型只来自：

- SQL 中 `CREATE EDGE ... comment='table_type:transport'` 的边
- SQL 中 `CREATE EDGE ... comment='table_type:link'` 的边
- 在 comment 缺失时，才使用 SQL edge 名称和注释做辅助判断

若 SQL 中有多个可用边类型，查询语句中应使用 `:edge_a|edge_b` 形式组合。不要加入版本、审计、元数据或与供需路径无关的边。

## 5. version_id 占位符规则

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

无法判断属性路径时，保守填写结构化字段并把属性路径缺口写入 `unresolved_gaps`。

节点版本过滤中的属性路径必须遵循图数据库建模 SQL。

## 6. 跳数范围规则

- 默认跳数范围为 `1..10`
- 若输入明确给出跳数范围，按输入覆盖默认值
- 最终结果不单独输出跳数字段；跳数范围直接体现在 `query_template` 中
- 不要把默认跳数视为业务证据；如需说明，只能在最终 `notes` 中简短写明“未发现输入跳数，使用默认 1..10”

## 7. 最终查询定义规则

最终输出必须是独立 `graph_path_queries`，包含：

- `query_language`
- `version_id_placeholder`
- `path_queries`
- `unresolved_gaps`

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

详细推理过程只能保存在中间 artifact `graph_path_query_analysis` 中，包括：

- `derivation_basis`
- `table_type_evidence`
- SQL 证据清单
- 详细 SQL 解析说明

最终 `graph_path_queries` 不能重复这些内容。若确实需要说明 SQL 证据，只能写入 `path_queries[*].notes`，且应控制为简短结果说明，不展开推理链。

最终 `path_queries` 不输出面向下游的工作定位字段，例如 `downstream_usage`。

## 8. 不确定性处理

以下情况必须暴露：

- 起点或终点标签无法稳定识别
- transport/link 边类型无法稳定识别
- 节点或边的 `version_id` 属性路径不明确
- 跳数范围缺少业务依据
- SQL 方言无法稳定转换为 Cypher 查询
- table_type 角色注释缺失或不完整

不确定性不应阻止输出 `graph_path_queries`，但应写入 `unresolved_gaps`。
