# 规格驱动开发（SDD）视角下的 Skills 体系分析

> 分析对象：当前仓库 `skills/` 下的 6 个 skill（or-workflow-guide、ontology-modeling、brd-generation、app-design、code-generation、code-verification）。
> 分析视角：**规格驱动开发（SDD, Spec-Driven Development）**，对应工作流「需求分析 → BRD → 详细设计 → 代码开发」。
> 与既有文档的关系：本文是《skills-optimization-plan.md》之后的**第二轮纵深分析**。前者解决了「阶段有没有 skill 覆盖」（补齐 code-generation / code-verification / 映射规则 / 进度账本，多数已落地）；本文聚焦「这些 skill 是否真正构成一条规格驱动、可追溯、可闭环的流水线」，即「够不够深」，而非「有没有」。
>
> **本版（v2）相对 v1 的修订**（便于校对）：
> - **§0 重写**：澄清「SDD」是歧义缩写，标明本项目实为「需求层 spec-driven + 设计/代码层 model-driven 的混合」；声明下文「评估清单」为本文构造，并标注每条的软件工程出处（非引用某个 SDD 标准）。
> - **§1**：映射表补入业界参考里的 **Tasks（任务分解）阶段**，指出项目把该阶段隐藏进了 code-generation。
> - **§3**：新增「问题 1：Tasks 阶段被隐藏」，问题按主题重新排列。
> - **§7 新增**：参考资料附录（含 URL）。

---

## 0. 术语校准与本文立场

### 0.1 「SDD」是歧义缩写

「SDD」**不是一个有单一权威定义的标准术语**（没有 ISO/IEEE/OMG 标准叫 SDD）。它是工业界/社区术语，同一缩写在不同语境指三种不同的东西：

| 缩写所指 | 全称 | 是否有正式标准 | 核心思想 |
|---|---|---|---|
| **Spec-Driven Development** | 规格驱动开发 | 无正式标准；AI 时代/Claude Code 生态有事实参考 | 规格是唯一事实源，代码是衍生产物；**先 spec 后 code** |
| **Schema-Driven Development** | 模式驱动开发 | 无正式标准；OpenAPI / GraphQL / Prisma 实践 | 数据 schema / API 契约为源头，驱动代码生成 |
| **Model-Driven Development (MDD/MDA)** | 模型驱动开发 | **有**：OMG 的 MDA（2001）、MOF、UML、XMI | 可视化/形式化模型为源头，逐层变换到代码 |

在 **Claude Code / AI agent 语境**，「SDD」几乎都指 **Spec-Driven Development**。其事实上的参考四阶段（以社区项目 `claude-code-spec-workflow` 为代表）为：

```
Requirements → Design → Tasks → Implementation
（需求规格）  （设计）  （任务分解）（实现）
```

> 因此，下文凡称「SDD」，特指 **Spec-Driven Development**；凡称「Model-Driven」，特指 MDD/MDA 范式。

### 0.2 本项目的真实定位：spec-driven 与 model-driven 的混合

本项目的设计意图被表述为「SDD 驱动开发的四阶段」。但按其实际机制分层看，它是一条**混合范式**流水线：

| 流水线层 | 驱动范式 | 依据 |
|---|---|---|
| 需求 / BRD 层 | **Spec-driven**（自然语言规格驱动） | `ontology-modeling` 产出 `brd.md`（Markdown）、`biz_logic` 记录对话原文 |
| 设计 / 代码层 | **Model-driven**（本体模型变换驱动） | 以 `ontology_schema.json`（对象-行为-规则模型）为源头，经 `ontology-mapping-rules.md` 的映射规则**变换**出表结构、接口、代码骨架 |

也就是说：**需求层是 spec-driven，设计/代码层是 model-driven**。这一区分很重要——它决定了本文评估清单里哪些条目适用哪一层。v1 版把整条流水线笼统称为「SDD」并套用同一组判据，抹平了这个差异，本版予以修正。

### 0.3 本文的「评估清单」是构造的，不是引用标准

下文 §2 的七条「规格驱动成熟度清单」**不是某个 SDD 规范里的条款**，而是本文综合多个成熟软件工程领域提炼的检查清单。每条都标注出处（§2 表中「理论出处」列），它们本身是这些领域的常识，但**组合在一起作为「SDD 评估框架」是本文的构造**。请据此理解其权重：它是一份可辩护的评估视角，不是合规审计依据。

---

## 1. 现状：四阶段与 skill 的映射

业界参考四阶段（含 Tasks）与本项目 skill 的对照：

| 业界 SDD 阶段 | 本项目对应 | 阶段产物 | 落地状态 |
|---|---|---|---|
| ① Requirements（需求规格） | ontology-modeling（需求分析 + BRD 合并为双产出） | `docs/ontology_schema.json`（结构化）+ `docs/brd.md` | ⚠️ 需求分析与 BRD 合并；另有重复入口 `brd-generation` |
| ② Design（详细设计） | app-design | `docs/app-design.md` + `docs/db-schema.md`（自由 Markdown） | ✅ 有，但产物为非结构化 |
| ③ **Tasks（任务分解）** | **被隐藏进 code-generation 的「骨架阶段」** | 无独立产物 | ❌ **无独立阶段、无独立门禁** |
| ④ Implementation（实现） | code-generation（骨架+填充）+ code-verification | Spring Boot 代码 + 验证报告 | ✅ 有 |

**两个结构性的「定义—实现不一致」**：

1. **Tasks 阶段缺失**：业界 SDD 在设计与实现之间设有独立的「任务分解」阶段（对应 Superpowers 的 `writing-plans`，产出精确到文件/签名/任务粒度的实现计划）。本项目把这一步塞进了 code-generation 的「步骤1 骨架优先」内部，未上升为独立阶段、未设独立门禁、未产出独立的实现计划文档。
2. **需求层阶段口径不一**：项目对外表述把「需求分析」和「BRD」列为两个独立阶段，但实现里二者被合并为 `ontology-modeling` 的双产出；同时还存在一个功能重叠的独立 `brd-generation` skill。

**一句话现状**：四个阶段都有 skill 覆盖，流水线骨架已搭起来；但 Tasks 阶段被隐藏、需求层阶段口径自相矛盾，且从第①阶段起，结构化 JSON 降级为自由 Markdown。

---

## 2. 规格驱动成熟度评估清单（本文构造）

> 声明：本清单为本文构造的评估视角，非 SDD 标准条款。「理论出处」列给出每条对应的成熟软件工程领域，供校验其合理性。

| # | 评估条目 | 含义 | 理论出处 |
|---|---|---|---|
| C1 | **单一权威源** | 每个制品有唯一权威定义，下游不得绕过、不得另起炉灶 | 软件配置管理（SCM）；Single Source of Truth |
| C2 | **可机器消费** | 规格足够结构化，能被下游**确定性**消费，而非靠 LLM「读 Markdown 自由发挥」 | 契约优先设计（Contract-First）；MDA 的模型可变换性 |
| C3 | **代码级可追溯** | 需求→设计→代码的每个元素可**双向确定性**追溯（代码带标注，而非仅文档写映射表） | 需求可追溯性（Requirements Traceability，IEEE 830 / RTM） |
| C4 | **阶段门禁（准出）** | 每阶段有明确的输出契约检查，产物不达标不准进入下游 | 验证与确认（V&V）；阶段门（Stage-Gate） |
| C5 | **变更传播** | 上游规格变更时，受影响的下游制品能被识别并同步重生成，不漂移 | 变更影响分析（Change Impact Analysis）；CMMI 配置管理 |
| C6 | **反馈闭环** | 验证发现的缺陷能回流为规格修订，规格与实现不长期背离 | 戴明环 PDCA；缺陷回流（Defect-to-Source） |
| C7 | **运行时一致** | 跨运行时 / 跨会话的状态、产物路径、触发机制统一，不出现多套并行权威 | 分布式系统单一事实源；一致性约束 |

下文问题诊断会标注每条违反了哪些清单条目。

---

## 3. 问题诊断

### 问题 1：Tasks（任务分解）阶段被隐藏进 code-generation，四阶段不完整 〖违反 C4〗

**现象**
- 业界 SDD 在 Design 与 Implementation 之间有独立的 Tasks 阶段：把设计拆解为精确到文件/签名/任务粒度的实现计划，作为「设计可行性」的预演缓冲层。
- 本项目把这一步塞进 code-generation 的「步骤1 骨架优先」——它确实做了「确定所有类签名/方法签名/import」的事（接近 task 分解），但是：
  - 没有产出一份**独立的实现计划文档**（task 清单）；
  - 没有作为**独立门禁**（骨架写完直接进填充，不暂停供用户审查）；
  - 把「设计可行性验证」与「代码生成」**耦合**——若设计本身不可行/自相矛盾，要等到生成骨架时才暴露，而非在设计准出时就暴露。

**根因（评估条目）**
- 违反 C4：缺少独立的「任务分解准出门禁」。设计与实现之间少了一个验证缓冲层。

**影响**
- code-generation 同时承担「task 分解 + 骨架生成 + 并行填充」多重职责，违反单一职责，出错时难定位是设计问题还是实现问题。
- 用户无法在「写代码前」审查实现计划——只有设计文档可审，代码骨架写完才可见，发现偏差时返工成本已沉没。

**证据**
- 业界参考四阶段：Requirements → Design → **Tasks** → Implementation（§0.1）。
- `code-generation/SKILL.md` 步骤 1「生成全局骨架」、步骤 2「并行填充」：task 分解与代码生成未分离，骨架阶段「完成后直接进入阶段 2，不单独暂停」。

---

### 问题 2：设计产物从结构化降级为自由 Markdown，可机器消费性断裂 〖违反 C2〗

**现象**
- `ontology_schema.json` 严格遵循 `Ontology` 接口，是结构化 JSON（✅ 好）。
- 但从 app-design 开始，`app-design.md`、`db-schema.md`、`brd.md` 全是自由 Markdown。
- code-generation 的「骨架阶段」要从 `app-design.md` 的**三张 Markdown 映射表**（行为→接口、规则→代码、SOP→Biz）里「读懂」要生成什么类、什么签名——这是 LLM 读表格自由推导，**不可复现**。

**根因（评估条目）**
- 违反 C2：model-driven 范式要求设计层产物可被确定性变换（MDA 的核心是「模型 → 模型 → 代码」的可机械执行变换）。Markdown 表格不满足。

**影响**
- 「骨架优先」声称解决子代理 import 冲突，但骨架本身由非结构化文档推导，**第一层不确定性已注入**，后续所有「确定性」都建立在它之上。

**证据**
- `app-design/SKILL.md`：要求设计文档「必须包含三张映射表」，但只约束「有没有」，未约束「是否机器可解析」。
- `code-generation/SKILL.md` 步骤 1：直接从 `docs/app-design.md` 推导所有类签名，无中间结构化契约。

---

### 问题 3：DDL / 接口埋在 Markdown 里，未作为一等契约 〖违反 C2、C3〗

**现象**
- `db-schema.md` 把 DDL 写在 Markdown 代码块里；接口设计是 Markdown 表格。
- 没有**可直接执行的 `.sql`**，没有**可被 swagger 校验的 OpenAPI spec**。

**根因（评估条目）**
- 违反 C2：DDL 和接口本应是 contract-first 的一等制品（可执行、可校验、可生成 client），却降级为「文档片段」。
- 违反 C3：code-verification 无法做「DDL 是否与 db-schema 一致」「接口是否与 OpenAPI 一致」的**确定性校验**，只能靠模型读文档对比代码。

**影响**
- code-generation 多一层「从 Markdown 提取 DDL/接口」的不确定解析。
- 验证环节失去确定性基准。

**证据**
- `app-design/SKILL.md`：DDL 写入 `docs/db-schema.md`（Markdown），接口为 Markdown 表格，无独立 `.sql` / `.yaml` 制品。

---

### 问题 4：可追溯性是「文档级声称」而非「代码级强制」 〖违反 C3〗

**现象**
- ontology-modeling 里对象有 `code`、规则有 `code`（✅ 有 ID 体系）；app-design 要求写「规则→代码位置映射表」。
- **但生成的代码里没有任何机制把类/方法与上游 ID 绑定**——无注释标注（如 `@ontology:object=GasContract`、`@brd:req=FR-003`），无清单文件。

**根因（评估条目）**
- 违反 C3：需求可追溯性（RTM）要求的是**代码 ↔ 规格的双向确定性链接**，而非「文档里写了映射」。追溯停留在文档级，没落到代码级。

**影响（关键）**
- code-verification 步骤 3「功能完整性对照」只能「**按方法名和注释匹配**」BRD 功能点。改名即失配、漏注释即误判为缺失。验证的置信度被追溯机制的脆弱性封顶。
- 一旦报「❌ 未找到对应实现」，无法区分「真没生成」还是「生成了但名字对不上」，需人工逐个排查。

**证据**
- `code-verification/SKILL.md` 步骤 3：「扫描生成的 Controller/BizService 代码，**按方法名和注释匹配**功能点」。
- `code-generation/SKILL.md`：子代理任务模板无「在生成方法上标注来源 ID」的要求。

---

### 问题 5：阶段门禁（准出）不完整 —— 只记「做没做」，不记「达没达标」 〖违反 C4〗

**现象**
- or-workflow-guide 的进度账本（`docs/workflow-progress.md`）只记 `complete / in progress / pending`，**不记产物质量是否达标**。
- app-design 有强准出门禁（HARD-GATE + 规范自审 7 项 + 用户审查），是六个 skill 里门禁最完整的 ✅。
- 但 **app-design → code-generation 之间无输入契约检查**：code-generation 明确「不读 brd / 不读 ontology_schema」（已由 app-design 消化）。若 app-design 漏掉某条规则的映射表，该信息在 code-generation 阶段**永久丢失、无法补救**。

**根因（评估条目）**
- 违反 C4：每阶段应有输出契约的自动校验。当前仅 app-design 自审，且自审结果不传递给下游作准入依据。

**影响**
- 「app-design 消化业务信息」这一前提，要求 app-design 准出门禁**必须**校验「三张映射表完整覆盖 ontology 全部对象/行为/规则」。当前自审第 7 项「映射完整性检查」只是文字要求，无可执行校验（如：对照 `ontology_schema.json` 的 objects/rules 数量核对映射表逐项覆盖）。
- 门禁一旦失效，错误沿「单向不回头」的流水线一路放大到代码。

**证据**
- `or-workflow-guide/SKILL.md` 进度账本格式：仅 `阶段: complete (步骤, 产物)`，无质量字段。
- `code-generation/SKILL.md` 输入表：「**不读取** ontology_schema.json 和 brd.md」——单向依赖，无回溯补救通道。

---

### 问题 6：变更传播缺失 —— 上游改一处，下游不自动跟着改，迭代必然漂移 〖违反 C5〗

**现象**
- 真实开发中，用户在代码阶段说「给合同加个 `priority` 字段」或「改一条利润计算规则」，会发生什么？
  - ontology-modeling 支持读已有 schema 增量更新（✅）。
  - 但 app-design **没有「上游变更影响分析」机制**——无 skill 负责「schema 加一个字段 → 哪些设计章节、哪些表、哪些接口要跟着改」。
  - code-generation 的「增量开发」只解决**代码文件冲突**（不覆盖已有文件），**不解决规格变更的传播**。

**根因（评估条目）**
- 违反 C5：SDD/MDD 的灵魂是规格驱动 + 变更可控传播（变更影响分析）。当前是一条**一次性线性流水线**，无「受影响产物识别 + 选择性重生成」能力。

**影响**
- 第二轮迭代起，schema / brd / app-design / 代码的同步全靠人脑和手工——这正是规格驱动要消灭的「漂移」。进度账本不记「代码对应的规格版本」，无法判断代码是否落后于规格。

**证据**
- `ontology-modeling/SKILL.md`：支持增量合并已有文件，但「覆盖写完整内容」，不产出「相对上一版的变更集」。
- `code-generation/SKILL.md` 步骤 0：增量模式只判断「文件冲突」，无「规格 diff → 代码 diff」映射。

---

### 问题 7：反馈闭环不闭合 —— 验证只改代码，不回流到规格 〖违反 C6〗

**现象**
- code-verification 发现 Important 问题（如「利润计算缺失：BRD 有需求、代码没实现」）时，处理方式是「报告给用户，由用户决定」。✅ 分级处理本身合理。
- 但**无机制把验证缺陷回流为规格修订**。上面的「利润计算缺失」可能源于：(a) app-design 漏写规则→代码映射（应改设计）；(b) code-generation 漏生成（应改代码）。当前流程不区分根因，也不更新对应规格。

**根因（评估条目）**
- 违反 C6：验证应是 SDD 的**反馈起点**（缺陷 → 定位根因 → 修订对应层规格 → 重新生成），而非流水线**终点**（出报告即结束）。

**影响**
- 随迭代，规格与实现裂缝只增不减，brd/app-design 沦为「过时文档」，失去规格驱动的权威性。

**证据**
- `code-verification/SKILL.md` 步骤 5「输出验证报告」是终点；「待处理事项」交用户，无「回流修订规格」步骤。

---

### 问题 8：BRD 阶段双入口，且与「四阶段定义」自相矛盾 〖违反 C1〗

**现象**
- 项目对外把「需求分析」「BRD」列为两个独立阶段；实现里二者合并为 `ontology-modeling` 的双产出（schema + brd 边建模边一起出）。
- 同时还存在一个独立的 `brd-generation` skill（只产 BRD 不产 schema），与 ontology-modeling 功能重叠。

**根因（评估条目）**
- 违反 C1（单一权威源）：BRD 阶段有两个入口、两套模板、两套 examples。
- 且与 §1 指出的「四阶段定义—实现不一致」叠加：口径上需求分析/BRD 是两阶段，实现上合并为一个 skill 的双产出。

**影响**
- 用户可能选错入口（走 brd-generation 产出的 brd 无 schema，下游 app-design 缺本体图谱输入）。
- 两份 BRD 模板（`brd-generation/references/brd-template.md` 与 `ontology-modeling/references/brd-template.md`）**已存在结构差异**（章节编号方式、是否有 RACI 矩阵、是否有数据生命周期、是否有变更记录字段均不同），产出格式不统一，下游 code-verification「从 §4 提取功能点」会因模板差异而不稳定。

**证据**
- `brd-generation/SKILL.md` 与 `ontology-modeling/SKILL.md` 都产出 `docs/brd.md`，职责重叠。
- 两份 `brd-template.md` 差异已由附属文件核对确认。
- （注：与旧方案「优化点 6（P3 未处理）」重叠，但旧方案仅讨论「合并 or 分层」，本文从单一权威源给出更明确结论——见建议 C2。）

---

### 问题 9：跨运行时的二元性 —— skill 既挂 Claude Code 又挂 OpenAI agent，状态权威分裂 〖违反 C7〗

**现象**
- `or-workflow-guide/agents/openai.yaml` 表明这套 skill 实际跨两个运行时：Claude Code 的 skill 机制 + OpenAI agent 配置。
- `ontology-modeling/references/script/finish_ontology.py` 在建模完成后**回调本地代理服务器**发完成通知。
- 于是存在**两套并行状态**：Claude Code 侧的 `docs/workflow-progress.md` 进度账本 vs. OpenAI agent / 本地代理侧的完成通知机制。

**根因（评估条目）**
- 违反 C7：规格驱动依赖统一的运行时契约（进度状态、产物路径、阶段触发的唯一权威）。双运行时下，若两侧对「当前阶段、产物位置、完成判定」理解不一致，可靠性从根上动摇。

**影响**
- 跨运行时恢复时，可能账本说「代码生成 in progress」但代理侧已收到「建模完成」通知，状态分裂。

**证据**
- `or-workflow-guide/agents/openai.yaml`（OpenAI agent 配置）、`ontology-modeling/references/script/finish_ontology.py`（回调本地代理）。

---

## 4. 改进建议

建议按三波主题聚类（A/B/C），每条标注所解问题。

### 主题 A — 阶段完整性与结构化契约（第一波）

**建议 A1：把 Tasks（任务分解）补为独立阶段/独立门禁** 〖解问题 1〗〖P0〗
- 在 app-design 与 code-generation 之间显式引入「实现计划」环节：把 code-generation 的「骨架阶段」拆出来，产出一份独立的 `docs/impl-plan.md`（或结构化的 `impl-plan.yaml`），列出所有要生成的文件、类签名、方法签名、分组与依赖顺序。
- 该计划作为独立门禁供用户审查后再进入「填充实现」。这样设计与实现之间有了缓冲层，设计可行性在写业务代码前就被验证。

**建议 A2：设计产物升级为结构化契约 + DDL/OpenAPI 一等公民** 〖解问题 2、3〗〖P0〗
- 新增 `docs/contracts/`：
  - `db-schema.sql` —— 可直接 `mysql <` 执行的 DDL（取代 Markdown 内嵌 DDL 为权威源）。
  - `app-contract.yaml` —— 结构化接口/映射契约：`objects[]`（PO/VO/DTO 字段）、`endpoints[]`（由行为→接口映射确定性生成）、`rules[]`（规则→层级+方法名）、`sops[]`（SOP→Biz 方法+调用序列）。
- code-generation 的骨架阶段改为**直接消费 `app-contract.yaml`**（确定性解析），Markdown 退化为「契约的人类可读视图」。
- 这条是整条流水线升级为 model-driven 的杠杆点。

### 主题 B — 可追溯与门禁闭环（第二波）

**建议 B1：代码带「规格出处」标注 + traceability.json** 〖解问题 4〗〖P0〗
- code-generation 子代理模板强制：每个 Controller/Biz/Service 方法在 Javadoc 标注来源 ID：
  ```java
  /** @ontology object=GasContract behavior=create  @brd req=FR-003  @rule profit_calc */
  ```
- 生成 `docs/traceability.json`：全部 `本体 code / BRD 功能点 ID / 规则 code → 代码文件:方法` 映射。
- code-verification「功能完整性对照」改为**读 `traceability.json` 做确定性匹配**，不再靠模糊匹配。

**建议 B2：每阶段加准出门禁，结果写进进度账本** 〖解问题 5〗〖P1〗
- 进度账本扩展质量字段：
  ```
  本体建模: complete (gate=passed, objects=8, rules=5, 产物=...)
  应用设计: complete (gate=passed, 映射覆盖率=对象8/8 行为40/40 规则5/5, 产物=...)
  代码生成: in progress (gate=—, 已生成对象=6/8)
  ```
- 关键新增 **app-design 可执行准出门禁**：对照 `ontology_schema.json` 的 objects/behaviors/rules 总数，核对 `app-contract.yaml` 逐项覆盖。覆盖率不达 100% 不放行——因 code-generation 禁止回头看业务原文，这是最后补救机会。

**建议 B3：验证缺陷根因回流规格** 〖解问题 7〗〖P1〗
- code-verification 对每个 Important 缺陷做根因定位：设计层缺失（→ 触发 app-design 局部修订）还是实现层缺失（→ 触发 code-generation 局部重生成）。
- 待处理事项区分 `[spec-gap]`（改规格）与 `[impl-gap]`（改代码），对接建议 C1 的变更传播。

### 主题 C — 迭代与治理（第三波）

**建议 C1：变更影响分析，支持迭代而非一次性流水线** 〖解问题 6〗〖P1〗
- 在 or-workflow-guide 新增「规格变更处理」分支：上游产物变化时 → 计算 diff → 生成「受影响产物清单」→ 仅重生成受影响部分。
- 进度账本记录「代码对应的规格版本（hash/序号）」，使「代码是否落后于规格」可判定。

**建议 C2：合并 BRD 单一入口，统一模板** 〖解问题 8〗〖P2〗
- 结论：**合并 brd-generation 进 ontology-modeling**，删除独立 skill 及重复模板（单一权威源）。
- 在 ontology-modeling 内增加显式「需求基线」子环节：建模完成后、产 BRD 前单独做需求收敛与确认，让 BRD 成为有独立质量门禁的阶段产物。
- 统一为单一 `brd-template.md`。

**建议 C3：统一运行时与状态权威** 〖解问题 9〗〖P2〗
- 选定 `docs/workflow-progress.md` 为跨运行时唯一状态真相源；`finish_ontology.py` 的完成通知改为**写入/更新同一账本**，而非另起通知。
- 在 skill 文档写明运行时假设（主运行时、另一运行时如何兼容），消除「既像 Claude Code skill 又像 OpenAI agent」的歧义。

---

## 5. 改进路线图

| 波次 | 建议 | 价值 | 说明 |
|------|------|------|------|
| **第一波（契约化 + 补阶段）** | A1 + A2 | ★★★★ | 补 Tasks 独立门禁 + 引入 `app-contract.yaml`/DDL 一等公民。这是把流水线从「文档驱动」升级为「model-driven」的杠杆点。 |
| **第二波（追溯 + 门禁 + 闭环）** | B1 + B2 + B3 | ★★★ | 代码标注 + traceability.json + 阶段准出门禁（含 app-design 覆盖率校验）+ 验证根因回流。把单向流水线变成带确定性追溯与质检反馈。 |
| **第三波（迭代治理）** | C1 + C2 + C3 | ★★ | 变更传播（支持多轮迭代）+ BRD 单一入口 + 运行时统一。偏治理与长期可维护性。 |

> 第一波是关键：问题 1（Tasks 缺失）、问题 2/3（规格不可机器消费、契约非一等公民）是当前体系最根本的短板。解决后，第二波的门禁与追溯才有确定性基础可依附。

---

## 6. 与既有优化方案（skills-optimization-plan.md）的关系

| 本文问题 | 旧方案对应 | 关系 |
|---------|-----------|------|
| 问题 8（BRD 双入口） | 旧优化点 6（P3 未处理） | **承接**：旧方案仅讨论合并 or 分层，本文从单一权威源给出明确结论（合并）。 |
| 问题 4（追溯） | 旧优化点 5（映射规则） | **深化**：旧方案要求「设计文档写映射表」，本文要求「映射落到代码标注 + traceability.json，让验证确定性化」。 |
| 问题 5（门禁） | 旧优化点（app-design HARD-GATE） | **扩展**：旧方案只给 app-design 加门禁，本文要求每阶段都有准出门禁并写进账本。 |
| 问题 1、2、3、6、7、9 | — | **新增**：Tasks 阶段缺失、规格可消费性、契约一等公民、变更传播、反馈闭环、运行时一致性，均为旧方案未覆盖的纵深维度。 |

**总结**：旧方案让流水线「补齐了阶段」（从 3 个 skill 到 6 个，骨架完整）；本文指出要成为**真正的规格驱动**，还需补回 Tasks 阶段、把「自由 Markdown 规格」升级为「结构化可校验契约」、把「文档级映射」升级为「代码级可追溯」、把「一次性线性流程」升级为「带门禁、能变更传播、有反馈闭环」的迭代流程。前者解决「有没有」，后者解决「是不是规格驱动」。

---

## 7. 参考资料

### 7.1 SDD 术语与定义
- [Pimzino/claude-code-spec-workflow (GitHub)](https://github.com/Pimzino/claude-code-spec-workflow) — Claude Code 生态 SDD 事实参考，定义 Requirements → Design → Tasks → Implementation 四阶段。
- [Itential — From Vibes to Specs: The Shift to Spec-Driven Development](https://www.itential.com/resource/blog/vibes-to-specs-development/) — SDD 在更高层级定义完整 API 契约 / schema / 系统接口；"Specifications are the source of truth; code is the output"。
- [Medium — SDD: Schema Driven Development (Alex Hint)](https://medium.com/@hintology/sdd-schema-driven-development-f1d232d73ea6) — 佐证「SDD」缩写在 Schema-Driven 语境的另一种用法（缩写歧义证据）。

### 7.2 模型驱动开发（对照范式）
- [OMG — Model Driven Architecture (MDA)](https://www.omg.org/mda/) — MDD/MDA 正式标准出处（2001）；MOF / UML / XMI 规范。
- [Mendix — 模型驱动开发：低代码的基础](https://www.mendix.com/zh-CN/blog/low-code-principle-1-model-driven-development/) — MDD 范式的工业实践说明。

### 7.3 评估清单各条目的理论出处（标准 / 方法论）
- **IEEE Std 830-1998** — *IEEE Recommended Practice for Software Requirements Specifications*；需求规格与可追溯性（出处对应 C3）。标准文档可在 IEEE Xplore 检索。
- **CMMI** — Configuration Management / Change Impact Analysis PA（出处对应 C5）。
- **Stage-Gate** — Cooper, R. G. 的产品开发阶段门方法（出处对应 C4）。
- **PDCA（戴明环）** — Deming, W. E.；持续改进与反馈闭环（出处对应 C6）。
- **Contract-First Design** — Web 服务/API 设计惯例（出处对应 C2）。

### 7.4 项目内部对照
- 《skills-optimization-plan.md》（本仓库 `docs/`）— 第一轮优化方案，本文为其纵深延续；其中引用的 **Superpowers** skill 体系（`brainstorming` → `writing-plans` → `executing-plans`）是 Tasks 阶段对照系。
