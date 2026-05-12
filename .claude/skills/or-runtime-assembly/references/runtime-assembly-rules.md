# Runtime Assembly Rules

## Boundary

This skill assembles runtime files only. It must not repair upstream business logic.

Allowed:

- Copy files from `data_loader_code_bundle.files`
- Copy `model_builder.py` from `core_code_bundle.files`
- Generate a thin `main.py`
- Generate a concise `README.md`
- Generate `runtime_package_manifest`

Forbidden:

- Reading real runtime config files
- Connecting to MySQL or NebulaGraph
- Running generated Python code
- Executing a solver
- Changing loader/model-builder business logic
- Hardcoding a concrete `version_id`

## Required Runtime Shape

The assembled package uses these paths:

- `db/config/mysql_config.json`
- `db/config/nebula_config.json`
- `graph_path_queries.json`
- `result/<timestamp>_<version_id>/solution/optimization_result.json`
- `result/<timestamp>_<version_id>/solution/result_summary.txt`

`main.py` must expose only one CLI business parameter:

```bash
python main.py --version-id <version_id>
```

Do not add `--config`, `--mysql-config`, `--nebula-config`, `--output-dir`, or other business-facing arguments.

## main.py Interface Contract

`main.py` should import:

```python
from data_loader import DataLoader
from model_builder import build_model, solve_model, parse_result
```

Runtime flow:

1. Parse `--version-id`
2. Create `result/<timestamp>_<version_id>/data` and `result/<timestamp>_<version_id>/solution`
3. Instantiate `DataLoader(graph_path_queries_path="graph_path_queries.json")`
4. Connect, load data, close in `finally`
5. Build model from `data`
6. Solve model
7. Parse result into the solution directory
8. Write `optimization_result.json` and `result_summary.txt`

If the provided loader exposes a different public interface, report the mismatch in `runtime_package_manifest.validation_results.interface_check`; do not hide it by rewriting the loader.

## File Bundle Rules

The `runtime_files` artifact must include:

- `main.py`
- `README.md`
- every file from `data_loader_code_bundle.files`
- every file from `core_code_bundle.files`
- `graph_path_queries.json` when a `graph_path_queries` input is provided

Copied files must preserve their original `content` exactly.

## Manifest Rules

`runtime_package_manifest` must:

- Set `entrypoint` to `main.py`
- Set `runtime_input` to `version_id`
- Use `python main.py --version-id <version_id>` as `run_command`
- Record runtime config paths without real config values
- Record source artifact names
- Record validation results as structured statuses
