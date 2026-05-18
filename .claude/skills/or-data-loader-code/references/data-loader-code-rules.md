# Data Loader Code Rules

## Runtime Contract

Generated code reads data at runtime and returns:

```python
{
    "tables": dict[str, pandas.DataFrame],
    "paths": list[list[Any]],
}
```

`version_id` is the runtime filter for versioned tables and path queries. Static reference tables without a version field are loaded without a version filter.

Data source mapping is fixed:

- `tables` are loaded from MySQL only.
- `paths` are loaded from NebulaGraph only.

Connection-config schema files describe the shape of accepted runtime config files. They are not runtime config values themselves.

Actual database config files are runtime files, not skill-generation inputs:

- default MySQL config path: `db/config/mysql_config.json`
- default NebulaGraph config path: `db/config/nebula_config.json`
- config files must conform to their schemas when the generated code runs

The time-discretized `or_ontology_time_discretized` is required input for MySQL table selection. It must conform to `references/or_ontology_time_discretized.schema.json`.

Generated code should accept overridable file paths, but default to the project-root `db/config` paths. Do not read or embed actual config values during skill generation.

Generated runtime code must:

- read a MySQL config file from `db/config/mysql_config.json` by default
- read a NebulaGraph config file from `db/config/nebula_config.json` by default
- derive the MySQL table read list from `or_ontology_time_discretized`
- read a graph path query file that conforms to `references/graph_path_queries.schema.json`
- validate required fields before opening connections
- establish a MySQL connection for table loading
- establish a NebulaGraph connection for path loading
- expose `version_id` as a runtime parameter and never fill, infer, or hardcode a concrete `version_id` during generation

## File Responsibilities

### table_loader.py

- Load MySQL connection config from a JSON file path or a JSON-compatible config object.
- Treat `references/mysql_config.schema.json` as the accepted config-file contract.
- Build the SQLAlchemy engine or equivalent MySQL client from runtime config values.
- Establish the MySQL connection in `connect()`.
- Use MySQL as the only data source for table data.
- Use `or_ontology_time_discretized.algorithm_objects.objects[*].table_schema` to determine target table names, selected columns, primary keys, and time/version fields.
- For each required table with a version field, execute a parameterized query filtered by the runtime `version_id`.
- For required static reference tables without a version field, execute the table query without a version filter.
- Return `dict[str, pandas.DataFrame]`, keyed by table name.
- Keep table rows inside DataFrames; do not transform them into optimization results.

Preferred interface:

```python
class TableLoader:
    def __init__(self, config_path: str | None = "db/config/mysql_config.json", config: dict | None = None): ...
    def connect(self) -> None: ...
    def close(self) -> None: ...
    def load_table(self, table_name: str, version_id: str) -> pandas.DataFrame: ...
    def load_all(self, version_id: str) -> dict[str, pandas.DataFrame]: ...
```

### path_loader.py

- Load NebulaGraph connection config from a JSON file path or a JSON-compatible config object.
- Treat `references/nebula_config.schema.json` as the accepted config-file contract.
- Load graph path queries from a JSON file path or a JSON-compatible query object.
- Treat `references/graph_path_queries.schema.json` as the accepted path-query contract.
- Connect to one available cluster server and select the configured graph space.
- Establish the NebulaGraph connection in `connect()`.
- Use NebulaGraph as the only data source for path data.
- Use query templates from the graph path query input to query feasible paths.
- Fill the configured `version_id_placeholder` with the runtime `version_id` before executing each query.
- Parse each returned path into a sequence with format `node_id, (edge_id, node_id)+`.
- Return `list[list[Any]]`.

Preferred interface:

```python
class PathLoader:
    def __init__(
        self,
        config_path: str | None = "db/config/nebula_config.json",
        query_config_path: str,
        config: dict | None = None,
        query_config: dict | None = None,
    ): ...
    def connect(self) -> None: ...
    def close(self) -> None: ...
    def load_paths(self, version_id: str) -> list[list[Any]]: ...
```

### data_loader.py

- Compose `TableLoader` and `PathLoader`.
- Keep source ownership fixed: `TableLoader` produces `tables`; `PathLoader` produces `paths`.
- Expose one runtime call that returns both objects.
- Do not contain model-building, solving, or result parsing logic.

Preferred interface:

```python
class DataLoader:
    def __init__(
        self,
        graph_path_queries_path: str,
        mysql_config_path: str | None = "db/config/mysql_config.json",
        nebula_config_path: str | None = "db/config/nebula_config.json",
    ): ...
    def connect(self) -> None: ...
    def close(self) -> None: ...
    def load_all(self, version_id: str) -> dict[str, object]: ...
```

## Generation Strategy

Use the built-in Jinja2 templates for stable code regions:

- `assets/templates/table_loader.py.jinja2`
- `assets/templates/path_loader.py.jinja2`
- `assets/templates/data_loader.py.jinja2`

These templates already cover:

- imports and module layout
- config loading helpers
- config-file schema validation helpers
- class definitions and public method signatures
- MySQL connection setup
- parameterized SQL query skeletons
- Nebula connection setup
- graph path query config loading
- query-template placeholder substitution
- data loader composition

Use LLM-generated code for variable regions:

- template variables for table names, selected columns, primary keys, and version field names extracted from `or_ontology_time_discretized`
- template variables for primary-key mapping used during path parsing
- small helper overrides only when the Nebula result shape cannot be handled by the template
- node and edge business-id extraction
- selection and ordering when multiple `path_queries` are provided
- error messages that name schema-specific objects

When both are present, keep generated flexible snippets inside named template blocks or clearly isolated helper functions.

The MySQL and NebulaGraph config schemas should remain in references as template contracts and regression checks. They do not need to be copied into every generated runtime project unless the user asks for runtime schema validation files.

## Query Rules

MySQL:

- Build connection parameters from runtime config fields such as `host`, `port`, `database`, `username`, `password`, `charset`, `pool_size`, `pool_recycle`, `pool_pre_ping`, `connect_timeout`, and `extra_params` when present.
- Extract target tables from `algorithm_objects.objects[*].table_schema.table_name`.
- Extract selected columns from `algorithm_objects.objects[*].table_schema.fields[*].name`.
- Extract primary keys from `algorithm_objects.objects[*].table_schema.primary_key`.
- Use `version_id` as the version field when present in table fields; if another version field is explicitly represented by the ontology, use that field; if no version field exists, set `version_field` to `null`.
- Use parameterized SQL, not string interpolation for `version_id`.
- Query only the tables required by the time-discretized ontology and downstream model inputs.
- If a table has a `version_id` field, filter by it.
- If a table does not have a version field, document the reason in a code comment and load it as static reference data only when required.

NebulaGraph:

- Build connection parameters from runtime config fields such as `cluster_servers`, `space`, `username`, `password`, `pool_config`, and `session_config` when present.
- Use the configured graph space before querying.
- Execute each `query_template` from the graph path query input after replacing the configured `{version_id}` placeholder.
- Do not invent path query statements when `graph_path_queries.json` is provided.
- Preserve the version filters already expressed in `version_filtering` and `query_template`.
- Preserve the path order returned by Nebula.
- Extract business ids for nodes and edges using schema-derived primary-key fields when available.
- Do not collapse paths into edges, adjacency maps, or aggregate metrics.

Path parsing target:

- The purpose of path parsing is to convert each Nebula path result into one sequence matching `node_id, (edge_id, node_id)+`.
- Existing path parsing implementations may be used as semantic reference for the extraction goal: collect path nodes in order, collect path relationships in order, extract each node and edge business key, then interleave them as node, edge, node, edge, ..., node.
- Do not copy an old parser mechanically if the generated Nebula SDK result shape differs; adapt the implementation while preserving the output structure.
- Node ids should come from the configured primary-key field for the node tag when available.
- Edge ids should come from the configured primary-key field for the edge type when available.
- Preserve Python-native id values instead of forcing all ids to strings.
- If required primary-key mapping is missing or a configured key field is absent from a returned node or edge, fail with an explicit error.
- Path sequences may be inspected by position, such as `path[0]` or `path[-1]`, and by membership, such as `node_id in path` or `edge_id in path`.

## Validation In Generated Code

Generated code should validate:

- Required config fields are present before connecting.
- The graph path query file contains at least one `path_queries` item.
- Each `query_template` contains the configured `version_id_placeholder`.
- `version_id` is non-empty.
- Each returned path has odd length and length at least 3.
- Path positions alternate node, edge, node, edge, ..., node.

## Exclusions

Generated code must not:

- run during generation
- query databases at build time
- read local instance data files at build time
- execute optimization solvers
- compute business metrics
- write model results
