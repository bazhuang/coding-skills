---
name: business-to-or-ontology
description: Standardize business ontology inputs into a precise or_ontology. Use when Codex needs to normalize business objects, objectives, constraints, and data evidence into an accurate, shallow, natural-language-first result rather than a formulaized model.
---

# Business To OR Ontology

将 `business_ontology` 标准化为需供网络导向的 `or_ontology`。

本 skill 只做一件事：从业务全景表达中剥离运筹问题内核，并把它标准化为浅层、可追溯、自然语言优先的运筹语义结果。

## 适用输入

使用本 skill 时通常需要两类输入：

- `business_ontology`：以对象、关系和规则组织的“运筹业务应用全景表达”。它不是优化问题的形式化定义，常混合对象定义、关系结构、流动机制、规则边界、管理流程、系统对象与运行口径。
- `simulation_schema`：表 schema 或仿真表 schema，用于提供表结构、字段定义、主外键关系、唯一键/索引定义、仿真表定义及数据承载证据。

输入边界必须明确区分：

- `business_ontology` 中若内嵌了对象 schema、字段清单、字段说明或表样例，这些内容一律忽略，不参与对象识别、规则抽取、结构绑定或命名判断。
- `simulation_schema` 是数据结构真值来源；`table_schema`、字段全集、字段顺序、主键、唯一键、外键和表绑定状态只能以它为准。
- `simulation_schema` 中的字段类型也必须原样保留到 `table_schema.fields[*].type`，例如 `varchar(64)`、`bigint(20) unsigned`、`decimal(20,4)`、`datetime`、`date`。
- 不得把 `business_ontology` 内嵌 schema 与 `simulation_schema` 拼接、折中或混合成新的 `table_schema`。
- 若 `business_ontology` 内嵌 schema 与 `simulation_schema` 冲突，直接忽略前者，只以 `simulation_schema` 为准；必要时可把冲突写入 `open_questions`。

若场景不能稳定表达为需供网络中的 `resource`、`node`、`edge`，本 skill 不是合适入口。

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

特别要求：`or_ontology.problem_frame.time_granularity` 是阻断性字段，必须明确为一个可执行的规划/匹配时间粒度，例如年度、季度、月度、周度、日度、小时级，或输入中明确命名的业务粒度。若输入无法确定粒度、信息缺失或证据冲突，必须先抛出澄清问题；若流程必须保留草案输出，则在 `open_questions` 写入阻断性问题，并将 `time_granularity` 写为 `未确定（阻断问题：见 open_questions）`，不得猜测补齐。

所有输出必须符合对应 schema。不要输出决策变量、索引集合、线性化、松弛、惩罚设计、求解器代码或 `or_dsl`。

## 工作流程

### 1. 抽取运筹信号

从 `business_ontology` 和 `simulation_schema` 中剥离运筹问题内核，输出 `or_signal_inventory`。

抽取时必须先做源头分工：

- 从 `business_ontology` 抽业务对象语义、流动语义、目标语义、约束语义和规则口径。
- 从 `simulation_schema` 抽表结构证据、字段证据、主键/唯一键/索引证据、关系证据和数据粒度证据。
- 同步抽取时间粒度证据，例如计划周期、排程周期、匹配周期、交付/库存/产能约束生效周期、结算周期，或业务输入中明确给出的年度/季度/月度/周度/日度/小时级口径。
- `simulation_schema` 的字段类型按原始数据库类型字符串抽取，不做 `varchar -> string`、`decimal -> float`、`tinyint -> boolean/int` 这类归一化。
- 忽略 `business_ontology` 内嵌 schema、字段清单、字段说明和表样例；它们不能作为 `simulation_schema` 的替代来源，也不能参与字段集合、对象命名或关系结构判断。
- `date`、`datetime`、`delivery_start_time`、`delivery_end_time` 等时间字段只能证明存在时间维度或时间窗口，不能单独证明时间粒度；若没有稳定周期口径，必须进入信息不足问题。

第一阶段输出要尽量短，只保留后续标准化真正需要的证据：

- `relevant_fragments` 只保留高价值短证据，不要大段复述输入。
- 来自 `simulation_schema` 的证据优先通过表名引用，显式填写 `table_name`，必要时只补少量关键字段名。
- 不要把整段 DDL、长字段串或长业务原文搬进中间文件；长输入应被压缩为“表名 + 关键字段/规则点”的可追溯信号。
- `schema_evidence` 必须结构化保留 `table_name`、关键字段、`primary_key`、可稳定识别的 `unique_keys` 和 `foreign_keys`，不要仅写成自由文本说明。

抽取对象：

- 业务需求描述
- 目标倾向
- 约束规则
- 资源流动对象
- 供给、需求、中转、处理、存储节点
- 运输或连接关系
- 支撑上述内容的数据证据

过滤对象：

- 只提供语境、组织、系统建设或实施过程的内容。
- 只表达管理流程、操作流程、系统流程或结果呈现的内容。
- 只表达状态流转、权限职责、记录追踪或数据治理的内容。
- 不能稳定支撑运筹问题内核的数据结构说明。

流程机制中只有稳定表达优化需求或约束的规则才抽取。判断依据是它是否限定了可行域、资源流动、对象匹配、数量边界、时间边界、优先级、条件作用或例外作用；单纯流程顺序、操作动作、状态流转或系统交互不得抽取为约束。

### 2. 标准化运筹本体

基于 `or_signal_inventory` 标准化对象、目标、约束和数据证据，并重新使用 `simulation_schema` 做结构核对，输出 `ontology_mapping` 与 `or_ontology`。

阶段 2 不重新大范围筛读原始业务输入，不引入上游信号中没有出现的核心业务对象、目标或约束。必须补充弱推理时，只能补高度确定的信息，并显式写出 `is_inferred` 与 `inference_basis`。`simulation_schema` 在这一阶段的职责是核对和完整转录表结构，而不是重新发明业务语义。

阶段 2 必须先校验时间粒度是否已被明确识别。若只能确认存在时间窗口、日期字段或宽泛业务周期，不能把粒度留给 `or-time-discretization` 或下游代码生成阶段再确定；应抛出澄清问题，并在 `open_questions` 标记该问题对时间维度、决策粒度和约束匹配的影响。

## 标准化规则

### 运筹内核

- `business_ontology` 不是“目标函数 + 约束集合”的形式化模型，不能机械转写。
- 先判断内容是否属于运筹问题内核，再做标准化。
- 数据结构、流程机制和方案管理逻辑只有在稳定支撑资源、节点、连接、目标或约束的抽象语义时才保留为证据。
- 不确定内容写入 `open_questions`，不要用猜测补成建模事实。

### 时间粒度

- 时间粒度是 `problem_frame` 的核心口径，不是字段类型，也不是单纯的时间窗口存在性。
- 最终 `time_granularity` 必须是单一、明确、可执行的规划/匹配粒度。若输入明确存在多层时间口径，必须说明主优化粒度以及其他粒度与主粒度的关系；无法区分主次时必须抛出问题。
- 只有业务口径、计划/排程/匹配/结算周期、约束生效周期或明确的数据统计周期能作为时间粒度依据。`date`/`datetime` 字段、开始/结束时间字段、时间窗口重叠约束本身不足以推断日度、周度或月度。
- 不得把“时间窗口”“按交付时间”“后续离散化确认”“日度/月度待确认”等含混表述写入最终明确粒度。
- 若时间粒度缺失、无法确定或证据冲突，必须抛出阻断性问题。问题应直接询问本次优化/匹配按哪个时间粒度运行，并说明会影响 `time_dimension`、时间离散化配置、决策变量时间维度和时间约束匹配。
- 下游 `or-time-discretization` 只消费已经明确的时间粒度，不负责替 `business-to-or-ontology` 决定粒度。

### 对象

对象必须优先落入元模型既有类型：

- `resource`：在网络中被供给、运输、消耗、存储或转化的真实流动对象。
- `node`：承载资源产生、消耗、中转、处理或存储的对象。
- `edge`：承载节点之间资源转移或映射连接的对象。

识别顺序：

1. 先识别真正流动的 `resource`。
2. 再识别承载资源流动的 `node`。
3. 最后识别承载流动或映射关系的 `edge`。

不要把管理性对象、规则性对象、结果性对象、组织性对象、流程性对象或记录性对象直接当成 `resource`。若对象只是资源供给或需求的记录载体，应继续判断其背后的节点角色。

候选对象必须同时满足：

- 与当前场景目标、约束、流动对象、节点连接或关键数据路径直接相关。
- 能独立承载对象语义或连接语义。

仅提供治理性、追踪性、状态性、通用元数据或无直接业务作用的表，不进入 `candidate_entities`。

### 节点

- 向网络输出资源的一侧，优先识别为 `supply_node`。
- 从网络接收并消耗资源的一侧，优先识别为 `demand_node`。
- 只承担流入流出、不承担存储或转化功能的中转位置，优先识别为 `passthrough_node`。
- 对资源执行加工、变换、处理等作用的对象，优先识别为 `processor_node`。
- 对资源执行库存持有、储存释放、时间平移等作用的对象，优先识别为 `storage_node`。

若输入明确存在供给、需求、传输或匹配语义，结果应优先形成 `resource + node + edge` 的网络表达。

### 线路

- 存在承载资源在节点间发生实际转移的通道语义时，优先识别为 `transport`。
- 仅表达节点或对象之间的非转移型连接语义，且不承载资源实际转移时，优先识别为 `link`。
- 不要把所有节点关系默认识别成 `transport`。

稳定承载连接语义、且不能稳定描述任一端对象自身属性的数据结构，默认先按 `link` 候选处理。若它稳定表达对象间非转移型连接关系，即使暂时不能精确落到 `edge` 子类，也必须作为独立候选对象进入 `candidate_entities`。

### 数据证据

schema 只提供数据承载与粒度证据，不替代业务语义。

这里的 schema 默认指 `simulation_schema`。`business_ontology` 中出现的 schema 片段、字段示例、属性列举、对象属性说明一律忽略，不参与 `attached` 对象 `table_schema` 的直接来源判断。

对关注的非 `resource` 对象，必须显式说明 schema 绑定状态：

- `attached`：对象直接绑定到主表；必须按 `simulation_schema` 中原表逐字段完整转录 `table_schema`，保留字段顺序、原始字段类型文本、主键、可稳定识别的唯一键和外键信息。
- `referenced`：只能稳定确认来源表；填写 `supporting_tables`，必要时补 `supporting_fields`。
- `missing`：无法稳定确认数据支撑；写入 `open_questions`。

若某个 `node` 同时受实体主表和关系表支撑，优先将描述对象自身属性的实体主表绑定为 `table_schema`；关系表保留为连接证据。

若某个 `edge` 同时受实体主表和关系表支撑，优先将直接定义关系语义及字段来源的关系表绑定为 `table_schema`；实体主表只作补充证据。

不得编造表 schema。不得用 `business_ontology` 内嵌 schema 去补齐、删减、改名、改序、改类型或覆盖 `simulation_schema` 原表字段。若 `attached` 对象输出的 `table_schema.fields` 少于原始主表字段数，明显只是 `supporting_fields` 的展开结果，混入仅存在于 `business_ontology` 内嵌 schema 而不在 `simulation_schema` 中的字段，或把原始数据库类型擅自归一化为 `string`、`float`、`boolean` 等抽象类型，视为失败。

若 `simulation_schema` 中能稳定识别 `UNIQUE KEY` 或唯一索引，必须写入 `table_schema.unique_keys`，并显式列出唯一键对应的字段组合；不要只保留“有唯一键”这一事实。

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
- 若一段原文包含多条彼此解耦的约束，应拆成多条。
- 只要识别出约束语义，就先抽取为约束；确定性通过 `confidence` 表达，不用省略代替判断。
- `confidence` 只能是 `high`、`medium`、`low`。
- 不补决策变量、bound 推导、slack 设计、线性化策略或公式实现。

约束来源：

- `business_ontology` 中明确限定可行域、边界、优先级、条件作用、例外作用或业务口径的规则。
- `simulation_schema` 中语义明确、作用对象稳定、能够表达数量边界、状态边界、关系边界、时间边界或条件作用的字段。

候选约束进入阶段 2 后，要么落入正式约束，要么在 `open_questions` 中说明无法稳定标准化的原因；不得静默丢失。

若某个 schema 约束字段的作用对象已明确是 `node` 或 `edge`，且字段名或字段说明明确表达约束语义，必须进入 `candidate_constraints`，并在阶段 2 落入对应对象的正式约束，除非存在明确冲突证据。

### 推理与问题

- 只允许高度确定且有明确依据的弱推理。
- 所有推理项都要显式标记 `is_inferred`，并填写 `inference_basis`。
- `open_questions` 只暴露已经出现但信息不足或语义不稳定的疑点。
- `open_questions` 至少包含 `question`，可提供时补充 `evidence_ids` 与 `impact`。

## 质量检查

提交前检查：

1. 是否引入了用户未提供且无充分依据的新概念。
2. 是否把目标误写成约束，或把约束误写成目标。
3. 是否遗漏、合并错或拆坏约束。
4. 是否为了“像模型”而写出过深公式。
5. 是否把管理性对象、记录载体或流程动作误写成 `resource`、`node` 或 `edge`。
6. 是否遗漏明显存在的 `supply_node`、`demand_node` 或 `edge`。
7. 是否混淆 `resource`、`node` 与 `edge` 的语义层级。
8. `attached` 对象的 `table_schema` 是否完整转录原始主表。
9. 上游候选目标和候选约束是否都已落入正式结果或 `open_questions`。
10. 所有 schema 输出是否满足对应 JSON Schema。
11. 是否错误地让 `business_ontology` 内嵌 schema 干扰了 `simulation_schema` 的字段集合、字段顺序、主键、唯一键或表选择。
12. `problem_frame.time_granularity` 是否是明确粒度；若缺失、含混或冲突，是否已抛出阻断性问题，而不是留给下游阶段确认。
