---
name: or-runtime-assembly
description: Assemble a complete operations-research runtime package from generated data-loader code, core model code, and final DSL artifacts. Use when Codex needs to produce main.py, README.md, a runtime package manifest, and a file bundle without changing loader or model-builder business logic.
---

# OR Runtime Assembly

将已经生成的数据读取代码、核心模型代码和最终 DSL 组装成可交付的运行态工程。

本 skill 只做工程组装，不做业务建模、代码补丁、数据读取或求解执行。

## 适用输入

通常输入：

1. `data_loader_code_bundle`，包含 `table_loader.py`、`path_loader.py`、`data_loader.py`
2. `core_code_bundle`，包含 `model_builder.py`
3. `or_dsl_safeguarded`，用于 README 和 manifest 描述
4. 可选 `graph_path_queries`，若运行态需要路径查询配置文件

## 内置参考

- 组装规则：[references/runtime-assembly-rules.md](references/runtime-assembly-rules.md)
- Runtime package manifest schema：[references/runtime_package_manifest.schema.json](references/runtime_package_manifest.schema.json)
- Runtime files schema：[references/runtime_files.schema.json](references/runtime_files.schema.json)

## 输出

必须输出两个 JSON artifact：

1. `runtime_package_manifest`：运行态包清单，符合 `references/runtime_package_manifest.schema.json`
2. `runtime_files`：运行态文件包，符合 `references/runtime_files.schema.json`

`runtime_files.files[*].content` 中必须包含完整文件内容。

## Workflow

1. 读取输入 bundle，确认 loader 文件和 `model_builder.py` 都存在。
2. 原样复制 loader 和 `model_builder.py` 内容，不改写业务逻辑。
3. 生成薄 `main.py`：
   - 命令行只接受 `--version-id`
   - 调用 `DataLoader(...).load_all(version_id)` 获取 `{"tables": ..., "paths": ...}`
   - 调用 `build_model(data)`、`solve_model(model)`、`parse_result(results, data, output_dir)`
   - 只写运行结果文件，不读取构建期 artifact 或真实配置值
4. 生成 README：
   - 说明运行命令使用 `python main.py --version-id <version_id>`
   - 说明运行态配置路径，不写真实配置值
   - 说明主要文件职责
5. 若提供 `graph_path_queries`，将其作为 `graph_path_queries.json` 加入 `runtime_files`。
6. 生成 `runtime_package_manifest`，记录入口、运行输入、文件职责、配置路径、源 artifact 和检查结果。

## 禁止事项

- 不要修改 `table_loader.py`、`path_loader.py`、`data_loader.py` 的数据读取逻辑
- 不要修改 `model_builder.py` 的模型构建、求解或结果解析逻辑
- 不要读取真实 MySQL 或 NebulaGraph 配置值
- 不要连接数据库、执行路径查询、拆分数据或执行优化求解
- 不要用临时适配代码掩盖 loader 与 model_builder 的接口不匹配
- 不要让 `main.py` 接受具体业务输入，除 `--version-id` 之外只能使用固定运行态路径约定
