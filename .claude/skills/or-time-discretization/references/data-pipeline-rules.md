# 时间离散化数据处理规则

本文件定义了从 `data_mapping.json` 到 MySQL → NebulaGraph → 时间拆分数据处理管线的确定性生成规则。

## 1. 输入来源

### 1.1 data_mapping.json 来源

读取 `data_mapping.json`，获取：

- `tags[]` — 所有 TAG 定义
  - `tag_name`、`tag_type`、`vid_field`、`source_table`、`description`
  - `fields`、`field_types`
  - `time_dimension`（可选）：`start_time_field`、`end_time_field`、`time_interval`、`quantity_fields`
- `edges[]` — 所有 EDGE 定义
  - `edge_name`、`edge_type`、`src_vid_field`、`dst_vid_field`、`rank_field`
  - `source_table`、`src_tag`、`dst_tag`、`description`
  - `fields`、`field_types`
  - `time_dimension`（可选）

### 1.2 配置来源

读取 `references/nebula_config.json`，获取：

- `cluster_servers[]` — 集群节点列表（host, port）
- `space` — 图空间名称
- `username`、`password` — 认证信息
- `pool_config` — 连接池配置（min_size, max_size, idle_time, timeout, interval_check）
- `session_config` — 会话配置（retry_times, timeout）

读取 `references/mysql_config.json`，获取：

- `host`、`port`、`database` — 连接信息
- `username`、`password` — 认证信息
- `charset`、`pool_size`、`pool_recycle`、`pool_pre_ping`、`connect_timeout`

## 2. MySQL 查询生成规则

### 2.1 连接规则

- 使用 `sqlalchemy` + `pymysql` 驱动
- 连接字符串格式：`mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset={charset}`
- 引擎配置：pool_size, pool_recycle, pool_pre_ping, connect_timeout

### 2.2 字段检测规则

通过 `information_schema.COLUMNS` 检查表中是否存在 `version_id` 字段：

```sql
SELECT COUNT(*) as count
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = :database
  AND TABLE_NAME = :table_name
  AND COLUMN_NAME = 'version_id'
```

### 2.3 查询规则

- 有 `version_id` 字段且传入版本号：`SELECT * FROM {table} WHERE version_id = :version`
- 无 `version_id` 字段或未传入版本号：`SELECT * FROM {table}`（全表）
- 查询结果返回 `pd.DataFrame`

### 2.4 表收集规则

从 `data_mapping.json` 中收集所有去重的 `source_table`：

- 遍历 `tags[]`，收集每个 `tag.source_table`
- 遍历 `edges[]`，收集每个 `edge.source_table`
- 去重后作为查询目标表列表

### 2.5 类结构

- `MySQLQueryExecutor` 类：封装连接、检测、查询逻辑
- `query_by_version(table_name, version)` — 单表查询
- `query_all_tables(version)` — 遍历所有表查询
- `main()` — 命令行入口（--config、--version、--table、--output）

## 3. NebulaGraph 导入生成规则

### 3.1 连接规则

- 使用 `nebula3-python` 客户端库
- 遍历 `cluster_servers`，任意一个节点连接成功即可
- 每个节点尝试：创建 `ConnectionPool` → `init()` → `get_session()` → `SHOW SPACES` 验证 → 成功则保留此 pool
- 全部失败抛出 `RuntimeError`

### 3.2 VID 构造规则

- TAG VID：`{version}_{vid_field_value}`，其中 `vid_field` 来自 `data_mapping.json` 中对应 TAG 的 `vid_field`
- EDGE 源 VID：`{version}_{src_vid_field_value}`，其中 `src_vid_field` 来自对应 EDGE 定义
- EDGE 目标 VID：`{version}_{dst_vid_field_value}`，其中 `dst_vid_field` 来自对应 EDGE 定义

### 3.3 TAG 导入规则

nGQL 语句格式：

```sql
INSERT VERTEX `tag_name` (`field1`, `field2`, ...) VALUES '{vid}':('val1', 'val2', ...);
```

- 字段列表来自 `data_mapping.json` 中 `tag.fields`，跳过 `vid_field`
- 值根据 `tag.field_types` 格式化
- 如果数据中没有 `version_id` 字段，手动添加 `version_id` 到属性列表
- 批量大小：256 条/批次

### 3.4 EDGE 导入规则

nGQL 语句格式：

```sql
INSERT EDGE `edge_name` (`field1`, `field2`, ...) VALUES '{src_vid}'->'{dst_vid}'@{rank}:('val1', 'val2', ...);
```

- 字段列表来自 `data_mapping.json` 中 `edge.fields`，跳过 `src_vid_field` 和 `dst_vid_field`
- `rank`：如果 `edge.rank_field` 非空且数据中有该字段，取该字段值；否则为 0
- 批量大小：256 条/批次

### 3.5 值格式化规则

| Nebula 类型 | 格式化方式 |
|---|---|
| `string` | `'value'`（转义单引号和反斜杠） |
| `int` / `int64` | `int(value)` |
| `double` | `float(value)` |
| `bool` | `str(bool(value)).lower()` |
| `date` | `date('value')` |
| `datetime` | `datetime('value')` |
| `timestamp` | `timestamp('value')` |
| NULL / NaN | `NULL` |

### 3.6 类结构

- `NebulaImporter` 类：封装连接、导入逻辑
- `connect()` — 集群连接
- `import_tag_data(tag_name, df, mapping, version)` — TAG 导入
- `import_edge_data(edge_name, df, mapping, version)` — EDGE 导入
- `import_all_data(table_data, version)` — 遍历所有 TAG/EDGE 导入
- `disconnect()` — 关闭连接
- `main()` — 命令行入口（--config、--data-dir、--mapping、--version）

## 4. 数据拆分生成规则

### 4.1 连接规则

- NebulaGraph 连接方式同 3.1 节
- 执行 `USE {space}` 切换到目标图空间
- 支持连接 MySQL（用于回写拆分结果）

### 4.2 TAG 查询规则

nGQL 语句：

- 有版本号：`MATCH (v:\`tag_name\`) WHERE id(v) STARTS WITH '{version}_' RETURN v`
- 无版本号：`MATCH (v:\`tag_name\`) RETURN v`

解析方式：

- 遍历结果行，`row.values()[0].as_node()` 获取节点
- 提取 VID：`vertex.get_id().as_string()`
- 从 VID 中去掉 `{version}_` 前缀得到原始值
- 遍历 `vertex.tags()` 和 `vertex.properties()` 提取属性

### 4.3 EDGE 查询规则

nGQL 语句：

- 有版本号：`MATCH (src)-[e:\`edge_name\`]->(dst) WHERE id(src) STARTS WITH '{version}_' AND id(dst) STARTS WITH '{version}_' RETURN e`
- 无版本号：`MATCH ()-[e:\`edge_name\`]->() RETURN e`

解析方式：

- 遍历结果行，`row.values()[0].as_relationship()` 获取边
- 提取 `start_vertex_id()`、`end_vertex_id()`
- 去掉 `{version}_` 前缀得到原始值
- 遍历 `edge.properties()` 提取属性

### 4.4 时间拆分规则

使用 `pandas.tseries.frequencies.to_offset(interval)` 获取窗口长度。

拆分流程：

1. 将开始/结束时间列转为 `datetime`
2. 从 `start.floor(interval)` 开始，按 offset 生成不重叠窗口 `[window_start, window_end)`
3. 计算每个窗口与原区间的重叠秒数 `overlap_seconds`
4. 按 `proportional` 方法分配：`allocated_value = total * (overlap_seconds / total_seconds)`
5. 为每个窗口创建新行，保留其他列，加入 `time_period` 和 `allocated_<field>` 列
6. 移除原始开始/结束时间列

Nebula 日期时间值转换：

- 处理 `DateWrapper`（get_year, get_month, get_day）
- 处理 `DateTimeWrapper`（get_year, get_month, get_day, get_hour, get_minute, get_sec, get_microsec）
- 兜底使用 `pd.to_datetime()`

### 4.5 拆分结果回写规则

- 表名规则：`split_{tag|edge}_{name}`
- 写入前：删除同 version 的旧数据（`DELETE FROM table WHERE version = :v`）
- 写入方式：`df.to_sql(if_exists='append', index=False, chunksize=1000)`
- `time_period` 转为字符串格式：`%Y-%m-%d %H:%M:%S`

### 4.6 处理流程

`process_all_splits()` 方法：

1. 遍历 `data_mapping.json` 的 `tags[]`，检查是否有 `time_dimension`
2. 有则：query_tag_data → split_by_time_dimension → 写回 MySQL
3. 遍历 `data_mapping.json` 的 `edges[]`，检查是否有 `time_dimension`
4. 有则：query_edge_data → split_by_time_dimension → 写回 MySQL

### 4.7 类结构

- `DataSplitter` 类：封装连接、查询、拆分、回写逻辑
- `query_tag_data(tag_name)` — 查询 TAG
- `query_edge_data(edge_name)` — 查询 EDGE
- `split_by_time_dimension(df, start_time_field, end_time_field, time_interval, quantity_fields)` — 时间拆分
- `process_all_splits()` — 处理所有拆分
- `disconnect()` — 关闭连接
- `main()` — 命令行入口（--config、--mapping、--version、--mysql-config）

## 5. 管线编排生成规则

### 5.1 管线流程

`DataPipeline.run(version)` 按顺序执行：

1. **Step 1 — MySQL 查询**：动态导入 `mysql_query.py`，创建 `MySQLQueryExecutor`，`query_all_tables(version)` 返回 DataFrame 映射
2. **Step 2 — NebulaGraph 导入**：动态导入 `nebula_import.py`，创建 `NebulaImporter`，`connect()` 后 `import_all_data(table_data, version)`
3. **Step 3 — 时间拆分**：动态导入 `data_split.py`，创建 `DataSplitter`，`connect()` 后 `process_all_splits()`

### 5.2 错误处理

- 每一步失败时记录错误信息并立即返回
- 记录每步的成功/失败状态
- 全部成功返回 0，否则返回 1

### 5.3 类结构

- `DataPipeline` 类：封装三步编排
- 构造函数参数：`mysql_config_path`、`nebula_config_path`、`data_mapping_path`
- `run(version)` — 执行管线
- `main()` — 命令行入口（--version、--mysql-config、--nebula-config）

## 6. 输出文件清单

| 文件 | 内容 |
|------|------|
| `mysql_query.py` | MySQL 查询脚本 |
| `nebula_import.py` | NebulaGraph 导入脚本 |
| `data_split.py` | 时间拆分脚本 |
| `data_pipeline.py` | 管线编排脚本 |

## 7. 校验规则

- TAG/EDGE 数量与 `data_mapping.json` 一致
- 所有 `source_table` 都能在 MySQL 查询中覆盖
- `time_dimension` 拆分配置与 `data_mapping.json` 中定义一致
- VID 格式统一为 `{version}_{pk_value}`
- 集群连接策略为遍历 `cluster_servers`，任意一个连接成功即可
- 四个文件均可独立运行（data_pipeline.py 依赖其他三个）
