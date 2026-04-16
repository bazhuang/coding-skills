---
name: or-feasible-path-query
description: Generate NebulaGraph path query code from algorithm ontology model. Extracts supply/demand node types and edge types, generates nGQL queries and Python loader code for finding feasible paths between resources and demands.
---

# OR Feasible Path Query

从算法本体模型中提取起点、终点和线路信息，生成 NebulaGraph 可行路径查询的 Python 代码。

本 skill 只做"从本体到路径查询代码的生成"，不做"业务语义理解"或"路径结果分析"。

## 适用输入

1. 算法本体模型 JSON（由 business-to-or-ontology skill 产出，符合 `../business-to-or-ontology/references/算法本体模型.schema.json`）

## 内置参考

- 图映射规则：[references/path-query-rules.md](references/path-query-rules.md)
- NebulaGraph 连接配置：[references/nebula_config.json](references/nebula_config.json)

## 输出文件

1. **path_query_code.py** — 完整的路径查询 Python 代码
2. **path_query_nql.txt** — 填充完成的 nGQL 查询语句

## Workflow

### 1. 读取算法本体模型

读取输入 JSON。

### 2. 筛选对象

- `object_category: "node"` 且 `object_type: "supply_node"` → 起点
- `object_category: "node"` 且 `object_type: "demand_node"` → 终点
- `object_category: "edge"` 且 `object_type` 为 `transport` 或 `link` → 线路

分别收集 `table_schema.table_name` 列表。

### 3. 生成 nGQL 查询语句

按 [path-query-rules.md](references/path-query-rules.md) 中的规则，将起点、终点、线路表名填入 nGQL 模板，写入 `path_query_nql.txt`。

### 4. 生成路径查询代码

按 [path-query-rules.md](references/path-query-rules.md) 中的规则生成 Python 代码，包含：

- 连接管理：从 [references/nebula_config.json](references/nebula_config.json) 读取配置，遍历 `cluster_servers`，任意一个节点连接成功即可
- 路径查询：使用步骤 3 生成的 nGQL，`version_id` 运行时填充
- 路径解析：提取节点和边的 VID 标识

### 5. 校验

- 起点、终点、线路列表均不为空
- 表名完全继承自 `table_schema.table_name`
- nGQL 语法完整
- Python 代码可独立运行

## 禁止事项

- 不要修改本体模型中的表名定义
- 不要编造不存在的表名或字段
- 不要将 `{version_id}` 在生成时填充为固定值
- 不要引入与路径查询无关的模块或业务逻辑

## 质量标准

1. 表名完全继承自 `table_schema.table_name`
2. resources 列表用 `, ` 分隔、方括号包裹；edges 列表用 `|` 分隔
3. `{version_id}` 保留为占位符
4. 生成的 Python 代码可独立运行
