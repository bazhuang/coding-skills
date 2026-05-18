---
name: or-spatial-path-query
description: Derive graph database feasible path query definitions from graph modeling SQL. Use when Codex needs version-placeholder supply-to-demand path-search statements from graph schema SQL.
---

# OR Spatial Path Query

## 职责与边界

本 skill 只做一件事：基于 `graph_modeling_sql` 产出图数据库可行路径查询定义。

输入的图数据库建模 SQL 必须自带语义角色，例如通过 `CREATE TAG` / `CREATE EDGE` 的 `comment='table_type:...'` 标注 `supply_node`、`demand_node`、`transport`、`link` 等角色。

本 skill 只负责路径查询定义，不负责 schema 合并、数据处理、路径搜索执行或求解器代码产出。

## 输入与引用

适用输入：

- `graph_modeling_sql`：图数据库建模 SQL，用于识别节点标签、边类型、属性映射、版本字段、起终点语义角色和可达关系。

读取顺序：

1. [execution_plan.yaml](execution_plan.yaml)：内部执行阶段定义
2. [references/spatial-path-query-rules.md](references/spatial-path-query-rules.md)：路径查询规则
3. [references/graph_path_query_analysis.schema.json](references/graph_path_query_analysis.schema.json)：中间分析结果 schema
4. [references/graph_path_queries.schema.json](references/graph_path_queries.schema.json)：最终路径查询定义 schema

中间分析结果记录节点标签、边类型、版本字段、跳数范围、SQL 证据和不确定缺口；最终输出只保留可供后续流程使用的路径查询定义。

## 执行边界

必须做：

- 只从 `graph_modeling_sql` 中识别 `supply_node`、`demand_node`、`transport`、`link` 图构件
- 从图建模 SQL 中识别节点标签、边类型、属性表和 `version_id` 过滤位置
- 构造 Cypher 风格图数据库可行路径查询语句，查询命名遵循 `graph_modeling_sql`
- 使用 `{version_id}` 表达运行时版本占位符，不写入具体版本值
- 输出独立的 `graph_path_queries` artifact
- 显式暴露无法稳定识别的标签、边类型、跳数或版本过滤缺口

不得做：

- 访问数据库、读取实例数据、执行路径搜索、写入路径结果或执行优化求解
- 产出求解器代码、数据加载代码或运行时执行脚本
- 把 `{version_id}` 替换成具体版本值，或把版本过滤做成构建期常量
- 假设图中存在 SQL 未定义的标签或边
- 将 `transport` 与 `link` 之外的 edge 默认作为可经过边
- 省略节点或边上的 `version_id` 过滤
- 把中间分析解释混入最终 `graph_path_queries.path_queries`

## 工作流程

按下面顺序工作，不要跳步。

### 1. 分析图查询构件

读取 `graph_modeling_sql`，提取：

- `CREATE TAG` / `CREATE EDGE` comment 中的 `table_type`
- `table_type = supply_node` 的节点标签、tag 或属性命名空间，作为起点集合
- `table_type = demand_node` 的节点标签、tag 或属性命名空间，作为终点集合
- `table_type = transport` 或 `table_type = link` 的边类型，作为可经过边集合
- 节点属性表、属性名前缀、节点和边上的 `version_id` 位置
- 可稳定识别的跳数范围

然后输出中间分析结果，符合 [references/graph_path_query_analysis.schema.json](references/graph_path_query_analysis.schema.json)。

### 2. 形成路径查询定义

- 基于中间分析结果形成独立路径查询定义
- 输出 `graph_path_queries`，而不是只输出查询片段
- 最终 `path_queries` 只保留关键参数、最终查询模板和必要注解
- 最终路径查询的核心参数必须组织为并列三项：`path_parameters.start_nodes`、`path_parameters.end_nodes`、`path_parameters.path_edges`
- 默认跳数范围为 `1..10`，直接体现在查询模板中；不单独输出 `confidence`、`hop_range`、`hop_parameter` 或 `hop_limit`
- `derivation_basis`、table_type 证据清单和详细 SQL 解析说明只保留在 `graph_path_query_analysis` artifact
- 若存在不确定缺口，写入 `graph_path_queries.unresolved_gaps`
- 最终输出符合 [references/graph_path_queries.schema.json](references/graph_path_queries.schema.json)。

## 查询表达要求

查询语句应使用占位符表达运行时参数：

- 版本占位符固定使用 `{version_id}`
- 默认跳数范围为 `1..10`
- 若输入中明确给出跳数范围，以输入为准覆盖默认值
- 查询文本中不能出现任何具体版本实例值，只能使用 `{version_id}`

典型 Cypher 结构：

```cypher
MATCH p=(s)-[:edge_type_a|edge_type_b*1..10]->(d)
WHERE ANY(label IN labels(s) WHERE label IN ['supply_node_graph_label_a', 'supply_node_graph_label_b'])
  AND ANY(label IN labels(d) WHERE label IN ['demand_node_graph_label_a'])
  AND s.source_table.version_id == {version_id}
  AND d.target_table.version_id == {version_id}
  AND ALL(e IN relationships(p) WHERE e.version_id == {version_id})
RETURN p
```

实际输出必须从图建模 SQL 的 comment 中读取 `table_type` 来确定图查询构件：`table_type:supply_node` 是起点标签集合，`table_type:demand_node` 是终点标签集合，`table_type:transport` 和 `table_type:link` 是可经过边集合。若 comment 缺失，只能使用 SQL 中的 tag、edge 名称和注释做辅助判断，并在 `unresolved_gaps` 中说明。
