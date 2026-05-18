---
name: or-data-loader-code
description: Generate runtime Python data loader code for operations-research models. Use when Codex needs to generate code that reads table data from MySQL and feasible path data from NebulaGraph using a time-discretized or_ontology, connection-config schemas, runtime return rules, and graph path queries, while generated code reads database configs from db/config at runtime and the skill itself does not read database configs or execute data reads.
---

# OR Data Loader Code

生成运行态数据读取代码，用于从 MySQL 读取业务表数据、从 NebulaGraph 读取路径数据。

这个 skill 的职责是生成代码，不是连接数据库、查询实例数据或运行生成代码。

## 适用输入

用户输入通常包括：

1. 时间离散适配后的 `or_ontology_time_discretized`
2. `graph_path_queries.json`

内置参考：

1. 代码生成规则
   - 读取 [references/data-loader-code-rules.md](references/data-loader-code-rules.md)
2. MySQL 连接配置 schema
   - 读取 [references/mysql_config.schema.json](references/mysql_config.schema.json)
3. NebulaGraph 连接配置 schema
   - 读取 [references/nebula_config.schema.json](references/nebula_config.schema.json)
4. 图路径查询输入 schema
   - 读取 [references/graph_path_queries.schema.json](references/graph_path_queries.schema.json)
5. `or_ontology_time_discretized` schema
   - 读取 [references/or_ontology_time_discretized.schema.json](references/or_ontology_time_discretized.schema.json)
6. 输出清单 schema
   - 读取 [references/data-loader-code-output.schema.json](references/data-loader-code-output.schema.json)
7. 运行态代码模板
   - 使用 [assets/templates/table_loader.py.jinja2](assets/templates/table_loader.py.jinja2)
   - 使用 [assets/templates/path_loader.py.jinja2](assets/templates/path_loader.py.jinja2)
   - 使用 [assets/templates/data_loader.py.jinja2](assets/templates/data_loader.py.jinja2)
8. 内部执行计划
   - 使用 [execution_plan.yaml](execution_plan.yaml)

## 核心边界

- 只生成运行态 Python 代码
- 不读取 MySQL、NebulaGraph、CSV、JSON 或任何实例数据
- 不验证真实连接可用性
- 不执行生成后的 loader
- 生成代码的运行态输入仍以 `version_id` 为数据版本过滤条件
- 数据表只能从 MySQL 获取，返回为 `tables`
- 路径只能从 NebulaGraph 获取，返回为 `paths`
- MySQL 目标表、字段、主键和版本字段必须从 `or_ontology_time_discretized` 的表绑定信息中抽取
- 生成的运行态代码必须能读取符合 schema 的 MySQL 和 NebulaGraph 配置文件
- 生成的运行态代码必须能根据配置与 MySQL 和 NebulaGraph 建立连接
- 连接配置 schema 是模板契约和校验依据，不是每次生成都必须由用户额外提供的输入
- 不要把连接配置 schema 当作运行态连接配置值
- 数据库实际配置不是生成期输入；生成代码默认从项目根目录 `db/config/mysql_config.json` 和 `db/config/nebula_config.json` 读取配置
- 运行态返回对象结构和读取规则以 [references/data-loader-code-rules.md](references/data-loader-code-rules.md) 为准
- 产物范围是内置参考，固定生成 `table_loader.py`、`path_loader.py`、`data_loader.py`
- `graph_path_queries.json` 用于提供运行态路径查询语句

## Workflow

按 [execution_plan.yaml](execution_plan.yaml) 执行内部子步骤：

1. `extract_generation_spec`：抽取 `data_loader_generation_spec`
2. `generate_code_bundle`：生成 `data_loader_code_bundle`
3. `validate_code_bundle`：自检并输出最终 `data_loader_code_bundle`

子步骤的输入、引用材料、产物 schema 和步骤专属约束以 [execution_plan.yaml](execution_plan.yaml) 为准。

生成代码的详细行为规则以 [references/data-loader-code-rules.md](references/data-loader-code-rules.md) 为准。

## 输出结果

输出生成的代码文件内容；若用户要求结构化清单，按 [references/data-loader-code-output.schema.json](references/data-loader-code-output.schema.json) 输出。

## 禁止事项

- 不要执行数据库连接或查询
- 不要读取或枚举实例数据文件
- 不要把真实数据行、真实路径列表或求解结果写入生成代码
- 不要读取或嵌入 MySQL / NebulaGraph 实际配置内容；只生成读取默认配置路径的能力
- 不要把数据读取逻辑混入模型构建或求解代码
