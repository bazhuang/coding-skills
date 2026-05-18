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

以下 Jinja2 模板位于 `assets/templates/` 目录，**生成的代码必须继承模板的类结构、方法定义、CLI 接口和错误处理模式**，不得简化或删减

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

### 4. 生成 mysql_query.py

参照 [assets/templates/mysql_query.py.jinja2](assets/templates/mysql_query.py.jinja2) 骨架，
按 [data-pipeline-rules.md](references/data-pipeline-rules.md) 中的 MySQL 查询生成规则生成代码。

**必须保留的核心结构**：
- 主执行类，构造函数接受配置文件路径，不直接接受配置字典
- 从文件加载 JSON 配置的方法
- 建立数据库连接池并测试连通性的方法
- 释放数据库连接的方法
- 按版本号查询单表数据的方法，需先通过 `information_schema.COLUMNS` 检查版本过滤字段是否存在
- 检查表中是否存在版本过滤字段的私有方法
- 查询所有配置的表并返回数据映射的方法
- 完整的 `main()` 函数 + `argparse` 参数解析 + `if __name__ == "__main__": sys.exit(main())` 入口点
- 全局使用 `logging` 模块，不得用 `print()` 替代
- 关键操作包裹在 `try/except/finally` 中

### 5. 生成 nebula_import.py

参照 [assets/templates/nebula_import.py.jinja2](assets/templates/nebula_import.py.jinja2) 骨架，
按 [data-pipeline-rules.md](references/data-pipeline-rules.md) 中的 NebulaGraph 导入生成规则生成代码。

**必须保留的核心结构**：
- 从本体提取的图数据库节点类型和边类型全局配置常量，不得硬编码
- 主执行类，构造函数接受配置文件路径
- 连接方法：尝试连接集群中的节点，切换到目标空间
- 断开连接方法：释放会话和连接池
- 根据图数据库类型格式化属性值的方法（处理字符串转义、空值、日期等类型）
- 批量插入节点数据的方法（固定批量大小）
- 批量插入边数据的方法（固定批量大小）
- 遍历所有节点和边类型执行导入的编排方法
- 完整的 `main()` 函数 + `argparse` 参数解析 + `if __name__ == "__main__": sys.exit(main())` 入口点
- 全局使用 `logging` 模块，不得用 `print()` 替代

### 6. 生成 data_split.py

参照 [assets/templates/data_split.py.jinja2](assets/templates/data_split.py.jinja2) 骨架，
按 [data-pipeline-rules.md](references/data-pipeline-rules.md) 中的数据拆分生成规则生成代码。

**必须保留的核心结构**：
- 时间粒度到 pandas offset 的映射常量
- 独立的按时间窗口拆分并分配量值的算法函数
- 主执行类，构造函数参数顺序：图数据库配置路径、时间拆分配置路径，可选追加版本号和关系型数据库配置路径
- 分别加载图数据库配置、时间拆分配置、关系型数据库配置的方法
- 连接方法：连接图数据库，如果配置了关系型数据库则同时连接
- 断开连接方法：释放图数据库和关系型数据库连接
- 从图数据库查询节点数据的方法，解析 VID 和属性
- 从图数据库查询边数据的方法，解析 VID 和属性
- 转换图数据库值为 Python 原生值的方法
- 按时间维度拆分数据的方法
- 将拆分结果写入关系型数据库目标表的方法，写入前清理同版本旧数据
- 遍历时间拆分配置执行所有拆分并保存结果的方法
- 完整的 `main()` 函数 + `argparse` 参数解析 + `if __name__ == "__main__": sys.exit(main())` 入口点
- 全局使用 `logging` 模块，不得用 `print()` 替代

### 7. 生成 data_pipeline.py

参照 [assets/templates/data_pipeline.py.jinja2](assets/templates/data_pipeline.py.jinja2) 骨架，
按 [data-pipeline-rules.md](references/data-pipeline-rules.md) 中的管线编排生成规则生成代码。

**必须保留的核心结构**：
- 管线编排类，构造函数接受各步骤所需的配置文件路径
- `run(version)` 方法按顺序执行：查询数据源 → 导入图数据库 → 时间维度拆分 → 写回数据源
- 各步骤的私有方法：使用 `importlib.util` 动态导入同目录下的模块，不使用 `subprocess`
- 每个步骤有独立的 `try/except` 捕获失败并返回结构化结果
- 完整的 `main()` 函数 + `argparse` 参数解析 + `if __name__ == "__main__": sys.exit(main())` 入口点
- 全局使用 `logging` 模块，不得用 `print()` 替代

### 8. 生成拆分结果表 DDL

根据 `time_discretization_config.json` 中已校验通过的对象，生成对应的时间拆分回写表 MySQL DDL，写入 `discretized_schema.sql`。规则见 [data-pipeline-rules.md](references/data-pipeline-rules.md) 第 3.4 节。

**关键要求**：
- 从本体定义中取出该对象的完整字段列表，逐个遍历判断是否在排除列表中
- 不在排除列表中的字段必须全部写入 DDL，**包括描述性字段和元数据字段**
- 字段名和 COMMENT 必须与源定义完全一致
- 必须为本体中的唯一索引生成对应唯一索引，索引字段组合为：本体唯一索引字段 + `time_period`

### 9. 生成 DDL 执行代码

生成 `discretized_ddl_executor.py`，要求：
- 接受 `--ddl-path` 和 `--config-path` 命令行参数
- 从 `--ddl-path` 文件读取 DDL 语句
- 从 `--config-path` JSON 文件读取 MySQL 连接配置
- 连接 MySQL，逐条执行 DDL 语句
- 输出每条语句的执行结果（成功/失败及错误信息）
- 执行失败时中断并返回错误码

### 10. 最终校验

按 [data-pipeline-rules.md](references/data-pipeline-rules.md) 中的校验规则逐项检查。

## 执行流程

本 Skill 通过 `execution_plan.yaml` 定义了子步骤：

1. **generate_time_config**（LLM）：从 or_ontology 提取时间维度配置，校验字段存在性、类型、表名唯一性
2. **generate_code_and_ddl**（LLM）：生成六个文件（mysql_query.py、nebula_import.py、data_split.py、data_pipeline.py、discretized_schema.sql、discretized_ddl_executor.py）
3. **execute_discretized_ddl**（Action）：调用 `discretized_ddl_executor.py` 将 DDL 执行到 MySQL

LLM 子步骤负责生成配置、代码和 DDL；Action 子步骤属于外部本地编排行为。该 Action 不是本 skill 的功能前提，skill 的语义、输出约束和代码生成规则不得为任何外部触发脚本调整。

## 禁止事项

- 不要修改 `or_ontology` 中的表名、字段名、类型定义
- 不要编造配置文件中不存在的连接参数
- 不要跳过版本过滤逻辑（查询和导入均需支持版本号）
- 不要引入与数据处理无关的业务逻辑
