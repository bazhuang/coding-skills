---
name: or-time-discretization
description: Generate data pipeline code that queries simulation tables by version_id, imports data into NebulaGraph, and splits data by time dimension.
---

# OR Time Discretization

生成数据处理管线代码：按版本号查询仿真表数据，导入 NebulaGraph 图数据库，按时间维度拆分并回写。

本 skill 只做"数据处理管线的代码生成"，不做"业务语义理解"或"数据计算"。

## 适用输入

用户输入通常包括：

1. 运筹算法本体 JSON（`or_ontology`），包含 `algorithm_objects.objects` 中的节点、边定义、`table_schema` 及 `time_dimension` 信息
2. NebulaGraph 连接配置（`nebula_config`），包含集群地址、图空间、用户名密码等
3. MySQL 连接配置（`mysql_config`），包含主机、数据库、用户名密码等

## 内置参考

- 数据处理管线规则：[references/data-pipeline-rules.md](references/data-pipeline-rules.md)
- 时间维度配置校验 Schema：[references/time_discretization_config.schema.json](references/time_discretization_config.schema.json)

## 内置模板

以下 Jinja2 模板位于 `assets/templates/` 目录，由 `utils/render_time_discretization.py` 在 `render_templates` 子步骤中直接渲染生成 Python 文件。模板已包含完整的类结构、方法定义、CLI 接口和错误处理模式，无需 LLM 生成 Python 代码。

- `mysql_query.py.jinja2` — 渲染生成 `mysql_query.py`，使用 `ontology_objects` 动态填充表列表和版本字段
- `nebula_import.py.jinja2` — 渲染生成 `nebula_import.py`，使用 `ontology_objects` + `map_to_nebula` 过滤器生成 TAG/EDGE 配置
- `data_split.py.jinja2` — 渲染生成 `data_split.py`，包含按时间窗口拆分算法
- `data_pipeline.py.jinja2` — 渲染生成 `data_pipeline.py`，使用 `importlib.util` 动态导入管线步骤

## 输出文件

1. **time_discretization_config.json** — 时间离散配置草案，从 or_ontology 中提取含 time_dimension 的对象及对应字段映射
2. **mysql_query.py** — 按版本号查询 MySQL 仿真表数据
3. **nebula_import.py** — 将查询结果导入 NebulaGraph
4. **data_split.py** — 从 NebulaGraph 查询数据并按时间维度拆分，将结果回写到 MySQL
5. **data_pipeline.py** — 编排上述三步的数据处理管线
6. **discretized_schema.sql** — 时间拆分结果回写表的 MySQL DDL 语句
7. **discretized_ddl_executor.py** — 读取 discretized_schema.sql 和 mysql_config，连接 MySQL 并执行 DDL 的 Python 代码

## Workflow

### 1. 读取输入

- 读取 `or_ontology`，从 `algorithm_objects.objects` 中提取 node/edge 对象，识别 `table_schema` 中的表名、字段、类型及 `time_dimension` 信息
- 读取 NebulaGraph 连接配置
- 读取 MySQL 连接配置

### 2. 提取时间维度配置

从 `or_ontology` 中筛选出包含 `time_dimension` 的 node/edge 对象，生成 `time_discretization_config.json`。该配置只做从 ontology 到配置 JSON 的字段提取映射，不做任何推断或修改。

每个对象映射为：
- `object_name` — 对象名称
- `object_category` — `"node"` 或 `"edge"`
- `table_name` — `table_schema.table_name`
- `start_time_field` / `end_time_field` — 时间范围字段
- `time_interval` — 时间窗口长度（枚举值：`Y`、`Q`、`M`、`W`、`D`）
- `quantity_fields` — 需要拆分的量字段列表
- `discretized_table` — 拆分结果表名（`discretized_{table_name}`）

### 3. 时间维度配置校验

按 [time_discretization_config.schema.json](references/time_discretization_config.schema.json) 校验生成的配置，同时执行以下 schema 无法覆盖的校验项：

**JSON Schema 校验**（由 schema 自动覆盖）：
- 必填字段完整性：`object_name`、`object_category`、`table_name`、`start_time_field`、`end_time_field`、`time_interval`、`quantity_fields`、`discretized_table`
- `object_category` 必须为 `"node"` 或 `"edge"`
- `time_interval` 必须为枚举值之一：`Y`、`Q`、`M`、`W`、`D`
- `quantity_fields` 不能为空数组
- `discretized_table` 格式必须为 `discretized_{table_name}`

**Schema 之外的校验**（需结合 or_ontology 手动检查）：
- `start_time_field` 和 `end_time_field` 必须能在对应对象的 `table_schema.fields` 中找到定义
- `quantity_fields` 中的每个字段必须能在对应对象的 `table_schema.fields` 中找到定义
- `discretized_table` 不能与 or_ontology 中任何现有的 `table_schema.table_name` 冲突

**校验不通过时**：返回步骤 2 重新生成，附带具体校验错误信息。

### 4. 模板渲染 Python 文件

`render_templates` 子步骤通过 `utils/render_time_discretization.py` 直接渲染 4 个 Jinja2 模板：

- `mysql_query.py.jinja2` → `mysql_query.py`
- `nebula_import.py.jinja2` → `nebula_import.py`
- `data_split.py.jinja2` → `data_split.py`
- `data_pipeline.py.jinja2` → `data_pipeline.py`

模板所需上下文：`or_ontology`（提供 ontology_objects）、`mysql_config`、`nebula_config`、`time_discretization_config`。`map_to_nebula` 过滤器负责将数据库类型文本（varchar/decimal/datetime 等）映射为 NebulaGraph 数据类型（string/double/int/datetime 等）。

### 5. 生成拆分结果表 DDL

根据 `time_discretization_config.json` 中已校验通过的对象，生成对应的时间拆分回写表 MySQL DDL，写入 `discretized_schema.sql`。规则见 [data-pipeline-rules.md](references/data-pipeline-rules.md) 第 3.4 节。

**关键要求**：
- 从本体定义中取出该对象的完整字段列表，逐个遍历判断是否在排除列表中
- 不在排除列表中的字段必须全部写入 DDL，**包括描述性字段和元数据字段**
- 字段名和 COMMENT 必须与源定义完全一致
- 必须为本体中的唯一索引生成对应唯一索引，索引字段组合为：本体唯一索引字段 + `time_period`

### 6. 生成 DDL 执行代码

生成 `discretized_ddl_executor.py`，要求：
- 接受 `--ddl-path` 和 `--config-path` 命令行参数
- 从 `--ddl-path` 文件读取 DDL 语句
- 从 `--config-path` JSON 文件读取 MySQL 连接配置
- 连接 MySQL，逐条执行 DDL 语句
- 输出每条语句的执行结果（成功/失败及错误信息）
- 执行失败时中断并返回错误码

### 7. 最终校验

按 [data-pipeline-rules.md](references/data-pipeline-rules.md) 中的校验规则逐项检查。

## 执行流程

本 Skill 通过 `execution_plan.yaml` 定义了 5 个子步骤：

1. **generate_time_config**（LLM）：从 or_ontology 提取时间维度配置，校验字段存在性、类型、表名唯一性，输出 `time_discretization_config.json`
2. **render_templates**（Action）：使用 Jinja2 渲染 4 个模板，生成 `mysql_query.py`、`nebula_import.py`、`data_split.py`、`data_pipeline.py`
3. **generate_discretized_schema**（LLM）：基于校验通过的配置，生成 `discretized_schema.sql`
4. **generate_ddl_executor**（LLM）：生成 `discretized_ddl_executor.py`
5. **execute_discretized_ddl**（Action）：调用 `discretized_ddl_executor.py` 将 DDL 执行到 MySQL

其中 `generate_discretized_schema` 和 `generate_ddl_executor` 为 LLM 子步骤，产物经过语法校验（Python 用 ast，SQL 用 CREATE TABLE + 括号平衡检查），失败时自动重试（最多 2 次）。Python 文件由模板直接渲染，无需 LLM 参与。Action 子步骤属于外部本地编排行为，不是本 skill 的功能前提，skill 的语义、输出约束和代码生成规则不得为任何外部触发脚本调整。

## 禁止事项

- 不要修改 `or_ontology` 中的表名、字段名、类型定义
- 不要编造配置文件中不存在的连接参数
- 不要跳过版本过滤逻辑（查询和导入均需支持版本号）
- 不要引入与数据处理无关的业务逻辑
