# 可行路径生成规则

本文件定义了从算法本体模型到 NebulaGraph 路径查询代码的确定性生成规则。

## 1. 对象筛选

### 1.1 起点（supply_node）

- `object_category: "node"` 且 `object_type: "supply_node"`
- 提取 `table_schema.table_name` 作为起点标签列表

### 1.2 终点（demand_node）

- `object_category: "node"` 且 `object_type: "demand_node"`
- 提取 `table_schema.table_name` 作为终点标签列表

### 1.3 线路（transport/link）

- `object_category: "edge"` 且 `object_type` 为 `transport` 或 `link`
- 提取 `table_schema.table_name` 作为边类型列表

## 2. nGQL 查询语句生成

### 2.1 查询模板

```nGQL
MATCH p = (r)-[:{edges}*1..10]->(d)
WHERE ANY(label IN labels(r) WHERE label IN [{resources}]) == true
  AND ANY(label IN labels(d) WHERE label IN [{demands}]) == true
  AND properties(r).version_id == {version_id}
  AND properties(d).version_id == {version_id}
  AND ALL(e IN relationships(p) WHERE e.version_id == {version_id}) == true
RETURN p
```

### 2.2 占位符填充规则

| 占位符 | 填充内容 | 拼接规则 |
|--------|---------|---------|
| `{resources}` | 起点表名列表 | 用 `, ` 分隔，不加引号 |
| `{demands}` | 终点表名列表 | 用 `, ` 分隔，不加引号 |
| `{edges}` | 线路表名列表 | 用 `|` 分隔 |
| `{version_id}` | 保留不填充 | 运行时传入，数值型，不加引号 |

### 2.3 拼接示例

**输入：**
- supply_nodes: `["supply_station", "resource_hub"]`
- demand_nodes: `["demand_site"]`
- edges: `["monthly_transport", "rel_transport"]`

**输出：**
```nGQL
MATCH p = (r)-[:monthly_transport|rel_transport*1..10]->(d)
WHERE ANY(label IN labels(r) WHERE label IN [supply_station, resource_hub]) == true
  AND ANY(label IN labels(d) WHERE label IN [demand_site]) == true
  AND properties(r).version_id == {version_id}
  AND properties(d).version_id == {version_id}
  AND ALL(e IN relationships(p) WHERE e.version_id == {version_id}) == true
RETURN p
```

## 3. 路径解析规则

### 3.1 路径序列解析

1. 从 `path_data.nodes()` 获取节点列表
2. 提取每个节点的 VID（图数据库顶点标识）
3. 从 `path_data.relationships()` 获取边列表
4. 提取每条边的 src/dst VID
5. 构建路径序列：`[node_vid, edge_vid, node_vid, edge_vid, ..., node_vid]`

### 3.2 输出格式

```python
[
    ["RES001", "REL001", "M001", "REL002", "DEM001"],
    ...
]
```

- 第一个元素是起点，最后一个元素是终点
- 路径中节点和边均使用图数据库的内部 VID 标识

## 4. 连接管理规则

### 4.1 连接配置

- 使用 `nebula3-python` 客户端库
- 连接参数支持外部 JSON 文件传入或代码内嵌
- 配置项：graphd_host, graphd_port, username, password, default_space, max_connection_pool_size, timeout_ms

### 4.2 连接流程

1. 初始化 `ConnectionPool`
2. 使用 `ConnectionPool.init()` 连接指定节点
3. 通过 `ConnectionPool.get_session()` 获取会话
4. 执行 `USE {default_space}` 切换到目标图空间

### 4.3 查询执行

- 默认最多重试 3 次，每次重试间隔 1 秒
- 查询失败应记录 warning 日志并重试
- 全部重试失败后抛出 RuntimeError

## 5. 输出文件清单

| 文件 | 内容 |
|------|------|
| `path_query_code.py` | 完整的路径查询 Python 代码 |
| `path_query_nql.txt` | 填充完成的 nGQL 查询语句 |

## 6. 校验规则

- 起点、终点、线路列表均不可为空
- 所有表名完全继承自 `table_schema.table_name`，不做任何修改
- nGQL 中 resources 列表用 `, ` 分隔、方括号包裹
- nGQL 中 edges 列表用 `|` 分隔
- `{version_id}` 保留为占位符，不在生成时填充
- 生成的 Python 代码可独立运行，不依赖外部 Jinja2 模板
