---
name: or-main-agent
description: Orchestrate the full build-time operations-research model generation flow. Use when Codex needs to coordinate OR skills from business inputs through ontology, discretization, graph/path definitions, DSL rewrites, core code, runtime assembly, gates, memory, and recovery while never processing runtime instance data.
---

# OR Main Agent

主导完整的构建时运筹建模代码生成流程：

```text
business input -> or_ontology -> discretized or_ontology -> or_dsl -> runtime code
```

本 skill 只负责编排、记忆、审查和恢复；不替代下游专业 skill 的语义标准化、图建模、路径查询、DSL 生成、DSL 重写或代码生成能力。

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

## Workflow

1. 读取 `business_ontology` 和 `simulation_schema`，形成 `scenario_profile`。
2. 根据 `scenario_profile` 和已产出的 artifact 解析状态机；时间离散、本体时间适配、空间图建模、路径查询、DSL 非线性优化与可行域保障阶段必须执行，必要时产出 pass-through artifact。
3. 按 contract registry 检查每个状态的 required artifact。
4. 触发对应专业 skill，并将其输出写入 `memory/facts` 或 `files`；若状态按规则跳过，在 `manifest` 中记录 skipped reason、证据和下游使用的源 artifact。
5. 每个状态后刷新 artifact metadata、hash、消费者和 stale 状态。
6. 对关键状态执行 gate：`ontology_discretized`、`dsl_safeguarded`、`runtime_packaged`。
7. 若出现失败，按 artifact 反向依赖生成恢复计划；不得在主 agent 内修补专业 skill 输出。

## 禁止事项

- 不读取 MySQL、NebulaGraph、CSV 或 API 中的业务实例数据
- 不接受具体 `version_id` 作为构建时输入
- 不执行路径搜索、数据拆分、优化求解或结果计算
- 不在主 agent 中重写专业 skill 的核心产物来掩盖错误
- 不把外部触发脚本、日志工具或本地执行器作为本 skill 的功能前提
