# 企业 Skills 优化方案

> 基于 Superpowers 技能体系对比分析，针对当前企业 Skills（or-workflow-guide、ontology-modeling、app-design、brd-generation）的 7 个优化方向。
>
> 目标：**本体建模 → 设计 → 生成可运行代码，产出少 bug 应用**

---

## 当前架构

```
用户请求 → or-workflow-guide（路由器）
              ↓
        ontology-modeling（本体建模 + BRD）
              ↓
        app-design（应用设计）
              ↓
        （实现阶段 ← 目前无 skill 覆盖）
```

## 优化后架构

```
用户请求
   ↓
or-workflow-guide（路由器 + 状态管理）
   ↓ 读取 docs/workflow-state.md
   ↓
ontology-modeling（增强铁律 + 防合理化）
   ↓ 产出：ontology_schema.json + brd.md
   ↓ 写入 workflow-state.md
   ↓
app-design（增强行为→接口 + 规则→代码映射）
   ↓ 产出：app-design.md + db-schema.md
   ↓ 写入 workflow-state.md
   ↓
code-generation（新增：精确实现计划 + 代码生成）
   ↓ 产出：可运行的 Spring Boot 项目代码
   ↓ 每个任务完成后触发 code-review-checkpoint
   ↓
code-verification（新增：编译 + 测试 + BRD 对照）
   ↓ 产出：验证报告
   ↓
finishing-a-development-branch（完成交付）
```

---

## 优化点 1：设计到实现之间断崖——缺 code-generation skill

### 问题描述

`app-design` 的终点是"设计文档完成，等待用户决定是否进入实现"，但**没有任何 skill 覆盖如何从设计文档到代码的路径**。这是当前最大的缺口——目标是"产出可运行应用"，但流程在设计文档就断了。

### Superpowers 参考

- `brainstorming` → `writing-plans` → `executing-plans` / `subagent-driven-development`
- `writing-plans` 将设计拆解为**精确到代码级别**的任务（含完整代码、文件路径、接口签名）
- 每个任务 2-5 分钟，不允许占位符（TBD、TODO）
- 每个任务遵循 TDD：写测试 → 确认失败 → 实现 → 确认通过 → 提交

### 初步优化方案

新增一个 **`code-generation`** skill，适配企业场景：

- **输入**：`docs/app-design.md` + `docs/db-schema.md` + `docs/ontology_schema.json`
- **输出**：精确的实现计划 + 代码生成，每个任务包含：
  - 要创建/修改的文件路径（遵循 Maven 模块结构）
  - 完整的类定义、方法签名（遵循 `backend-tech-guidelines.md`）
  - DDL 建表语句执行顺序
  - MyBatis Mapper XML 的完整 SQL
  - 每个任务对应本体中的哪些对象/行为/规则（可追溯性）
- **关键创新**：因为你有本体图谱，实现计划可以直接标注每段代码对应的本体元素，实现 **本体 → 代码** 的完整可追溯链

### 探讨结论（已确认）

#### 输入来源：业务信息由 app-design 消化，code-generation 只消费技术信息

核心原则：**app-design 的职责就是把业务信息（ontology_schema + brd）消化为技术信息，code-generation 不应再回头读原始业务信息。** 如果 code-generation 还需要读 ontology_schema，说明 app-design 的转换不充分。

| 输入文件 | 作用 | 使用方式 |
|---------|------|---------|
| `docs/app-design.md` | 架构决策、模块划分、接口设计、数据流、错误处理 | **主要输入**——代码生成的直接依据 |
| `docs/db-schema.md` | DDL、表结构、索引 | **主要输入**——PO/Mapper 生成的直接依据 |

注：BRD 功能需求验收不在 code-generation 中处理，由下游验证 skill（优化点2）负责。

**前置条件**：此方案依赖优化点5落地——app-design 必须把本体中的行为和规则完整地转化为技术文档中的接口设计和校验逻辑。否则 code-generation 缺少足够信息。

依赖链：
```
优化点 5（app-design 增加行为→接口 + 规则→代码映射）
   ↓ 落地后，app-design 的产出足够完整
优化点 1（code-generation 只需消费 app-design 产出）
   ↓ 才能真正工作
```

#### 代码生成粒度：两阶段生成——先骨架后填充

核心问题：子代理并行快，但互相不知道对方做了什么，导致集成时 import 路径错误等问题。

解决方案：**先生成全局契约（骨架），再并行填充实现细节**。

**阶段 1：生成全局骨架（单代理，顺序执行）**

这个阶段是"合同"，所有类的全限定名、方法签名、import 路径在这里确定。后续子代理必须遵循这个骨架，不允许修改。

```
- 确定所有模块的包路径（如 com.enn.gas.*）
- 生成所有 PO 类（字段定义、类型、注解）
- 生成所有 VO/DTO 类
- 生成所有 Controller 方法签名（空实现，只有注解和方法头）
- 生成所有 Service/Biz 方法签名（空实现）
- 生成所有 Mapper 接口（空方法声明）
- 生成所有 Mapper XML 骨架（namespace + resultMap）
```

**阶段 2：并行填充实现（多子代理）**

每个子代理负责 1 个本体对象的实现填充。子代理只填充方法体，不修改签名。因为骨架是确定的，子代理之间不会产生冲突，import 路径也不会出错。

```
Task 1: GasContract → 填充 Mapper SQL + Service 逻辑 + Biz 编排 + Controller 实现
Task 2: GasResource → 同上
Task 3: ...
```

**子代理数量与分组策略**：
- 并行子代理的具体数量由 agent 根据实际情况自行决定，skill 中不强制约束
- 分组策略：按对象依赖关系分批——被依赖的对象先生成（如引用对象、核心对象），依赖别人的后生成（如实体对象、关系对象）
- 原则：确保后批可以引用前批已确定的类和方法签名

**阶段 3：集成验证（单代理，顺序执行）**

编译验证 → 运行测试（详见优化点2）。

#### 增量开发支持：前置探测步骤

```
步骤 0：探测已有代码
- 检查项目目录是否存在 Maven 模块结构
- 扫描已有的 Mapper、Service、Controller
- 读取已有的 pom.xml 确定依赖版本
- 确定是"全新项目"还是"增量开发"模式

如果是增量开发：
- 新增的文件不与已有文件冲突
- 新增的 Mapper XML 追加而非覆盖
- 新增的接口路径不与已有路径重复
- import 路径基于已有的 base package 推断

如果是从零开始：
- 按技术规范生成完整项目骨架
- 模块结构、启动类、配置文件一并生成
```

#### 技术规范：严格遵循参考文件，不在 skill 中重复摘录

生成代码时必须严格遵循 `references/backend-tech-guidelines.md` 中的全部技术规范，不可妥协。规范细节由参考文件维护，skill 中不重复摘录——避免维护两份导致不一致。

无论本地环境配置如何，都不允许因"编译不通过"或"运行报错"而省略规范中的任何要求。如果因环境问题导致编译/运行失败，应该生成环境配置说明文档指导用户配置，而不是删除或降级代码中的规范要求。

### 已确认的问题

- [x] 阶段2的子代理数量：由 agent 自行决定，skill 不强制约束；分组按对象依赖关系分批
- [x] BRD 功能需求对照：不在 code-generation 中处理，放入验证环节的 skill（优化点2）；code-generation 的输入只有 app-design.md + db-schema.md
- [x] 阶段1和阶段2之间不单独确认，但骨架文件写入磁盘，用户可随时查看

### 优先级：P0

---

## 优化点 2：无验证闭环——缺 verification + TDD 机制

### 问题描述

所有 4 个 skill 都没有要求"验证产出是否真正可用"。`app-design` 说"规范自审"但只是检查文档，不检查代码是否能运行。没有验证 = 产出质量无保障。

### Superpowers 参考

- `verification-before-completion`：铁律——没有运行验证命令 = 没有完成
- `test-driven-development`：先写失败测试 → 再写代码 → 确认通过
- 防合理化表："测试通过了"必须附上测试命令输出，不能说"应该通过"

### 探讨结论（已确认）

#### 与 code-generation 的边界

- `code-generation` **不做任何验证**，终点是代码文件写入磁盘。如果用户本地没有 Maven 或缺公司内部配置，编译自检会卡住，因此不要求。
- `code-verification` 负责全部验证工作，包含环境引导和跳过机制。

#### 验证范围：三层递进，环境不强求

| 层级 | 内容 | 环境要求 | 不可用时 |
|------|------|---------|---------|
| 静态检查 | 对照 backend-tech-guidelines.md 逐条检查 | 无 | 不存在不可用 |
| 编译验证 | `mvn compile` | JDK + Maven | 跳过，提示安装后重验 |
| 运行验证 | DDL 建表 + 应用启动 + 接口冒烟 | 数据库 + 完整运行环境 | 逐步引导，没有就跳过 |

运行验证逐步引导用户提供环境，没有则跳过，不强求。每个环境步骤如果不可用，明确告知用户跳过了什么、后续如何补验。

#### BRD 功能需求对照：自动扫描 + 人工确认

1. 从 brd.md 提取功能点列表
2. 自动扫描 Controller/BizService 代码按方法名和注释匹配
3. 生成对照清单，标记 ✅/❌
4. 用户只聚焦 ❌ 的项目确认

#### 验证失败处理：分级策略

| 级别 | 定义 | 处理方式 |
|------|------|---------|
| Critical | 技术规范违规（确定性规则，如缺 @Authorize、用了 javax） | 自动修复，修复后重新检查 |
| Important | 编译错误、逻辑缺陷、功能缺失（可能涉及设计决策） | 报告给用户，由用户决定 |
| Minor | 代码风格、优化建议 | 记录备查，不阻断流程 |

#### 独立 skill

新建 `code-verification` skill，不作为 code-generation 的一部分。可被其他场景复用（如人工写完代码后也想验证）。

#### 测试代码：可选生成

- 默认不生成单元测试代码（自动生成的测试往往测的是"代码怎么写的"而非"业务要求什么"，维护成本大于价值）
- 用户可选择让 code-generation 同步生成测试类骨架（继承 BaseTest、方法签名、@Transactional 注解就位，方法体留空或只写基本断言）
- code-verification 不依赖测试代码，有测试就运行，没有也不影响验证结论

### 优先级：P0（已落地）

---

## 优化点 3：ontology-modeling 缺少防合理化机制

### 问题描述

`ontology-modeling` 的"验证与优化"步骤（步骤5）是自检清单，但**没有强制执行机制**。例如：

- "所有核心对象是否都有 CRUD 行为？"——这是一个检查项，但没有说"如果发现遗漏必须立即补齐，不允许跳过"
- 规则过滤原则写得很好，但没有"如果提取了低价值规则应该怎么办"的明确指令
- 没有堵住"这个场景太简单了，不需要完整建模"这类合理化借口

### Superpowers 参考

每个纪律性 skill 都有 **Red Flags 表** + **合理化对照表**，堵住所有跳过流程的借口。例如：

| 合理化想法 | 现实 |
|-----------|------|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "The skill is overkill" | Simple things become complex. Use it. |
| "I'll just do this one thing first" | Check BEFORE doing anything. |

### 初步优化方案

给 `ontology-modeling` 增加铁律和防合理化机制：

```markdown
## 铁律（Iron Laws）

1. **不允许跳过步骤**：即使"这个业务很简单"，也必须完成所有6步。
   - 合理化想法："这个场景太简单了，不需要对象层建模"
   - 现实：简单场景的建模很快，但跳过会导致下游设计偏差

2. **行为必须改变状态**：每个行为必须明确指出改变了哪个对象的哪个属性。
   - 合理化想法："查询行为不需要改变状态"
   - 现实：查询行为 [Q] 的定义就是不改变状态，但它必须明确关联到某个对象

3. **规则过滤必须执行**：如果在 rules[] 中发现基本校验类规则，必须移除并说明理由。
   - 合理化想法："多写几条规则总比少写好"
   - 现实：低价值规则会污染下游代码生成，导致生成冗余校验代码

4. **跨会话必须读取已有文件**：每次新会话必须先读取 docs/ 下的已有产出。
   - 合理化想法："用户应该知道上次做到哪了"
   - 现实：用户可能在不同终端/时间恢复工作，不读取会导致重复建模
```

### 待探讨问题

- [ ] 铁律是否需要和 or-workflow-guide 的路由逻辑联动？例如"检测到用户跳过建模，强制回退"
- [ ] 是否需要增加"轻量模式"？对于真正简单的场景（如只加一个字段），完整6步是否过重？
- [ ] 规则过滤的判断标准是否需要更多正例/反例？当前的正反例来自天然气场景，是否需要覆盖更多业务域？

### 优先级：P1

---

## 优化点 4：or-workflow-guide 路由逻辑缺少中间状态管理

### 问题描述

`or-workflow-guide` 的流程是线性的：建模 → 路由 → 执行。但**没有进度跟踪**，用户说"继续上次的建模"时，路由器不知道做到哪一步了。跨会话时，上下文丢失后无法恢复进度。

### Superpowers 参考

`subagent-driven-development` 使用 **`progress.md`** 持久进度账本，记录每个任务的完成状态，防止对话压缩后丢失上下文。每次子代理启动时先读取进度账本。

### 探讨结论（已确认）

采用 Superpowers 风格的进度账本（progress ledger），参考 `subagent-driven-development` 的 Durable Progress 机制。

**文件位置**：`docs/workflow-progress.md`

**格式**：每个阶段一行，记录完成状态和产出（参照 Superpowers 的 `Task N: complete (commits, review clean)` 格式）：

```
本体建模: complete (步骤1~6, docs/ontology_schema.json + docs/brd.md)
应用设计: complete (步骤1~10, docs/app-design.md + docs/db-schema.md)
代码生成: in progress (步骤1骨架已完成, 步骤2填充中: GasContract/GasResource已完成, GasPlan待执行)
代码验证: pending
```

**核心规则**（参照 Superpowers）：
- **由 or-workflow-guide 统一管理**：各个 skill 不知道账本的存在，or-workflow-guide 在每个 skill 执行完毕或中断时负责写入和更新（参照 Superpowers 中主代理管理 ledger、子代理不知道 ledger 的做法）
- **启动时先检查账本**：已标记 complete 的阶段绝不重复执行，从第一个非 complete 的阶段恢复
- **阶段完成后同步更新账本**：在标记阶段完成的同时写入
- **压缩后信任账本**：不信任自己的记忆，以账本记录为准

**回退处理**：用户想重新做某个阶段时，直接进入对应 skill 即可（如 ontology-modeling 已有"读取已有文件，在基础上继续"的机制），完成后更新账本。

### 优先级：P2（已落地）

---

## 优化点 5：app-design 与 ontology-modeling 的衔接不够紧密

### 问题描述

- `app-design` 说"读取本体图谱文件"，但只笼统提了类、属性、关系
- 数据库设计规则中的"每个本体类对应一张业务表"是好的，但**没有行为到接口的映射规则**
- 缺少**规则到代码逻辑的映射规则**
- 导致从设计到代码的推导过程中，行为和规则的信息丢失

### Superpowers 参考

`writing-plans` 中的每个任务都精确关联到上游设计的具体元素，实现可追溯性。

### 探讨结论（已确认）

#### 映射规则放在 SKILL.md 中，不放技术规范

技术规范定义技术栈的硬约束（必须怎样），映射规则定义从业务到技术的推导方法（应该怎样推导）。两者职责不同，映射规则是 app-design skill 的核心方法论，放 SKILL.md 中。

#### 行为→接口映射

每个核心对象的 5 类行为映射为 Controller 接口，统一使用 POST 方法（遵循技术规范）：

| 行为类型 | HTTP 方法 | URL 模式 | Biz 方法 | Service 方法 |
|---------|----------|---------|---------|-------------|
| Create [C] | POST | /api/{object}/create | create{Object}() | insert{Object}() |
| Update [U] | POST | /api/{object}/update | update{Object}() | update{Object}() |
| Query [Q] | POST | /api/{object}/query | query{Object}() | select{Object}List/ById() |
| Delete [D] | POST | /api/{object}/delete | delete{Object}() | delete{Object}() |
| Derive [->] | POST | /api/{source}/derive{Target} | derive{Target}From{Source}() | 源查询+目标创建 |

#### 规则→代码映射

| 规则类型 | 实现位置 | 实现方式 |
|---------|---------|---------|
| 计算规则 | Service 层 | 独立方法，返回计算结果 |
| 约束规则 | Biz 层 | 校验方法，不通过抛业务异常 |
| 跨实体一致性 | Biz 层 | 事务内校验 |

Biz 层典型模式：约束校验（约束规则）→ 调用 Service 计算（计算规则）→ 执行操作

#### SOP 流程→Biz 编排方法

一个 SOP 流程对应一个 Biz 方法，方法内部按步骤依次调用对应的 Service。不需要独立流程引擎，条件分支用 if-else 实现。

#### 设计文档必须包含映射表达

app-design.md 的接口设计部分必须包含：行为→接口映射表、规则→代码位置映射表、SOP→Biz 编排方法映射表。确保下游 code-generation 可直接推导出完整代码骨架。

### 优先级：P1（已落地）

---

## 优化点 6：brd-generation 与 ontology-modeling 功能重叠

### 问题描述

`brd-generation` 是 `ontology-modeling` 的子集（只产 BRD 不产 Schema），但维护了两套独立的模板和示例。增加了维护成本，也容易让用户选错入口。

### Superpowers 参考

Superpowers 中没有类似的重叠技能。每个技能的职责边界清晰，不存在"A 做的事 B 也能做"的情况。

### 初步优化方案

两种选择：

**(a) 合并**：删除 `brd-generation`，所有 BRD 需求统一走 `ontology-modeling`。如果用户只需要 BRD 不需要 Schema，在 `ontology-modeling` 中增加一个"轻量模式"标志，跳过 Schema 持久化但保留双产出。

**(b) 明确分层**：如果保留，让 `brd-generation` 明确声明"本 skill 适用于只需要文档产出的场景，如果后续需要应用设计，请使用 `ontology-modeling`"，避免用户选错入口。

### 待探讨问题

- [ ] 实际使用中，是否有用户确实只需要 BRD 而不需要 Schema？
- [ ] 如果合并，"轻量模式"的体验如何保证？是否会因为流程相同而导致产出冗余？
- [ ] 如果保留，如何确保两套模板和示例的同步更新？

### 优先级：P3

---

## 优化点 7：缺少代码审查环节

### 问题描述

整个流程没有任何代码审查机制。代码生成后直接交给用户，没有"第二双眼睛"检查质量。

### Superpowers 参考

- `requesting-code-review`：派遣独立审查子代理，在问题扩散之前捕获它们
- `receiving-code-review`：专业地接收和处理审查反馈
- 审查标准：Critical（立即修复）、Important（继续前修复）、Minor（记录后续处理）

### 初步优化方案

### 探讨结论（已确认）

#### 合并到 code-verification，不单独建 skill

代码审查合并到 code-verification 中作为步骤 2，避免流程过长。code-verification 已经要逐文件检查代码，顺便做质量审查不需要额外开销。

#### 与技术规范合规检查的区别

| | 步骤 1：技术规范合规 | 步骤 2：代码质量审查 |
|---|---|---|
| 目标 | 检查"有没有"——规范有没有遵守 | 检查"好不好"——代码质量、设计合理性、安全风险 |
| 执行者 | 当前代理 | 独立子代理（提供"新鲜视角"） |

#### 全部完成后统一审查

code-generation 的多子代理并行填充完成后，统一做一次审查。可以看全局，发现跨对象的问题。不需要每个对象完成后立即审查。

#### 子代理执行审查

派遣独立子代理，给 diff 文件和技术规范，独立审查代码质量。避免"自己看不到自己的问题"。

审查关注点：代码重复、职责边界、异常处理、安全风险（SQL 拼接等）、数据一致性、代码可维护性。

### 优先级：P2（已落地）

---

## 总结：优先级排序

| 优先级 | 优化项 | 状态 |
|-------|--------|------|
| **P0** | 优化点1：新增 `code-generation` skill | ✅ 已落地 |
| **P0** | 优化点2：新增 `code-verification` skill | ✅ 已落地 |
| **P1** | 优化点3：`ontology-modeling` 增加铁律 | ⏭️ 跳过 |
| **P1** | 优化点5：`app-design` 增加行为→接口/规则→代码映射 | ✅ 已落地 |
| **P2** | 优化点4：`or-workflow-guide` 增加进度账本 | ✅ 已落地 |
| **P2** | 优化点7：代码质量审查（合并到 code-verification） | ✅ 已落地 |
| **P3** | 优化点6：处理 `brd-generation` 重叠 | ⏭️ 暂不处理 |
