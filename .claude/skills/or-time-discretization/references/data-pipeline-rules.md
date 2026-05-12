# Data Pipeline Rules

## 1. Overview

本文件描述 or-time-discretization skill 中 4 个模板的代码生成规则。

- **表信息**来源：`or_ontology.json` → `algorithm_objects.objects`
- **时间拆分**来源：`time_discretization_config.json`
- **连接配置**来源：`mysql_config.json` / `nebula_config.json`

---

## 2. 从 or_ontology 提取表信息

### 2.1 表列表

从 `or_ontology.algorithm_objects.objects` 中筛选 `object_category` 为 `"node"` 或 `"edge"` 的对象，取其 `table_schema.table_name` 构成完整表列表。

| 分类 | 取值路径 |
|------|----------|
| node 表 | `objects[].object_category == "node"` → `objects[].table_schema.table_name` |
| edge 表 | `objects[].object_category == "edge"` → `objects[].table_schema.table_name` |

### 2.2 字段信息

从 `objects[].table_schema.fields[]` 获取：
- `name` — 字段名
- `type` — 数据类型
- `desc` — 字段描述
- `is_required` — 是否必填

### 2.3 VID 字段规则

- **node 对象**：`table_schema.unique_keys.fields` 中的唯一键字段作为 VID
- **edge 对象**：从 `edge_endpoints.supporting_fields` 中取第一个字段作为源点标识，最后一个作为目标点标识

### 2.4 MySQL 查询模板（mysql_query.py）

- 查询的表列表必须从 or_ontology 提取，不得硬编码
- 生成的 `MySQLQueryExecutor` 接受 `config_path`（mysql_config.json）
- 按版本号过滤时，先通过 `information_schema.COLUMNS` 检查该字段是否存在
- 表名列表由生成代码直接嵌入
- **extra_params 处理**：读取配置时忽略 `extra_params` 字段，不将其拼接到连接 URL 或 `connect_args` 中，避免 JDBC 风格参数导致 PyMySQL 驱动异常
- **禁止使用 `pymysql`、`dbutils`、`PooledDB`**：必须使用 SQLAlchemy 的 `create_engine` 作为数据库连接方式，通过连接池参数（`pool_size` / `pool_recycle` / `pool_pre_ping`）管理连接
- **`connect_timeout` 必须放在 `connect_args` 字典中**，禁止作为 `create_engine()` 的直接参数（PyMySQL dialect 不识别该参数）
- 数据查询必须使用 `pandas.read_sql` 返回 DataFrame，不得使用原生 cursor 和 DictCursor

### 2.5 Nebula 导入模板（nebula_import.py）

- **配置常量**：必须定义 `TAGS_CONFIG` 和 `EDGES_CONFIG` 两个全局常量，每个元素包含：名称、源表名、VID 字段（node 从唯一索引字段过滤版本字段，edge 从端点支持字段取首尾）、字段列表、字段类型映射
- **命名约束**：节点/边的名称必须严格等于本体定义中的表名，不得使用别名
- **禁止使用 `ValueWrapper`**：直接拼接 NGQL 字符串，按类型分别处理引号转义、NULL、布尔值、日期格式化
- **禁止硬编码单表导入逻辑**：必须遍历配置常量动态执行导入
- **NGQL 语法**：TAG 使用 `INSERT VERTEX`，EDGE 使用 `INSERT EDGE`
- **属性值格式**：必须使用位置值格式，不得使用 `key: value` 格式。正确示例：`INSERT VERTEX \`tag\` (\`a\`, \`b\`) VALUES 'vid':('val_a', 123);`
- **包裹规则**：VID 使用单引号包裹，属性和表名使用反引号包裹
- **批量大小**：固定 256 条一批，单条失败不影响同批其他记录
- **VID 构成**：版本前缀 + VID 字段值，多字段时用下划线拼接
- **映射内嵌**：所有映射信息内嵌到生成代码中，不得依赖外部配置文件
- **字段类型映射**：配置中必须包含 `field_types` 字段，将本体数据类型映射为图数据库类型，禁止在运行时硬编码类型转换
- **类型感知格式化**：`bool` → `true`/`false`；`int`/`int64` → 纯数字（try/except 保护）；`double` → 浮点数字符串；`date` → `date('YYYY-MM-DD')`；`datetime`/`timestamp` → 对应构造函数（空格替换为 `T`）；`string` → 单引号包裹并转义反斜杠和单引号
- **空时间值处理**：JSON 序列化会将 NaT 转为字符串，格式化时需检测该字符串并输出 `NULL`
- **版本号缺失时自动填充**：如果数据 DataFrame 中不包含版本过滤字段，必须在拼接属性时显式将该字段名和传入的版本参数值添加到 NGQL 语句中，禁止以 `NULL` 值写入。具体：先检测版本字段是否在 `df.columns` 中；遍历字段时跳过该字段（若不在数据中）；处理完后手动追加版本字段名和版本参数值

---

## 3. 时间拆分配置

### 3.1 配置来源

`time_discretization_config.json` 结构：

顶层结构：

| key | 类型 | 说明 |
|-----|------|------|
| `objects` | array | 含时间维度的对象列表，每个元素对应 or_ontology 中一个含 time_dimension 的对象 |

`objects[]` 数组元素结构：

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `object_name` | string | or_ontology 对象名称 | 对象名称 |
| `object_category` | string | or_ontology object_category | 枚举值：`node`、`edge` |
| `table_name` | string | or_ontology table_schema.table_name | 原始表名 |
| `start_time_field` | string | or_ontology table_schema.fields[].name | 开始时间字段，必须能在 fields 中找到 |
| `end_time_field` | string | or_ontology table_schema.fields[].name | 结束时间字段，必须能在 fields 中找到 |
| `time_interval` | string | or_ontology time_dimension | 枚举值：`Y`、`Q`、`M`、`W`、`D` |
| `quantity_fields` | string[] | or_ontology table_schema.fields[].name | 具有实际业务量含义的字段，代表可被拆分的总量，不包含衍生或换算型数值 |
| `discretized_table` | string | 生成规则 | 格式 `discretized_{table_name}`，不得与 or_ontology 中现有表名冲突 |

### 3.2 拆分模板（data_split.py）

- **配置加载**：从 `time_discretization_config.json` 读取拆分配置，构造函数接受图数据库连接配置路径、时间拆分配置路径、版本号、关系型数据库连接配置路径四个参数
- **管线入口**：`process_all_splits()` 遍历配置中的对象数组，按对象类型分发到对应的图查询方法，逐个执行拆分并写回
- **版本过滤强制要求**：图数据库查询必须以版本号作为必填过滤条件，未传入时应主动抛出异常而非降级为全量查询；节点按 VID 前缀匹配，边按源点和目标点 VID 前缀同时匹配；命令行参数应设为必填
- **复杂类型转换**：图数据库返回的日期/时间封装对象必须通过 getter 方法提取各组件构造原生时间类型（`pd.Timestamp`），禁止直接调用 `str()` 转换（会产生带时区描述的格式，无法被关系型数据库识别）。方法名必须准确：`get_sec()` 而非 `get_second()`，`pd.Timestamp` 微秒参数名为 `microsecond=` 而非 `microsec=`
- **属性访问规范**：图和边的属性获取接口为方法调用而非属性访问，必须加括号调用，节点调用需传入 tag 名称参数
- **写入时间格式**：写入关系型数据库前必须将时间列转为字符串格式，避免 datetime64 和 Timestamp 对象的类型兼容性问题
- **冗余字段排除**：拆分结果写入时必须排除已被替代的原始字段（时间范围字段被 `time_period` 替代，量值原始字段被 `discretized_` 前缀字段替代），以及图查询引入的内部标识字段
- **ResultSet 遍历规范**：nebula3 的 `session.execute()` 返回 `ResultSet` 可迭代对象，直接遍历，不存在 `.data()` 方法。正确模式：`for record in resp:` → `record.values()[0].as_node()` / `.as_relationship()`
- **边查询版本过滤**：NebulaGraph 不支持对 `id(e)` 使用 `STARTS WITH`，必须匹配边两端节点：`MATCH (src)-[e:name]->(dst) WHERE id(src) STARTS WITH 'ver_' AND id(dst) STARTS WITH 'ver_'`

### 3.3 拆分逻辑

- `time_interval` 到 pandas offset 的映射：
  - `Y` → `'1YS'`（年）
  - `Q` → `'1QS'`（季度）
  - `M` → `'1MS'`（月）
  - `W` → `'1WS'`（周）
  - `D` → `'1D'`（日）

- **时间窗口生成**：使用 `while cur < end` 循环按 offset 逐步推进窗口，每次计算与原始区间的重叠秒数。禁止使用 `pd.date_range(start, end, freq)` 后遍历 `len(periods) - 1` 的模式，因为当起止时间在同一区间时 `date_range` 仅返回 1 个元素，导致窗口循环 0 次、拆分结果为空

### 3.4 拆分结果表 DDL（discretized_schema.sql）

每个含 time_dimension 的对象生成一张拆分结果表，DDL 字段规则如下：

**表名**：`discretized_{table_name}`（与 `time_discretization_config.objects[].discretized_table` 一致）

**字段组成**：

| 字段类别 | 说明 |
|----------|------|
| 主键 | 自增主键 |
| 时间维度 | 固定字段名 `time_period`，日期时间类型，拆分后的时间标识 |
| 拆分结果 | 每个 quantity_field 对应一个拆分后数值列，前缀 `discretized_`，字段类型与原字段保持一致 |
| 其余字段 | 从本体定义的完整字段列表中获取，排除列表中外的所有字段，**必须全部保留**，包括描述性字段和元数据字段，不得编造或遗漏任何字段 |

**排除列表**：以下字段不进入拆分结果表：
- 主键（由 DDL 重新定义）
- 时间范围字段（被时间维度字段替代）
- 量值原始字段（被 `discretized_` 前缀字段替代）

**字段生成流程**：

1. 从本体定义中取出该对象对应的完整字段列表（含所有业务字段和元数据字段）
2. 逐个遍历每个字段，判断是否在排除列表中
3. 不在排除列表中的字段，**必须全部写入 DDL**，不得遗漏或跳过任何字段

**字段名称与 COMMENT 约束**：
- 字段名必须严格等于本体定义中的字段名，不得重命名或编造
- COMMENT 必须严格等于本体定义中的字段描述，不得使用占位文本

**数据写入约束**：
- 拆分后的数据写入 DDL 定义的对应表
- 仅保存拆分结果 DataFrame 中存在的字段
- 写入前先清理同版本的旧数据

**唯一索引**：
- 为本体定义中该对象的 `table_schema.unique_keys` 中的每个唯一键生成对应的 MySQL 唯一索引
- 唯一索引字段组合为：版本字段（从本体 `table_schema.fields` 中筛选，字段名包含 `version` 的字段） + `unique_keys[].fields` 中的字段 + `time_period`
- 版本字段必须从本体定义中获取，不得编造字段名
- 索引命名格式：`uniq_{table_name}_index`

---

## 4. 管线编排模板（data_pipeline.py）

### 4.1 参数

- `mysql_config_path` — MySQL 连接配置
- `nebula_config_path` — NebulaGraph 连接配置
- `time_config_path` — 时间拆分配置（time_discretization_config.json）

### 4.2 执行流程

1. Step 1：查询 MySQL 仿真表数据（按版本过滤）
2. Step 2：将查询结果导入 NebulaGraph 图数据库
3. Step 3：从 NebulaGraph 读取数据，按时间维度拆分，将拆分结果写回 MySQL 中 DDL 定义的对应表

### 4.3 步骤间数据传递

- **内存传递优先**：管线编排应尽量通过内存传递 DataFrame 对象，避免跨步骤的文件序列化开销和类型丢失
- **JSON 序列化传递**：若使用 JSON 临时文件传递 DataFrame 数据，查询端必须先调用 `.to_dict(orient="records")` 将 DataFrame 转为记录列表后再序列化，禁止直接 `json.dump(DataFrame, ...)`；由于记录中可能包含 `pd.Timestamp` 等不可 JSON 序列化的类型，必须添加 `default=str` 参数将这类值转为字符串
- **JSON 反序列化**：加载端读取 JSON 后调用 `pd.DataFrame(v)` 恢复时，必须先校验 `v` 是否为 `list` 类型，非列表类型应转为空 DataFrame 占位，避免 `pd.DataFrame` 构造函数参数校验异常

### 4.4 与 or_ontology 的关系

- mysql_query.py 和 nebula_import.py 的表列表信息已在生成时嵌入代码
- data_split.py 通过 `time_config_path` 获取拆分规则
- 版本过滤字段名从 or_ontology 中提取

---

## 5. NebulaGraph API 约束

### 5.1 连接配置 API

- **只能从 `nebula3.Config` 导入 `Config` 和 `SessionPoolConfig`**
- **禁止使用 `PoolConfig`、`SessionConfig`**（这些类在 nebula3 中不存在）
- `Config` 可用属性：
  - `min_connection_pool_size`（最小连接池大小）
  - `max_connection_pool_size`（最大连接池大小）
  - `idle_time`（空闲时间）
  - `timeout`（超时）
  - `interval_check`（检查间隔）
  - `use_http2`（是否使用 HTTP/2）

### 5.2 ConnectionPool API

- `ConnectionPool.init(addresses, configs=None, ssl_conf=None)` — `addresses` 为 `(host, port)` tuple 列表
- `ConnectionPool.get_session(user_name, password, retry_connect=True)` — 不接受额外的 session_config 参数
- 连接代码中禁止调用 `session.release()` 后再使用 session
- **每次获取新 session 后必须执行空间切换**：无论是创建新 session 还是复用持久 session，在执行任何数据查询或写入操作前必须先执行 `USE {space}` 切换空间
- **禁止导入图数据库内部类型类**：不使用 `isinstance` 检查底层封装类型，应通过对象自身的方法（`is_null()`、`is_datetime()`、`is_date()` 等）进行类型检测和值提取
---

## 6. 校验规则

### 6.1 生成时校验

- `mysql_query.py` 的表列表应与 or_ontology 中所有 node/edge 的表名一致
- `mysql_query.py` 必须使用 SQLAlchemy 的 `create_engine` 和 `pandas.read_sql`，禁止使用 `pymysql`、`dbutils`、`PooledDB`
- `nebula_import.py` 必须包含 `TAGS_CONFIG` 和 `EDGES_CONFIG` 全局常量，从 or_ontology 提取，禁止硬编码单个表的导入逻辑
- `nebula_import.py` 必须包含 `import pandas as pd`，不得省略此导入（`_format_value` 中使用 `pd.isna` 进行 NaN 检测）
- `nebula_import.py` 禁止导入或使用 `ValueWrapper` 类，应直接拼接 NGQL 字符串
- `data_split.py` 的拆分对象必须全部来自 `time_discretization_config`
- 生成代码不应包含 `PoolConfig`、`SessionConfig` 导入
- 生成代码禁止从图数据库驱动的内部类型模块中显式导入封装类型，应通过对象自身提供的类型检测方法进行值转换操作，无需引用底层封装类
- 所有 `version` 参数必须在函数体中被实际使用
- 不得定义未使用的局部变量
- 跨步骤使用 JSON 文件传递 DataFrame 数据时，序列化端必须使用 `.to_dict(orient="records")`，反序列化端必须校验值为 `list` 类型后再构造 DataFrame
- 图数据库导入代码中 `_format_value` 或等效方法必须按 `field_types` 映射进行类型感知的值格式化，不得将所有值统一当作字符串处理
- 图数据库导入代码中 `_format_value` 或等效方法必须处理序列化后的空时间值字符串，输出 `NULL`
- 数据拆分代码中从图数据库读取的封装类型必须提取组件转换为原生值，不得直接使用 `str()` 转换
- 数据拆分代码写入关系型数据库前必须将时间列转为字符串格式
- 数据拆分代码写入拆分结果表前必须排除时间范围字段和量值原始字段
- 图数据库导入代码中每次创建新 session 后必须先执行空间切换语句再进行数据操作，持久化 session 也必须在连接初始化阶段完成空间切换
- 数据拆分代码中从图数据库读取节点时，必须通过 `vertex.properties(tag_name)` 方法（带括号和 tag 参数）获取属性，禁止使用 `vertex.properties` 属性访问
- 数据拆分代码中从图数据库读取边时，必须通过 `edge.properties()` 方法（带括号）获取属性，禁止使用 `edge.properties` 属性访问
- **图数据库查询方法使用规范**：nebula3 的 `ResultSet` 为可迭代对象，应直接遍历，不存在 `.data()` 方法；`session.execute()` 返回 `ResultSet`，直接 `for record in resp:` 遍历，通过 `record.values()[0]` 获取元素。禁止调用不存在的 `.data()` 方法
- **边查询版本过滤必须按源点和目标点分别过滤**：NebulaGraph 不支持对 `id(e)` 使用 `STARTS WITH`，必须使用 `MATCH (src)-[e:edge_name]->(dst) WHERE id(src) STARTS WITH 'ver_' AND id(dst) STARTS WITH 'ver_'` 分别匹配两端节点 VID 前缀
- **时间封装类型 getter 方法名必须准确**：`TimeWrapper` 的秒数方法为 `get_sec()`，禁止使用 `get_second()`；`DateTimeWrapper` 构造 `pd.Timestamp` 时微秒参数名为 `microsecond=`，禁止使用 `microsec=`

### 6.2 运行时校验

- 查询前通过 `information_schema` 检查版本过滤字段是否存在，不存在则降级为全表查询并输出警告
- 所有 NebulaGraph 连接（`nebula_import.py`、`data_split.py`）必须使用集群连接模式，一次性传入所有节点地址给 `ConnectionPool.init`，由连接池内部处理路由和故障转移，禁止逐个节点尝试连接
- 时间拆分时对 NaN、无效时间区间（start >= end）、总量为零的情况做保护处理
- 图数据库查询返回的复杂类型（DateWrapper、DateTimeWrapper）需正确转换为 Python 原生值
- 写入关系型数据库前先清理同版本旧数据，避免重复写入
- 单表查询失败不影响后续表的查询，返回空 DataFrame 占位

---

## 7. 代码稳定性要求

### 7.1 连接管理

- 所有数据库连接必须在 `finally` 块中释放，异常发生时也不泄漏
- 关系型数据库使用连接池（`pool_size` / `pool_recycle` / `pool_pre_ping`），禁止每次查询新建连接
- 图数据库使用集群连接模式，一次性传入所有节点地址给 `ConnectionPool.init`，由连接池内部处理路由和故障转移
- 连接方法中必须测试连通性（执行 `USE {space}` 切换空间），确保后续操作可用

### 7.2 异常处理

- 关键操作方法使用 `try/except/finally` 结构，异常信息通过 `logging.error` 输出
- `main()` 函数使用 `try/except` 捕获顶层异常，失败时 `sys.exit(1)`
- 单条记录插入失败不影响批量中其他记录，记录失败数继续执行
- 空 DataFrame 或空数据时跳过后续操作，不抛异常

### 7.3 批量操作

- 图数据库导入使用固定批量大小（256），避免单次事务过大导致超时
- 关系型数据库写入使用 `chunksize` 分批插入
- 批量操作完成后记录成功/失败统计，便于问题定位

### 7.4 数据兼容

- 图数据库返回的复杂类型（DateWrapper、DateTimeWrapper）需转换为 Python 原生值
- 时间字段写入关系型数据库前转为字符串格式，避免 MySQL 类型兼容问题
- `NaN` / `None` 统一转换为 `NULL`，不同类型按 string/int/double/bool/date/datetime 分别格式化
- 拆分结果为空时返回空 DataFrame 而非报错，管线继续执行
