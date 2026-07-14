---
name: code-verification
description: "对已生成的代码进行交付前质量验证：技术规范合规、代码质量审查、基于 traceability.json 或 app-contract 的功能完整性确定性对照、运行验证，并对缺陷做根因分类回流（设计层/实现层）。当代码生成完成后、现有应用增量实现完成后、交付前使用。"
---

# 代码验证

对已生成的代码进行交付前的质量验证。code-generation 只负责生成代码文件，不执行任何验证；本 skill 是对最终产出的全面质量把关。

## 输入

| 输入文件 | 作用 |
|---------|------|
| `docs/app-design.md` | 技术规范合规检查的依据（人读视图） |
| `docs/contracts/db-schema.sql` | 数据库设计合规检查的权威依据（可执行 DDL）；无数据库变更时可不存在 |
| `docs/contracts/app-contract.yaml` | 接口/应用表面、规则/SOP 契约，校验代码是否与设计契约一致的依据；统一 v2 格式（存量 legacy 旧契约只读兼容） |
| `docs/traceability.json` | **功能完整性对照的确定性依据**——本体/规则/SOP/需求 code → 代码位置；须符合 `references/traceability.schema.json` |
| `docs/requirements-baseline.json` | 已批准需求基线，判定功能点是否为已批准需求的锚点 |
| `docs/contracts/acceptance-tests.yaml` | 可选验收测试视图，由 requirements baseline 派生；存在时用于自动验收/接口冒烟 |
| `docs/brd.md` | 功能完整性对照的补充验收清单 |

> 若 `traceability.json` / `requirements-baseline.json` 缺失，或上游阶段为 `waived`（非完整 SDD 输入），需在报告中明确「追溯置信度受限 / 上游被豁免」，并降级为方法名模糊匹配。

## 验证流程

### 步骤 1：技术规范合规检查

先读取 `docs/contracts/app-contract.yaml`，按 `project.targetKind` 分流：

- 后端契约（`backend-java` / `backend-python`）：读取 `../app-design/references/backend-tech-guidelines.md` 和对应语言规范逐条检查生成的代码。存量 legacy 旧契约（无 `version` 字段）按 `project.backend.language` 确定语言，同样走后端规范检查。
- 非后端契约：不要套用 Java/Python 后端规范；改为按 `project.implementation.guideline`、仓库规范、`docs/app-design.md` 和 `objects[].behaviors[].surfaces` 做项目内一致性检查。

后端语言规范：

- `java` -> `../app-design/references/backend-java-tech-guidelines.md`
- `python` -> `../app-design/references/backend-python-tech-guidelines.md`

**检查项**（包括但不限于）：

| 检查维度 | Java 具体项 | Python 具体项 |
|---------|-------------|---------------|
| 接口层 | Controller 方法是否有 `@Authorize` 注解、返回类型是否为 `ServiceResult<VO>` | API Router 是否声明鉴权依赖、是否使用统一 Result 包装 |
| 命名空间/类型 | 是否使用 `jakarta` 而非 `javax` | 是否有公共函数类型标注，Pydantic Schema 是否清晰 |
| 框架规范 | PO/DTO/VO 是否使用 `@Data`、Mapper 是否使用 `@Mapper` | FastAPI Router、Pydantic v2、SQLAlchemy 2.x 用法是否符合规范 |
| 分层规范 | Biz/Service 是否直接用实现类（无 interface）、数据转换方向是否为 PO -> DTO -> VO | API -> Biz -> Service -> Repository -> DB 是否单向依赖，API/Biz 是否直接暴露 ORM Model |
| 审计字段 | 每张表对应的 PO 是否包含 create_by/gmt_create/update_by/gmt_modified | 每张表对应的 Model 是否包含 create_by/gmt_create/update_by/gmt_modified |
| 时间/小数类型 | 时间字段是否使用 `java.util.Date`，小数是否用 BigDecimal | 时间字段是否与数据库 datetime 一致，小数是否用 Decimal |
| 数据库规范 | 是否存在外键约束、是否使用了 float/double、字段命名是否规范 | 是否存在外键约束、是否使用了 float、字段命名是否规范 |

非后端契约检查项：

| 检查维度 | 具体项 |
|---------|--------|
| 应用表面 | `surfaces` 中的 component/renderer/preload/ipc/main/external 是否能在代码或接口定义中找到对应位置 |
| 边界一致性 | renderer 不直接调用 main-only 能力，preload 暴露面与 IPC channel 对齐 |
| 状态与清理 | 轮询、超时、取消、组件卸载或窗口关闭清理策略是否实现 |
| 持久化 | `persistence` 为非建表对象时未新增伪表；本地 KV key 与设计一致 |
| 数据库规范 | 只有存在 `docs/contracts/db-schema.sql` 时才执行 DDL 规范检查 |

**问题分级**：

| 级别 | 定义 | 处理方式 |
|------|------|---------|
| **Critical** | 技术规范违规（确定性规则，如缺鉴权、用了错误命名空间、绕过分层） | **自动修复**，修复后重新检查 |
| **Important** | 编译错误、逻辑缺陷（可能涉及设计决策） | **报告给用户**，由用户决定如何处理 |
| **Minor** | 代码风格、优化建议 | **记录备查**，不阻断流程 |

### 步骤 2：代码质量审查（子代理执行）

派遣独立子代理审查代码质量，提供没有上下文包袱的"新鲜视角"。

**与步骤 1 的区别**：步骤 1 检查"有没有"（规范有没有遵守），步骤 2 检查"好不好"（代码质量、设计合理性、安全风险）。

**子代理输入**：
- 生成代码的 diff 文件（通过 `git diff` 生成）
- `../app-design/references/backend-tech-guidelines.md` 和所选语言技术规范

**审查关注点**：

| 维度 | 典型问题 |
|------|---------|
| 代码重复 | 多个 Service 中重复相同的逻辑块 |
| 职责边界 | Biz 层是否做了 Service 层该做的事，Service 层是否越权 |
| 异常处理 | 是否吞掉异常、是否有空 catch、业务异常是否明确 |
| 安全风险 | SQL 拼接（Java/MyBatis 中使用 `${}` 而非 `{}`；Python 中拼接原始 SQL）、未校验的入参 |
| 数据一致性 | 跨对象操作是否有事务保障 |
| 代码可维护性 | 文件是否过大、方法是否过长、命名是否清晰 |

**子代理输出**：审查报告，按 Critical / Important / Minor 分级。

**问题分级与处理**（与步骤 1 相同）：

| 级别 | 处理方式 |
|------|---------|
| Critical | 自动修复 |
| Important | 报告给用户 |
| Minor | 记录备查 |

### 步骤 3：功能完整性对照（确定性匹配）

以**确定性追溯制品**为主依据，将需求基线与生成的代码做对照，**自动生成对照清单，用户聚焦未匹配项确认**。

**对照方式**（按优先级，确定性优先）：

1. **优先读 `docs/traceability.json`**：以 `requirements` / `objects` / `rules` / `sops` 的 code→代码位置映射做**确定性匹配**，不再靠方法名+注释模糊匹配（改名不失配、漏标注不误判）。
2. 如果没有 `traceability.json`，使用 `app-contract.yaml` 的 `objects[].behaviors[].surfaces`、`rules[].location`、`sops[].entry/calls` 作为确定性追溯输入。
3. 以 `docs/requirements-baseline.json` 为需求锚点：确认每个 Must Have 需求都有对应代码实现，且判定其是否为「已批准需求」。**对照范围**：默认只对照 `status` 非 `delivered` 的需求（当前场景）；带 `delivered` 标记的历史需求已在其场景交付时验证过，仅在用户要求全量回归时纳入对照。
4. 以 `docs/requirements-baseline.json` 的 `acceptance_criteria[]` 为验收条件权威；若存在 `docs/contracts/acceptance-tests.yaml`，逐条 `given/when/then` 执行或判定其是否可被代码满足。
5. `docs/brd.md` §4 作为补充（仅在上述制品缺失时降级使用）。

生成对照清单：

```
| 需求ID | BRD 功能需求 | 对应代码位置(traceability.json) | 验收条件 | 状态 |
|--------|-------------|------------------------------|---------|------|
| F-001  | 创建合同     | GasContractController.createGasContract() | 创建后状态=草稿 | ✅ 已匹配 |
| F-002  | 合同审批     | GasContractBizService.executeApprovalFlow() | 审批链路完整 | ✅ 已匹配 |
| F-005  | 利润计算     | ??? | 交付量×(售价-采购价) | ❌ 未找到对应实现 |
```

将清单呈现给用户，用户重点确认 ❌ 的项目：

- 如果是命名差异导致未匹配，用户确认后标记为 ✅
- 如果确实缺失，**进入步骤 6 做根因识别**（区分是设计层缺失还是实现层缺失），不再笼统归为 Important

### 步骤 4：运行验证（条件执行）

逐步引导用户提供运行环境，如果环境不可用则跳过，不强求。

**环境检查顺序**：

1. **语言构建工具**：Java 检查 JDK + Maven，能否执行 `mvn compile`；Python 检查 Python + 依赖管理工具，能否执行测试/导入检查。
   - 如果不能 → 跳过运行验证，提示用户安装后重新执行
2. **数据库**：是否有可连接的 MySQL 实例？
   - 引导方式："运行验证需要连接 MySQL 数据库。请提供连接信息（host/port/database/username），或输入 skip 跳过数据库验证。"
   - 如果不能 → 跳过数据库相关验证
3. **应用启动**：能否启动所选语言应用（Java: Spring Boot；Python: FastAPI/Uvicorn）？
   - 如果不能 → 跳过接口冒烟测试

**运行验证内容**（按环境可用性逐步执行）：

| 环境就绪 | 验证内容 |
|---------|---------|
| 构建工具可用 | Java: `mvn compile` 编译通过；Python: 依赖安装、导入检查或 `pytest` 基础检查通过 |
| 数据库可用 | DDL 建表语句执行成功 |
| 应用可启动 | 接口冒烟测试（POST /api/xxx/create 等端点可达） |

每个环境步骤如果不可用，明确告知用户跳过了什么、后续如何补验。

### 步骤 5：输出验证报告

汇总所有检查结果，生成验证报告：

```markdown
# 代码验证报告

## 技术规范合规
- ✅ 通过：12 项
- 🔧 已自动修复：3 项（列出修复内容）
- ⚠️ 待用户确认：1 项（列出 Important 问题）
- 💡 建议：2 项（列出 Minor 问题）

## 代码质量审查
- ✅ 通过：6 项
- ⚠️ 待用户确认：2 项（如：Biz 层包含计算逻辑应下沉到 Service 层）
- 💡 建议：1 项（如：GasPlanService 方法超过 50 行，建议拆分）

## 功能完整性（对照 traceability.json / requirements-baseline.json）
- ✅ 已匹配：8 / 10 项（确定性匹配，基于 code→代码位置）
- ❌ 未匹配：2 项（列出，已进入步骤6根因分类）

## 运行验证
- 编译：✅ 通过 / ❌ 失败 / ⏭️ 跳过（原因）
- 数据库：✅ 建表成功 / ⏭️ 跳过（无可用数据库）
- 应用启动：⏭️ 跳过（无法连接数据库）

## 待处理事项（按根因分类）
1. [Important][spec-gap] xxx —— 建议回到 app-design 修订 app-contract.yaml 的对应映射
2. [Important][impl-gap] xxx —— 建议回到 code-generation 局部重生成对应方法
```

### 步骤 6：缺陷根因识别与回流（闭环）

验证不是流水线的终点，而是**反馈起点**。对步骤 1–4 发现的每个 Important 缺陷、以及步骤 3 的未匹配项，做根因定位并标注回流方向，使缺陷能回流为对应层规格/代码的修订，避免规格与实现长期背离。

**根因分类**：

| 标签 | 判定依据 | 回流动作 |
|------|---------|---------|
| `[spec-gap]`（设计层缺失） | `app-contract.yaml` 漏了某对象/行为/规则的映射，或 `db-schema.sql` 缺表/缺字段，或 `requirements-baseline.json` 漏了需求 | 回到 **app-design** 局部修订契约（补映射/补表/补需求）→ 再触发 code-generation 局部重生成受影响部分 |
| `[impl-gap]`（实现层缺失） | 契约里有该映射（`traceability.json` 应有但代码实际缺失/实现错误） | 回到 **code-generation** 局部重生成对应方法，无需改设计 |

**判定方法**（确定性优先）：

1. 查 `traceability.json` 是否有该 code/需求 → 有则说明契约层已定义，缺失在代码 → `[impl-gap]`。
2. `traceability.json` 中没有该 code/需求，但 `ontology_schema.json` / `requirements-baseline.json` 中有 → 说明 app-design 消化时漏了映射 → `[spec-gap]`。
3. 两者都没有 → 需求本身可能未被纳入本轮范围，标注 `[scope]` 交用户决策。

**输出**：将分类结果写回报告「待处理事项」（每条带 `[spec-gap]`/`[impl-gap]`/`[scope]` 标签与建议修订位置），并提示用户：`[spec-gap]` 项需先改契约再重生成代码，`[impl-gap]` 项可直接重生成代码。这样实现「缺陷 → 定位根因 → 修订对应层 → 重新生成」的反馈闭环。

**与 C1 变更分支衔接**：当 `[spec-gap]`/`[impl-gap]` 项修订后需重生成代码时，走 or-workflow-guide 的「规格变更处理」分支做**增量重生成**（仅改受影响类/方法 + 增量更新 `traceability.json` / `sdd-state.yaml`），而非整条流水线重跑——缺陷回流天然就是一次规格变更，复用变更分支避免全量返工。

## 技术规范参照

验证后端契约时必须对照 `../app-design/references/backend-tech-guidelines.md` 和契约中指向的语言规范，不可妥协。验证非后端契约时，对照 `project.implementation.guideline`、仓库规范、`docs/app-design.md` 与契约 surfaces，不套用后端专用规则。

## 关键原则

- **验证是终检也是反馈起点**：code-generation 不做任何验证，所有质量检查在本 skill 完成；同时缺陷经步骤 6 根因分类回流到设计层或实现层，闭合规格↔实现的反馈环
- **规范合规 + 代码质量双维度**：步骤 1 检查"有没有"（规范有没有遵守），步骤 2 检查"好不好"（代码质量、设计合理性、安全风险）
- **代码质量审查由子代理执行**：提供没有上下文包袱的"新鲜视角"，避免自己看不到自己的问题
- **分级处理**：Critical 自动修复、Important 报告用户、Minor 记录备查——不过度打断，也不放任问题
- **环境不强求**：逐步引导，有环境就验，没有就跳过，明确告知跳过了什么
- **功能对照确定性优先**：以 `traceability.json` + `requirements-baseline.json` 做确定性匹配，`acceptance-tests.yaml` 仅作为可选自动验收视图；制品缺失或上游 `waived` 时降级为模糊匹配并明确标注置信度受限
- **缺陷回流有方向**：`[spec-gap]` 回 app-design 改契约、`[impl-gap]` 回 code-generation 改代码——让验证驱动迭代而非止于报告
