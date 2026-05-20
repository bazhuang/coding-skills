---
name: or-main-agent
description: "Entrypoint for explicit end-to-end operations-research algorithm/runtime generation, such as 运筹算法打造, 运筹算法生成, 运筹建模代码生成, or requests to generate a runnable OR package from business ontology and simulation schema. Use when Codex needs to coordinate the full build-time OR skill chain from or_ontology, mandatory time discretization, graph modeling, path queries, DSL generation, nonlinear optimization, feasibility safeguard, core code, runtime assembly, gates, memory, and recovery while never processing runtime instance data. For exploratory OR business requests that have not yet completed ontology modeling, use or-workflow-guide first."
---

# OR Main Agent

主导完整的构建时运筹建模代码生成流程：

```text
business input -> or_ontology -> discretized or_ontology -> or_dsl -> runtime code
```

本 skill 只负责编排、记忆、审查和恢复；不替代下游专业 skill 的语义标准化、图建模、路径查询、DSL 生成、DSL 重写或代码生成能力。

## 触发入口

当用户明确提出“运筹算法打造”、“运筹算法生成”、“运筹建模代码生成”或要求从业务本体/schema 端到端生成可运行运筹代码时，触发本 skill 作为主编排入口，再由本 skill 顺序调用下游专业 skill。若用户只是描述需供运筹、供需匹配优化、资源调度优化、路径流/网络流优化等业务问题，且尚未完成本体建模，先使用 `or-workflow-guide`。

## 适用输入

通常输入：

1. `business_ontology`：业务本体、目标、约束与数据承载线索
2. `simulation_schema`：权威仿真表结构或表 schema
3. 可选 `main_agent_flow`：状态机、artifact、skill contract 和 gate 配置
4. 可选历史 `manifest`：用于恢复、stale 判断和局部重跑

若用户未显式提供 `business_ontology` 文件，优先在当前项目的 `docs/` 目录查找业务本体模型相关文件；若 `docs/` 中无法稳定确定唯一业务本体模型，再要求用户提供。

## 内置参考

- 主流程规则：[references/main-agent-rules.md](references/main-agent-rules.md)
- 场景画像 schema：[references/scenario_profile.schema.json](references/scenario_profile.schema.json)
- Artifact 元信息 schema：[references/artifact_metadata.schema.json](references/artifact_metadata.schema.json)
- Run manifest schema：[references/main_agent_manifest.schema.json](references/main_agent_manifest.schema.json)
- Gate result schema：[references/gate_results.schema.json](references/gate_results.schema.json)

## 输出

按任务阶段输出以下 artifact 中的一种或多种：

1. `scenario_profile`
2. `main_agent_plan`
3. `manifest`
4. `gate_results`
5. `recovery_plan`

若任务要求执行完整流程，必须持续更新 `manifest`，并把每个下游 skill 的产物写入记忆层。

## 输出目录契约

所有主 agent 输出目录必须相对项目根目录解析。项目根目录是包含 `.claude/skills/` 的当前 workspace 根目录，不是 `.claude/skills/` 或任一 skill 定义目录。

主 agent 必须使用以下项目根目录相对位置：

| 位置 | 内容 |
| --- | --- |
| `manifest.json` | 运行清单、状态计划、artifact metadata、hash、依赖和 stale 状态 |
| `memory/facts/` | 下游步骤消费的结构化事实 artifact，是后续流程唯一事实源 |
| `memory/decisions/` | 主 agent 编排决策、跳过原因、恢复计划和路线选择 |
| `memory/reviews/` | gate/review 结果、未解决缺口和校验报告 |
| `files/` | 构建过程中生成的文件型产物或中间文件，例如代码、SQL、bundle 文件 |
| `runtime/` | `or-runtime-assembly` 物化后的最终运行级项目 |

写入前必须创建缺失的 `memory/facts/`、`memory/decisions/`、`memory/reviews/`、`files/` 和 `runtime/` 目录。

完整链路中的 JSON 事实产物默认进入 `memory/facts/`；主 agent 的计划、跳过原因和恢复方案进入 `memory/decisions/`；gate 和 review 结果进入 `memory/reviews/`；代码、SQL、配置草案等构建期文件进入 `files/`；最终运行级项目只由 `or-runtime-assembly` 物化到 `runtime/`。若下游 skill 只返回 bundle JSON，主 agent 负责按 bundle 内相对文件名决定是否物化到 `files/` 或 `runtime/`。

## Workflow

1. 读取 `business_ontology` 和 `simulation_schema`，形成 `scenario_profile`。
2. 根据 `scenario_profile` 和已产出的 artifact 解析状态机；时间离散、本体时间适配、空间图建模、路径查询、DSL 非线性优化与可行域保障阶段必须执行，必要时产出 pass-through artifact。
3. 按 contract registry 检查每个状态的 required artifact。
4. 触发对应专业 skill，并将其输出写入项目根目录下的 `memory/facts` 或 `files`；这些路径必须相对项目根目录解析，不得写入 `.claude/skills/files`；若状态按规则跳过，在 `manifest` 中记录 skipped reason、证据和下游使用的源 artifact。
5. 每个状态后刷新 artifact metadata、hash、消费者和 stale 状态。
6. 对关键状态执行 gate：`ontology_discretized`、`dsl_safeguarded`、`runtime_packaged`。
7. 若出现失败，按 artifact 反向依赖生成恢复计划；不得在主 agent 内修补专业 skill 输出。

## Skill 调用流程

主 agent 必须按以下顺序调用专业 skill。除非用户显式提供的 `main_agent_flow` 禁用某状态，否则不得因为 `has_time_dimension=false`、`has_spatial_network=false` 或 `requires_path_query=false` 跳过专业阶段；无结构性改写时应产出 completed 的 pass-through / identity artifact，并在 `manifest` 记录证据。

| 状态 | 调用 skill | 主要输入 | 主要输出 |
| --- | --- | --- | --- |
| `input_profiled` | 主 agent 内部画像 | `business_ontology`, `simulation_schema` | `scenario_profile` |
| `ontology_ready` | `business-to-or-ontology` | `business_ontology`, `simulation_schema` | `or_ontology` |
| `time_pipeline_ready` | `or-time-discretization` | `or_ontology`, `simulation_schema` | `discretized_schema`, time pipeline artifacts |
| `graph_schema_ready` | `directed-graph-modeling` | `or_ontology`, `discretized_schema` | `graph_modeling_sql`, graph schema artifacts |
| `path_query_ready` | `or-spatial-path-query` | `graph_modeling_sql` | path query artifacts |
| `ontology_discretized` | `or-ontology-time-discretization-adaptation` | `or_ontology`, `discretized_schema` | `or_ontology_time_discretized` |
| `loader_ready` | `or-data-loader-code` | `or_ontology_time_discretized`, path query artifacts | runtime data loader code |
| `dsl_ready` | `or-ontology-to-dsl` | `or_ontology_time_discretized`, loader/path contracts | `or_dsl` |
| `dsl_optimized` | `or-dsl-nonlinear-optimization` | `or_dsl` | `dsl_optimized` |
| `dsl_safeguarded` | `or-dsl-feasibility-safeguard` | `dsl_optimized` | `dsl_safeguarded` |
| `core_code_ready` | `or-dsl-to-core-code` | `dsl_safeguarded` | core optimization code |
| `runtime_packaged` | `or-runtime-assembly` | loader code, core code, final DSL | runtime package |
| `verified` | 主 agent gate/review | `ontology_discretized`, `dsl_safeguarded`, `runtime_packaged` | `gate_results`, `manifest`, reviews |

`runtime_packaged` 阶段必须遵循 `or-runtime-assembly` 的输出目录契约：最终运行级项目根目录为 `runtime/`，运行包内文件路径均相对 `runtime/` 且不得带 `runtime/` 前缀。

完整调用链：

```text
business-to-or-ontology
-> or-time-discretization
-> directed-graph-modeling
-> or-spatial-path-query
-> or-ontology-time-discretization-adaptation
-> or-data-loader-code
-> or-ontology-to-dsl
-> or-dsl-nonlinear-optimization
-> or-dsl-feasibility-safeguard
-> or-dsl-to-core-code
-> or-runtime-assembly
```

## 禁止事项

- 不读取 MySQL、NebulaGraph、CSV 或 API 中的业务实例数据
- 不接受具体 `version_id` 作为构建时输入
- 不执行路径搜索、数据拆分、优化求解或结果计算
- 不在主 agent 中重写专业 skill 的核心产物来掩盖错误
- 不把外部触发脚本、日志工具或本地执行器作为本 skill 的功能前提
