---
name: or-time-discretization
description: Generate data pipeline code that queries simulation tables by version_id, imports data into NebulaGraph, and splits data by time dimension. Depends on directed-graph-modeling output data_mapping.json and connection configs.
---

# OR Time Discretization

生成数据处理管线代码：按版本号查询仿真表数据，导入 NebulaGraph 图数据库，按时间维度拆分并回写。

本 skill 只做"数据处理管线的代码生成"，不做"业务语义理解"或"数据计算"。

## 适用输入

1. directed-graph-modeling 产出的 `data_mapping.json`（由 directed-graph-modeling skill 从算法本体模型映射生成）
2. NebulaGraph 连接配置：[references/nebula_config.json](references/nebula_config.json)
3. MySQL 仿真表连接配置：[references/mysql_config.json](references/mysql_config.json)

## 内置参考

- 数据处理管线规则：[references/data-pipeline-rules.md](references/data-pipeline-rules.md)

## 输出文件

1. **mysql_query.py** — 按 version_id 查询 MySQL 仿真表数据
2. **nebula_import.py** — 将查询结果导入 NebulaGraph
3. **data_split.py** — 从 NebulaGraph 查询数据并按时间维度拆分
4. **data_pipeline.py** — 编排上述三步的数据处理管线
5. **discretized_schema.sql** — 时间拆分结果回写表的 MySQL DDL 语句（基于有 `time_dimension` 的 TAG/EDGE 生成）

## Workflow

### 1. 读取 data_mapping.json 和连接配置

- 读取 `data_mapping.json`，获取所有 TAG/EDGE 定义：`tags[].tag_name`、`tags[].source_table`、`tags[].vid_field`、`tags[].fields`、`tags[].field_types`、`tags[].time_dimension`，以及 `edges` 中的对应字段和 `src_tag`/`dst_tag`/`src_vid_field`/`dst_vid_field`/`rank_field`
- 读取 [references/nebula_config.json](references/nebula_config.json)，获取 NebulaGraph 集群连接配置
- 读取 [references/mysql_config.json](references/mysql_config.json)，获取 MySQL 连接配置

### 2. 生成 mysql_query.py

按 [data-pipeline-rules.md](references/data-pipeline-rules.md) 中的 MySQL 查询生成规则生成代码。

### 3. 生成 nebula_import.py

按 [data-pipeline-rules.md](references/data-pipeline-rules.md) 中的 NebulaGraph 导入生成规则生成代码。

### 4. 生成 data_split.py

按 [data-pipeline-rules.md](references/data-pipeline-rules.md) 中的数据拆分生成规则生成代码。

### 5. 生成 data_pipeline.py

按 [data-pipeline-rules.md](references/data-pipeline-rules.md) 中的管线编排生成规则生成代码。

### 6. 生成拆分结果表 DDL

根据 `data_mapping.json` 中有 `time_dimension` 的 TAG/EDGE，生成对应的时间拆分回写表 MySQL DDL，写入 `discretized_schema.sql`。规则见 [data-pipeline-rules.md](references/data-pipeline-rules.md) 第 6 节。

### 7. 校验

按 [data-pipeline-rules.md](references/data-pipeline-rules.md) 中的校验规则逐项检查。

## 禁止事项

- 不要修改 `data_mapping.json` 中的表名、字段名、类型定义
- 不要编造配置文件中不存在的连接参数
- 不要跳过版本过滤逻辑（查询和导入均需支持 version_id）
- 不要引入与数据处理无关的业务逻辑

## 质量标准

1. 所有表名完全继承自 `data_mapping.json`
2. 字段类型与 `data_mapping.json` 中定义的 NebulaGraph 类型一致
3. VID 格式统一为 `{version}_{pk_value}`
4. 集群连接策略为遍历 `cluster_servers`，任意一个连接成功即可
5. 时间拆分使用 proportional 分配方法
6. 生成的 Python 代码可独立运行（data_pipeline.py 依赖其他三个文件）
