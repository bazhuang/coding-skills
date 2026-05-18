---
name: directed-graph-modeling
description: Convert algorithm ontology objects into NebulaGraph TAG/EDGE schema, DDL execution code.
---

# Directed Graph Modeling

将 `or_ontology` 中的节点和边对象转化为 NebulaGraph 图数据库的 TAG/EDGE 定义，生成 DDL 语句和执行代码。

## 适用输入

用户输入通常包括：

1. 运筹算法本体 JSON（`or_ontology`），包含 `algorithm_objects.objects` 中的节点、边定义及 `table_schema`
2. NebulaGraph 连接配置（`nebula_config`），包含集群地址、图空间、用户名密码等

## 内置参考

- 图映射规则：[references/graph-mapping-rules.md](references/graph-mapping-rules.md)
- Schema 校验定义：[references/nebula_schema_meta.schema.json](references/nebula_schema_meta.schema.json)

## 输出文件

1. **nebula_schema_meta.json** — 结构化中间态（TAG/EDGE 定义），必须通过 JSON Schema 校验
2. **nebula_schema.sql** — 从 nebula_schema_meta.json 渲染的可执行 DDL 语句
3. **ddl_executor.py** — 读取 nebula_schema.sql 和 nebula_config，连接 NebulaGraph 集群并执行 DDL 的 Python 代码

## Workflow

### 1. 读取运筹算法本体

读取输入的运筹算法本体 JSON，识别 `algorithm_objects.objects` 中每个对象的类别、类型、表结构、端点关系。

### 2. 筛选对象

- `object_category: "node"` → 映射为 TAG
- `object_category: "edge"` → 映射为 EDGE

### 3. 生成结构化中间态

按 [graph-mapping-rules.md](references/graph-mapping-rules.md) 中的规则生成 `nebula_schema_meta.json`，必须严格符合 [nebula_schema_meta.schema.json](references/nebula_schema_meta.schema.json) 的定义。

中间态包含：
- `tags[]` — 每个 TAG 的名称、类型、VID 字段、属性字段列表、类型映射、索引等
- `edges[]` — 每个 EDGE 的名称、类型、源/目标 TAG、源/目标 VID 字段、属性字段列表、类型映射、索引等

### 4. JSON Schema 校验

按 [nebula_schema_meta.schema.json](references/nebula_schema_meta.schema.json) 校验生成的中间态：
- 必填字段完整性
- 类型转换符合 MySQL → NebulaGraph 规则
- 每个 EDGE 的 src_tag/dst_tag 存在于 tags 列表中
- 每个 TAG/EDGE 的 fields 包含版本过滤字段
- 每个 TAG/EDGE 的 field_types 覆盖所有 fields
- TAG 名称与 table_schema.table_name 完全一致

**校验不通过时**：返回步骤 3 重新生成，附带具体校验错误信息。

### 5. 渲染 DDL

校验通过后，从 `nebula_schema_meta.json` 渲染 **nebula_schema.sql**：
按 [graph-mapping-rules.md](references/graph-mapping-rules.md) 中的 DDL 格式规则渲染。

### 6. 生成 DDL 执行代码

生成 `ddl_executor.py`，要求：
- 接受 `--ddl-path` 和 `--config-path` 命令行参数
- 从 `--ddl-path` 文件读取 DDL 语句
- 从 `--config-path` JSON 文件读取 NebulaGraph 连接配置（cluster_servers、space、username、password 等）
- 连接 NebulaGraph 集群，逐条执行 DDL 语句
- 输出每条语句的执行结果（成功/失败及错误信息）
- 执行失败时中断并返回错误码

### 7. 交叉引用校验

按 [graph-mapping-rules.md](references/graph-mapping-rules.md) 中的校验规则逐项检查 nebula_schema_meta.json 的一致性。

## 执行流程

本 Skill 通过 `execution_plan.yaml` 定义了三个子步骤：

1. **generate_schema_meta**（LLM）：从 or_ontology 生成 nebula_schema_meta.json 并校验
2. **render_ddl_and_executor**（LLM）：从校验通过的中间态渲染 DDL 并生成执行代码
3. **execute_ddl**（Action）：调用 `ddl_executor.py` 将 DDL 执行到 NebulaGraph 集群

LLM 子步骤负责生成结构化中间态、DDL 和执行代码；Action 子步骤属于外部本地编排行为。该 Action 不是本 skill 的功能前提，skill 的语义、输出约束和图建模规则不得为任何外部触发脚本调整。

## 禁止事项

- 不要修改 `table_schema` 中的表名或字段名
- 不要编造不存在的字段
- 不要遗漏版本过滤字段和索引
- 不要跳过交叉引用校验
- 不要绕过 JSON Schema 校验直接生成 DDL
- **Skill 不直接执行 DDL，只生成可执行代码**

## 质量标准

1. TAG/EDGE 名称与 `table_schema.table_name` 完全一致
2. 字段名称与 `table_schema.fields[].name` 完全一致
3. 大小写全文一致
4. 每个 TAG/EDGE 都有版本过滤字段和对应索引
5. EDGE 的 src_tag/dst_tag 可回溯到 TAG 定义
6. 类型转换严格遵循 MySQL → NebulaGraph 规则表
7. `nebula_schema_meta.json` 必须通过 JSON Schema 校验
