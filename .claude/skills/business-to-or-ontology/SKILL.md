---
name: business-to-or-ontology
description: Standardize business ontology inputs into a precise or_ontology. Use when Codex needs to normalize business objects, objectives, constraints, and data evidence into an accurate, shallow, natural-language-first result rather than a formulaized model.
---

# Business To OR Ontology

将 `business_ontology` 与 `simulation_schema` 标准化为需供网络导向的 `or_ontology`。

本 skill 只做一件事：从业务全景表达中剥离运筹问题内核，输出浅层、可追溯、自然语言优先的运筹语义结果。若场景不能稳定表达为 `resource + node + edge` 网络，本 skill 不是合适入口。

## 输入边界

使用本 skill 时通常需要两类输入：

- `business_ontology`：业务对象、关系、流动、目标、约束、规则口径和非内核运行流程。
- `simulation_schema`：表结构、字段定义、主键、唯一键/索引、外键或可推断引用关系、数据承载与粒度证据。

源头分工必须清楚：

- `business_ontology` 只提供业务语义；其中内嵌的对象 schema、字段清单、字段说明或表样例一律忽略。
- `simulation_schema` 是结构真值来源；`table_schema`、字段全集、字段顺序、原始字段类型、主键、唯一键、外键和表绑定状态只能以它为准。
- 不得拼接、折中或混合两类输入中的 schema。若二者冲突，以 `simulation_schema` 为准，必要时写入 `open_questions`。

## 必读资源

按任务需要读取：

- [execution_plan.yaml](execution_plan.yaml)：内部两阶段编排、输入输出 artifact。
- [references/需供运筹元模型.md](references/需供运筹元模型.md)：`resource`、`node`、`edge` 及其子类定义。
- [references/or_signal_inventory.schema.json](references/or_signal_inventory.schema.json)：阶段 1 输出 schema。
- [references/本体映射.schema.json](references/本体映射.schema.json)：标准化过程输出 schema。
- [references/or_ontology.schema.json](references/or_ontology.schema.json)：最终 `or_ontology` 输出 schema。

## 输出

必须产出：

- `or_signal_inventory`：阶段 1 中间信号。
- `ontology_mapping`：阶段 2 映射过程与依据。
- `or_ontology`：最终 `or_ontology`。

所有输出必须符合对应 schema。不要输出决策变量、索引集合、线性化、松弛、惩罚设计、求解器代码或 `or_dsl`。

`or_ontology.problem_frame.time_granularity` 是阻断性字段，必须是明确可执行的规划/匹配粒度，例如年度、季度、月度、周度、日度、小时级，或输入中明确命名的业务粒度。若无法确定、信息缺失或证据冲突，先抛出澄清问题；若必须保留草案输出，则在 `open_questions` 写入阻断性问题，并将 `time_granularity` 写为 `未确定（阻断问题：见 open_questions）`。

## 工作流程

### 1. 抽取运筹信号

从 `business_ontology` 和 `simulation_schema` 中剥离运筹问题内核，输出 `or_signal_inventory`。

- 从 `business_ontology` 抽业务对象、资源流动、目标倾向、约束规则、规则口径。
- 从 `simulation_schema` 抽表结构、字段、主键、唯一键、外键/引用关系、数据承载与粒度证据；字段类型必须保留原始数据库类型文本。
- 同步抽取时间粒度证据：计划周期、排程周期、匹配周期、交付/库存/产能约束生效周期、结算周期或明确统计周期。`date`、`datetime`、开始/结束时间字段只能证明存在时间维度，不能单独证明时间粒度。
- 候选对象聚焦资源、节点、连接关系和支撑它们的数据证据；候选目标和候选约束必须逐条保留，约束保留 `confidence`。
- `relevant_fragments` 只保留高价值短证据；`schema_evidence` 必须结构化保留 `table_name`、关键字段、`primary_key`、可稳定识别的 `unique_keys` 和 `foreign_keys`。
- 过滤纯语境、组织、系统建设、管理流程、状态流转、权限职责、记录追踪和数据治理内容。流程机制只有在限定可行域、流动、匹配、数量/时间边界、优先级、条件或例外作用时才抽取为约束。

### 2. 标准化运筹本体

基于 `or_signal_inventory` 标准化对象、目标、约束和数据证据，并重新使用 `simulation_schema` 做结构核对，输出 `ontology_mapping` 与 `or_ontology`。

- 以 `or_signal_inventory` 为主输入，不重新大范围筛读原始业务输入，不引入上游没有出现的核心对象、目标或约束。
- 先校验时间粒度；若只能确认时间窗口、日期字段或宽泛业务周期，必须抛出澄清问题，不能留给 `or-time-discretization` 决定。
- 使用 `simulation_schema` 核对并完整转录结构，不重新发明业务语义。
- 弱推理只允许高度确定的信息，并显式填写 `is_inferred` 与 `inference_basis`。
- 上游候选目标和候选约束必须落入正式结果，或在 `open_questions` 说明无法稳定标准化的原因。

## 标准化规则

### 运筹内核

- `business_ontology` 不是形式化模型，不能机械转写为目标函数和约束集合。
- 数据结构、流程机制和方案管理逻辑只有在稳定支撑资源、节点、连接、目标或约束时才保留。
- 不确定内容写入 `open_questions`，不要用猜测补成建模事实。

### 对象与网络

- 识别顺序：先识别真实流动的 `resource`，再识别承载流动的 `node`，最后识别承载转移或映射关系的 `edge`。
- `resource`：在网络中被供给、运输、消耗、存储或转化的真实流动对象。
- `node`：承载资源产生、消耗、中转、处理或存储的对象。优先使用 `supply_node`、`demand_node`、`passthrough_node`、`processor_node`、`storage_node`。
- `edge`：承载节点之间资源转移或映射连接的对象。实际转移优先为 `transport`，非转移型连接优先为 `link`。
- 若输入存在供给、需求、传输或匹配语义，结果应优先形成 `resource + node + edge` 的网络表达。
- 不要把管理性、规则性、结果性、组织性、流程性或记录性对象直接当成 `resource`、`node` 或 `edge`；若只是供给/需求记录载体，应继续识别背后的节点角色。
- 稳定承载连接语义、且不能稳定描述任一端对象自身属性的数据结构，默认先按 `link` 候选处理，并作为独立候选对象进入 `candidate_entities`。

### 时间粒度

- 时间粒度是 `problem_frame` 核心口径，不是字段类型，也不是单纯的时间窗口存在性。
- 最终 `time_granularity` 必须是单一、明确、可执行的规划/匹配粒度。若存在多层时间口径，说明主优化粒度及其与其他粒度的关系；无法区分主次时必须抛出问题。
- 只有业务口径、计划/排程/匹配/结算周期、约束生效周期或明确数据统计周期能作为时间粒度依据。`date`/`datetime` 字段、开始/结束时间字段、时间窗口重叠约束本身不足以推断日度、周度或月度。
- 不得把“时间窗口”“按交付时间”“后续离散化确认”“日度/月度待确认”等含混表述写入最终明确粒度。
- 下游 `or-time-discretization` 只消费已经明确的时间粒度，不负责决定粒度。

### 数据证据

- schema 只提供数据承载与粒度证据，不替代业务语义。这里的 schema 默认指 `simulation_schema`。
- 关注的非 `resource` 对象必须显式说明 schema 绑定状态：
  - `attached`：对象直接绑定到主表；必须按原表逐字段完整转录 `table_schema`，保留字段顺序、原始类型文本、主键、唯一键和外键信息。
  - `referenced`：只能稳定确认来源表；填写 `supporting_tables`，必要时补 `supporting_fields`。
  - `missing`：无法稳定确认数据支撑；写入 `open_questions`。
- `node` 同时受实体主表和关系表支撑时，优先绑定描述自身属性的实体主表；关系表保留为连接证据。
- `edge` 同时受实体主表和关系表支撑时，优先绑定直接定义关系语义的关系表；实体主表只作补充证据。
- 不得编造表 schema，不得用 `business_ontology` 内嵌 schema 补齐、删减、改名、改序、改类型或覆盖 `simulation_schema` 原表字段。
- 若 `attached.table_schema.fields` 少于原始主表字段数、混入非 `simulation_schema` 字段，或把 `varchar(64)`、`decimal(20,4)` 等原始类型改写为 `string`、`float` 等抽象类型，视为失败。
- 能稳定识别 `UNIQUE KEY` 或唯一索引时，必须写入 `table_schema.unique_keys` 并列出字段组合。能稳定匹配到其他表唯一键字段组合时，必须写入 `table_schema.foreign_keys`；若引用关系明显但被引用侧唯一键不稳定，写入 `open_questions`。

### 目标

- 目标保持浅层、自然语言优先。
- 先拆出清晰、独立的 `objective_terms`，再用 `objective_aggregation` 说明总目标如何包含这些子项。
- 即使业务本质上是单一总目标，只要它由多个可独立解释的业务价值项或代价项构成，也应拆成目标子项。
- 只有原文无法稳定拆解构成项时，才允许退化为单项目标。
- 如需表达式，只允许自然语言加简单数学符号，不输出求解器可直接使用的严格目标函数。

### 约束

- 一条业务规则对应一条约束表达。
- 约束以自然语言表达为主，必要时只补简洁符号。
- 不把多类规则压缩成单条笼统约束。
- 若一段原文包含多条彼此解耦的约束，应拆成多条。只要识别出约束语义，就先抽取为约束，确定性通过 `confidence` 表达。
- `confidence` 只能是 `high`、`medium`、`low`。
- 不补决策变量、bound 推导、slack 设计、线性化策略或公式实现。
- 约束来源包括业务规则，也包括 `simulation_schema` 中语义明确、作用对象稳定、能够表达数量、状态、关系、时间边界或条件作用的字段。
- 候选约束进入阶段 2 后，要么落入正式约束，要么在 `open_questions` 中说明无法稳定标准化的原因，不得静默丢失。
- 若某个 schema 约束字段的作用对象已明确是 `node` 或 `edge`，且字段名或说明表达约束语义，必须进入 `candidate_constraints` 并在阶段 2 落入正式约束，除非存在明确冲突证据。

### 推理与问题

- 只允许高度确定且有明确依据的弱推理。
- 所有推理项都要显式标记 `is_inferred`，并填写 `inference_basis`。
- `open_questions` 只暴露已经出现但信息不足或语义不稳定的疑点。
- `open_questions` 至少包含 `question`，可提供时补充 `evidence_ids` 与 `impact`。

## 质量检查

提交前检查：

1. 是否引入无依据的新概念，或把目标、约束、对象层级混淆。
2. 是否遗漏、合并错或拆坏目标与约束；上游候选目标/约束是否都进入正式结果或 `open_questions`。
3. 是否把管理性对象、记录载体或流程动作误写成 `resource`、`node` 或 `edge`。
4. 是否遗漏明显存在的 `supply_node`、`demand_node` 或 `edge`。
5. `problem_frame.time_granularity` 是否明确；若缺失、含混或冲突，是否已抛出阻断性问题。
6. `attached` 对象的 `table_schema` 是否完整转录原始主表，字段顺序、原始类型、主键、唯一键和外键是否来自 `simulation_schema`。
7. 是否错误地让 `business_ontology` 内嵌 schema 干扰结构输出。
8. 所有输出是否满足对应 JSON Schema，且未输出求解器级公式、变量、线性化或 `or_dsl`。
