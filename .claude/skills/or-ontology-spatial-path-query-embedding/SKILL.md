---
name: or-ontology-spatial-path-query-embedding
description: Embed graph database feasible path queries into a time-discretized OR algorithm ontology. Use when Codex needs to derive supply-to-demand path-search statements from graph modeling SQL and return the complete or_ont extended with version-placeholder path query definitions.
---

# OR Ontology Spatial Path Query Embedding

## 职责与边界

本 skill 只做一件事：基于时间离散后的运筹算法本体 `or_ont_time_discretized` 和 `graph_modeling_sql`，在完整 `or_ont` 中追加 `graph_path_query_system`，生成从供给节点到需求节点、沿 `transport` 与 `link` 类边进行可变跳数搜索的图数据库路径查询定义。

术语口径：

- 业务本体：`biz_ont`
- 运筹算法本体：`or_ont`
- 运筹 DSL：`or_dsl`

本 skill 是算法本体扩展器，不是 schema 合并器、数据处理器、路径搜索执行器或求解器代码生成器。

## 系统边界

本 skill 同时读取两套系统，但不得混用其职责：

| 系统 | 来源 | 职责 | 不得用于 |
| --- | --- | --- | --- |
| 业务数据系统（主系统） | `or_ont_time_discretized` 中的 `table_schema` | 算法对象、目标、约束、映射依据和数值建模字段的依据 | 被图数据库 schema 覆盖或改写 |
| 图数据库系统（辅助路径系统） | `graph_modeling_sql` | 推导节点标签、边类型、属性路径和 `{version_id}` 过滤位置 | 提供建模数值，改写目标、约束或对象 schema |

图数据库建模 SQL 通常来自未离散的原始 schema，表名、标签名或属性承载名可能与 `or_ont` 中的离散化 schema 不一致。这些差异只用于生成 `graph_path_query_system` 中的查询语句，不得反向影响 `or_ont` 主体。

## 输入与引用

适用输入：

- `or_ont_time_discretized`：已经适配时间离散数据后的运筹算法本体，是业务对象、目标、约束、映射依据和建模数值的主依据。
- `graph_modeling_sql`：基于原数据 schema 生成的图数据库建模 SQL，只用于识别节点标签、边类型、属性映射、版本字段、起终点关系或可达关系。

读取顺序：

1. [execution_plan.yaml](execution_plan.yaml)：内部执行阶段定义
2. [references/spatial-path-query-embedding-rules.md](references/spatial-path-query-embedding-rules.md)：路径查询生成规则
3. [references/graph_path_query_analysis.schema.json](references/graph_path_query_analysis.schema.json)：中间分析结果 schema
4. [references/algorithm_ontology_path_query_embedded.schema.json](references/algorithm_ontology_path_query_embedded.schema.json)：最终扩展本体 schema

中间分析结果记录节点标签、边类型、版本字段、跳数范围、映射依据和不确定缺口；最终输出只保留完整 `or_ont_path_query_embedded`、路径查询定义和少量必要说明。

## 执行边界

必须做：

- 从 `or_ont_time_discretized` 中识别 `supply_node`、`demand_node`、`transport`、`link` 对象
- 从图建模 SQL 中识别对应节点标签、边类型、属性表和 `version_id` 过滤位置
- 生成 Cypher 风格图数据库可行路径查询语句，查询命名遵循 `graph_modeling_sql`
- 使用 `{version_id}` 表达运行时版本占位符，不写入具体版本值
- 只新增或更新 `graph_path_query_system`，并输出完整 `or_ont_path_query_embedded` artifact
- 显式暴露无法稳定识别的标签、边类型、跳数或版本过滤缺口

不得做：

- 访问数据库、读取实例数据、执行路径搜索、写入路径结果或执行优化求解
- 生成求解器代码、数据加载代码或运行时执行脚本
- 把 `{version_id}` 替换成具体版本值，或把版本过滤做成构建期常量
- 假设图中存在 SQL 未定义的标签或边
- 将 `transport` 与 `link` 之外的对象默认作为可经过边
- 省略节点或边上的 `version_id` 过滤
- 用图建模 SQL 的未离散 schema 覆盖、修正或替代 `or_ont` 中的离散化 schema
- 因图 SQL 与 `or_ont` 表名不同而调整、重命名或重分类 `algorithm_objects`
- 修改目标、约束、映射依据或业务语义
- 把中间分析解释混入最终 `or_ont` 主体或 `graph_path_query_system.path_queries`

## 工作流程

按下面顺序工作，不要跳步。

### 1. 分析图查询构件

读取时间离散后的 `or_ont_time_discretized`，识别：

- 供给端：`object_type = supply_node`，收集 `table_schema.table_name` 与 `supporting_tables`
- 需求端：`object_type = demand_node`，收集 `table_schema.table_name` 与 `supporting_tables`
- 中间边：`object_type = transport` 或 `object_type = link`

读取图建模 SQL，提取：

- `CREATE TAG` / `CREATE EDGE` comment 中的 `table_type`
- `table_type = supply_node` 的节点标签、tag 或属性命名空间，作为起点集合
- `table_type = demand_node` 的节点标签、tag 或属性命名空间，作为终点集合
- `table_type = transport` 或 `table_type = link` 的边类型，作为可经过边集合
- 节点属性表、属性名前缀、节点和边上的 `version_id` 位置
- 可稳定识别的跳数范围

然后输出中间分析结果，符合 [references/graph_path_query_analysis.schema.json](references/graph_path_query_analysis.schema.json)。

### 2. 嵌入路径查询定义

- 基于中间分析结果生成查询定义，在顶层新增 `graph_path_query_system`
- 输出完整 `or_ont_path_query_embedded`，而不是查询片段
- 原样保留原 `or_ont_time_discretized` 的 `problem_frame`、`algorithm_objects`、`objective_system`、`constraint_system`、`mapping_rationale`、`open_questions`
- 最终 `graph_path_query_system.path_queries` 只保留关键参数、最终查询模板和必要注解
- 最终路径查询的核心参数必须组织为并列三项：`path_parameters.start_nodes`、`path_parameters.end_nodes`、`path_parameters.path_edges`
- 默认跳数范围为 `1..10`，直接体现在查询模板中；不单独输出 `confidence`、`hop_range`、`hop_parameter` 或 `hop_limit`
- 不输出 `downstream_usage` 等下游用途字段；这类内容只用于 skill 理解自身工作定位
- `mapping_basis`、`derivation_basis`、table_type 证据清单、详细 schema 差异说明只保留在 `graph_path_query_analysis` artifact
- 若存在不确定缺口，同步写入 `graph_path_query_system.unresolved_gaps`，必要时也写入顶层 `open_questions`
- 最终输出符合 [references/algorithm_ontology_path_query_embedded.schema.json](references/algorithm_ontology_path_query_embedded.schema.json)。

## 查询表达要求

查询语句应使用占位符表达运行时参数：

- 版本占位符固定使用 `{version_id}`
- 默认跳数范围为 `1..10`
- 若输入中明确给出跳数范围，以输入为准覆盖默认值
- 查询文本中不能出现任何具体版本实例值，只能使用 `{version_id}`

典型 Cypher 结构：

```cypher
MATCH p=(s)-[:edge_type_a|edge_type_b*1..10]->(d)
WHERE ANY(label IN labels(s) WHERE label IN ['supply_node_table_or_graph_label_a', 'supply_node_table_or_graph_label_b'])
  AND ANY(label IN labels(d) WHERE label IN ['demand_node_table_or_graph_label_a'])
  AND s.source_table.version_id == {version_id}
  AND d.target_table.version_id == {version_id}
  AND ALL(e IN relationships(p) WHERE e.version_id == {version_id})
RETURN p
```

实际输出必须先从 `or_ont_time_discretized` 中按 `object_type = supply_node` / `demand_node` 收集起终点对象与表名列表，再从图建模 SQL 的 comment 中读取 `table_type` 来确定图查询构件：`table_type:supply_node` 是起点标签集合，`table_type:demand_node` 是终点标签集合，`table_type:transport` 和 `table_type:link` 是可经过边集合。若 comment 缺失或 table_type 与 `or_ont` 角色无法对应，再使用表名或对象名做辅助映射，并在 `unresolved_gaps` 中说明。不得照抄示例中的占位业务名。
