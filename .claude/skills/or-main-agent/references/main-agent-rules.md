# Main Agent Rules

## Boundary

The main agent is a build-time orchestrator.

Allowed:

- Build `scenario_profile`
- Select enabled states
- Trigger specialized downstream skills
- Persist artifacts into memory
- Validate schemas, semantic traceability, and build/runtime boundaries
- Track hash, stale state, reverse dependencies, and recovery plans

Forbidden:

- Reading runtime instance data
- Reading real database config values
- Accepting a concrete `version_id` as build-time input
- Running path queries, data splitting, DDL execution, solvers, or generated runtime code
- Fixing downstream skill outputs with local patches

## Input Discovery

When `business_ontology` is not explicitly provided, first look in the current project's `docs/` directory for the business ontology model.

If multiple docs candidates are plausible, prefer files whose names or headings explicitly mention `业务本体模型`, `business_ontology`, or business ontology. If no stable single candidate exists, use the user's explicit path or the local runner input binding instead of guessing.

## Canonical State Order

```text
initialized
-> input_profiled
-> ontology_ready
-> time_pipeline_ready
-> graph_schema_ready
-> path_query_ready
-> ontology_discretized
-> loader_ready
-> dsl_ready
-> dsl_optimized
-> dsl_safeguarded
-> core_code_ready
-> runtime_packaged
-> verified
```

Skip rules:

- `has_time_dimension=false`: skip time pipeline and ontology time adaptation.
- `has_spatial_network=false`: skip graph modeling and path query.
- `requires_path_query=false`: downstream DSL and loaders must not require path query artifacts.

## Specialized Skills

The main agent coordinates these skills without absorbing their responsibilities:

- `business-to-or-ontology`
- `or-time-discretization`
- `directed-graph-modeling`
- `or-spatial-path-query`
- `or-ontology-time-discretization-adaptation`
- `or-data-loader-code`
- `or-ontology-to-dsl`
- `or-dsl-nonlinear-optimization`
- `or-dsl-feasibility-safeguard`
- `or-dsl-to-core-code`
- `or-runtime-assembly`

## Memory

Use a run-local memory layout:

```text
manifest.json
memory/facts/
memory/decisions/
memory/reviews/
files/
```

Facts are the only source of truth for downstream steps. Decisions record the main agent's route and recovery choices. Reviews record gates, unresolved gaps, and validation results.

## Gates

`schema_gate`:

- Validate JSON artifacts against schema.
- Check required files exist.
- Compile generated Python files.

`semantic_gate`:

- Check unresolved blocking gaps.
- Check downstream references trace to upstream artifacts.
- For path-query scenarios, ensure DSL/data loader references runtime `paths` rather than path instances.

`boundary_gate`:

- Reject build-time instance-data reads.
- Reject concrete `version_id` literals.
- Reject path search, data split, DDL execution, solver execution, or generated runtime execution at build time.

## Recovery

Recovery follows artifact dependencies:

- If an upstream fact changes, mark all direct and indirect consumers stale.
- If schema gate fails, rerun the producer of the invalid artifact.
- If semantic gate fails, rerun the producer of the semantic structure, not a downstream code generator.
- If boundary gate fails in generated code, fix the producing skill's rules, schema, references, or templates.
- Never patch artifacts in the main agent to hide downstream skill defects.
