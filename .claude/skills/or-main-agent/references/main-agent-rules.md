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

This is the required state order. Specialized stages are mandatory validation/generation passes and must not be skipped due to scenario-profile flags. When a pass has no structural work to perform, it must still produce a completed pass-through or identity artifact with evidence.

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

- No canonical specialized state may be skipped solely because `has_time_dimension=false`, `has_spatial_network=false`, or `requires_path_query=false`.
- If an explicit user-provided `main_agent_flow` disables a state, record the override reason, evidence, and downstream source artifact in `manifest`.

Mandatory time passes:

- `or-time-discretization` must run after `ontology_ready`. If the scenario has no native time dimension or no structural time split is required, it must still produce `time_pipeline_ready` artifacts as a pass-through or identity discretization with evidence that no temporal split was required.
- `or-ontology-time-discretization-adaptation` must run after the time pipeline. If the time pipeline is pass-through or identity, it must still produce `ontology_discretized` as the canonical downstream ontology aligned to the produced discretized schema.

Mandatory graph/path passes:

- `directed-graph-modeling` must run after `time_pipeline_ready`. If the scenario has no native spatial network, it must still produce `graph_schema_ready` artifacts as a pass-through or identity graph contract with evidence that no structural graph expansion was required.
- `or-spatial-path-query` must run after `graph_schema_ready`. If the scenario has no route enumeration requirement, it must still produce `path_query_ready` artifacts as a pass-through or empty path-query contract with evidence that no path enumeration was required.
- Downstream DSL and data-loader stages must consume the canonical path-query artifact, including pass-through or empty path-query artifacts, rather than assuming the path-query stage was absent.

Mandatory DSL passes:

- `or-dsl-nonlinear-optimization` must run after `dsl_ready`. If the DSL is already linear and contains no nonlinear expressions, nonlinear functions, powers, ratios, products of decision variables, or other reformulation needs, it must still produce `dsl_optimized` as a pass-through artifact with evidence that no nonlinear rewrite was required.
- `or-dsl-feasibility-safeguard` must run after `dsl_optimized`. If the DSL has no declared or identified softenable boundary constraints, feasibility-recovery requirement, or relaxation/slack-variable requirement, it must still produce `dsl_safeguarded` as a pass-through artifact with evidence that no feasibility rewrite was required.

Mandatory time, graph/path, and DSL rewrite states should be recorded as completed, even when they make no structural changes.

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
