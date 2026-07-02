# app-design Skill 调整方案

日期：2026-07-01

## 1. 背景

本方案基于一次真实使用链路：先用 `ontology-modeling` 为 EnnewClaw 扫码登录生成 `docs/ontology_schema.json` 与 `docs/brd.md`，再使用 `app-design` 做功能设计。

这次任务不是新建 Java/Spring Boot 或 Python/FastAPI 后端应用，而是在现有 Electron + Vue 3 + TypeScript 桌面端中增量扩展认证功能。当前 `app-design` 仍强绑定“后端语言 Java/Python、MySQL DDL、后端接口契约”，导致设计阶段出现了几处不适配：

- skill 要求确认 Java/Python 后端语言，但实际项目没有新增后端。
- `app-contract.schema.json` 只允许 `project.backend.language = java | python`，无法表达 Electron/TypeScript 桌面端功能设计。
- 数据库规则要求“每个本体类对应一张业务表”，但扫码登录票据是认证服务短生命周期状态，不应该落桌面端业务表。
- 行为到接口映射只覆盖 HTTP Controller/Biz/Service，不覆盖 Electron IPC、preload、renderer service、Vue component 这类桌面端边界。
- “每部分展示后等待用户批准”的强流程在 coding agent 单轮设计任务中容易卡住，实际更适合产出“审批点清单”后让用户一次评审。

## 2. 调整目标

让 `app-design` 保持“本体驱动设计 + 结构化契约 + 覆盖率门禁”的核心优势，同时支持更多项目形态：

- Java/Spring Boot 新后端项目
- Python/FastAPI 新后端项目
- 现有 Web/桌面/前端/Node/Electron 项目的增量功能设计
- 无新增数据库表、只改 IPC/API/UI/本地 KV 的功能
- 无法直接进入 `code-generation` 的非后端设计产物

## 3. 核心调整建议

### 3.1 增加“项目目标类型”判定，先于后端语言选择

当前流程第 3 步是“确认后端开发语言”。建议改为：

1. 先判断设计目标类型。
2. 只有目标类型是“新建后端应用”或“后端模块生成”时，才强制选择 Java/Python。
3. 如果是现有项目增量设计，则以现有项目技术栈为准。

建议新增目标类型：

| target_kind | 适用场景 | 技术选型要求 |
|-------------|----------|--------------|
| `backend-java` | 新建或扩展 Java/Spring Boot 后端 | 读取 Java 规范 |
| `backend-python` | 新建或扩展 Python/FastAPI 后端 | 读取 Python 规范 |
| `existing-app-feature` | 在现有项目中新增功能 | 读取项目技术栈，生成项目内设计 |
| `desktop-electron-feature` | Electron 桌面端 IPC/UI/主进程功能 | 以 Electron + renderer/main/preload 边界设计 |
| `frontend-only-feature` | 纯前端界面或交互 | 不生成后端/DDL |
| `docs-or-process` | 流程、规范、文档类改造 | 不生成代码契约 |

`app-design/SKILL.md` 中的“后端语言必问项”应改为“当且仅当 target_kind 需要后端生成时才必问”。

### 3.2 将“后端技术规范”改为“实现目标规范”

建议把 `references/backend-tech-guidelines.md` 调整为更通用的入口，例如：

- `references/implementation-target-guidelines.md`
- 或保留旧文件名，但内容新增 target_kind 路由表

路由规则：

| target_kind | 需要读取的参考 |
|-------------|----------------|
| `backend-java` | `backend-tech-guidelines.md` + `backend-java-tech-guidelines.md` |
| `backend-python` | `backend-tech-guidelines.md` + `backend-python-tech-guidelines.md` |
| `desktop-electron-feature` | 新增 `electron-vue-tech-guidelines.md` |
| `existing-app-feature` | 先读项目 `AGENTS.md` / 模块 spec / 相关代码，必要时读对应 target reference |
| `frontend-only-feature` | 前端设计规范或项目 UI 规范 |

这样既不破坏原 Java/Python 流水线，也能支持 EnnewClaw 这类桌面端增量任务。

### 3.3 为 app-contract 增加多目标 schema

当前 `app-contract.schema.json` 强约束：

```yaml
project.backend.language: java | python
objects[].behaviors[].controller: /api/...
```

这对 Electron IPC 功能不适用。建议新增 contract v2，保留 Java/Python 兼容，同时支持非后端目标：

```yaml
version: 2
project:
  targetKind: desktop-electron-feature
  implementation:
    language: typescript
    framework: electron-vue
    guideline: AGENTS.md
  modules:
    - shared-auth
    - main-auth
    - preload-auth
    - renderer-auth

objects:
  - code: qr_login_ticket
    name: QrLoginTicket
    persistence: external-auth-service
    behaviors:
      - type: CREATE
        surfaces:
          renderer: EnnewQrLogin.startQrLogin
          preload: electron.auth.startQrLogin
          ipc: AuthIpcChannel.StartQrLogin
          main: startEnnewQrLogin
          external: POST /userCenter/unify/auth/qr/create
```

建议字段变化：

- `project.backend` 改为 `project.implementation`，或同时支持二者。
- `controller/biz/service` 改为通用 `surfaces`，Java/Python 可继续填 `controller/biz/service`。
- `table` 改为可选；新增 `persistence` 表达 `mysql-table`、`sqlite-kv-existing`、`external-service`、`transient-memory`、`none`。
- rules 的 `location` 允许 `Module.method()`、`Component.method()`、`file:function` 等 TypeScript/前端形式。
- sops 的 `calls` 允许跨 UI/service/IPC/main helper 的调用链。

### 3.4 数据库设计增加“持久化决策门禁”

当前规则“每个本体类对应一张业务表”对业务后端成立，但对外部服务状态、UI 状态、短生命周期票据不成立。

建议在数据库设计前增加“持久化决策表”：

| 对象类型 | 是否建表 | 规则 |
|----------|----------|------|
| 核心业务实体 | 通常建表 | 有独立生命周期、需要本系统持久化 |
| 外部系统实体 | 不建表或只存引用 | 数据权威源在外部系统 |
| 短生命周期流程状态 | 默认不建表 | 如扫码票据、验证码、临时授权态 |
| UI 状态 | 不建表 | 组件内状态或 store 状态 |
| 既有本地 KV 状态 | 不新增表 | 复用现有 key，设计中说明 key 契约 |
| 审计事件 | 视项目已有审计能力 | 没有明确审计表时不强制新建 |

数据库设计产物应按实际方案生成，而不是所有任务都强制生成 SQL 文件：

- 如果需要新增或修改数据库表，必须生成 `docs/contracts/db-schema.sql`，并把它作为权威 DDL。
- 如果不涉及数据库变更，不强制生成 `db-schema.sql` 或 `db-schema.md`，但必须在 `docs/app-design.md` 写明“数据库影响：无”及原因。
- 如果下游兼容旧 `code-generation` 或其他自动化强依赖 SQL 文件存在，才允许生成 no-op `docs/contracts/db-schema.sql` 作为兼容产物，并在文档中说明它不是实际数据库设计。

这样能避免为了满足 skill 产物而错误地把扫码票据落本地库，也避免制造无意义文件。

### 3.5 行为映射增加“应用表面”而不只 HTTP 接口

建议把 `references/ontology-mapping-rules.md` 拆成通用规则 + target-specific 规则：

- `ontology-mapping-rules.md`：对象/行为/规则/SOP 的通用追溯要求。
- `mapping-backend-java.md`：HTTP Controller/Biz/Service/DAL。
- `mapping-backend-python.md`：API Router/Biz/Service/Repository。
- `mapping-electron-vue.md`：Vue Component / renderer service / preload / IPC / main helper / external API。
- `mapping-frontend-only.md`：Component / composable / store / service / route。

Electron/Vue 映射建议：

| 本体行为 | 映射表面 |
|----------|----------|
| Create | component action -> renderer service -> preload -> IPC -> main helper |
| Query | component polling/query -> renderer service -> IPC -> main helper/external API |
| Update | component action -> IPC -> main helper |
| Delete/Cancel | component cleanup/cancel -> IPC -> main helper |
| Derive | main/helper 或 renderer orchestration 将一个对象结果转换为下游对象输入 |

### 3.6 用户审批流程改为“交互式优先、批量草案兜底”

当前 skill 要求每个设计部分都展示并等待批准。这个流程适合长交互，但在用户说“进行功能设计”时，agent 通常需要一次性生成草案。

建议改为：

- 当用户明确要求“逐步设计/边聊边确认”时，保持每部分批准。
- 当用户要求“生成设计/出方案/做功能设计”且没有要求逐步确认时，允许一次性生成 draft，但必须在文档末尾列出“当前审批点”。
- 在 final 回复中提醒用户审查并批准，未批准前不得进入实现。

这保留 hard gate，又减少无谓等待。

### 3.7 输出产物按目标类型裁剪

建议产物规则改为：

| target_kind | 必需产物 |
|-------------|----------|
| `backend-java` / `backend-python` | `docs/app-design.md`、`docs/contracts/db-schema.sql`、`docs/db-schema.md`、`docs/contracts/app-contract.yaml` |
| `desktop-electron-feature` | `docs/app-design.md`、`docs/contracts/app-contract.yaml`；仅在有数据库变更或兼容需要时生成 DB 文件 |
| `frontend-only-feature` | `docs/app-design.md`、`docs/contracts/app-contract.yaml`；DB 文件按需生成 |
| `docs-or-process` | `docs/app-design.md`；结构化契约可选 |

这样避免所有任务都被强行压进后端应用模板。

## 4. 建议修改文件清单

### P0：先改 app-design 主流程

- `skills/app-design/SKILL.md`
  - 在检查清单第 3 步前新增“确认设计目标类型”。
  - 将“确认后端语言”改为“确认实现目标与技术规范”。
  - 修改 hard gate 后的设计流程，允许“批量草案 + 审批点”模式。
  - 数据库设计章节加入“持久化决策门禁”和按需生成数据库产物规则。
  - 接口映射章节从 HTTP 后端扩展为 target-specific surfaces。

### P0：新增/调整参考文件

- 新增 `skills/app-design/references/implementation-target-guidelines.md`
- 新增 `skills/app-design/references/mapping-electron-vue.md`
- 新增 `skills/app-design/references/app-contract-v2-template.yaml`
- 新增 `skills/app-design/references/app-contract-v2.schema.json`

### P1：保留兼容，逐步迁移

- 保留现有 `app-contract-template.yaml` 与 `app-contract.schema.json` 给 Java/Python code-generation 使用。
- 在 `code-generation` 中声明：只有 legacy Java/Python contract 或 v2 targetKind 为 backend 时才可直接生成后端项目。
- 在 `code-verification` 中支持读取 v2 traceability contract 做非后端功能验证。

## 5. 建议的 SKILL.md 文案调整片段

### 5.1 检查清单替换建议

将当前第 3 步：

> 确认后端开发语言并理解项目技术规范

替换为：

> 确认设计目标类型与实现技术规范。先判断本次是 Java/Python 后端生成、现有项目增量功能、Electron 桌面端功能、纯前端功能，还是流程/文档设计。只有当目标类型需要后端生成时，才要求用户选择 Java/Spring Boot 或 Python/FastAPI；现有项目增量功能必须优先遵循项目技术栈和 AGENTS.md。

### 5.2 数据库设计规则前新增

```markdown
### 持久化决策门禁

在从本体对象推导表结构前，先判断每个对象的数据权威源和生命周期。
只有由当前应用长期持久化、具有独立业务生命周期的对象才建表。
外部系统权威对象、短生命周期票据、UI 状态、轮询状态、一次性授权码、已有 KV 状态默认不建表。

数据库设计产物按实际方案生成。持久化决策是必选环节；当方案不涉及数据库变更时，不强制生成 `docs/contracts/db-schema.sql` 或 `docs/db-schema.md`，但必须在 `docs/app-design.md` 明确记录“数据库影响：无”及原因。只有下游生成器或兼容流程明确依赖 SQL 文件存在时，才生成 no-op `docs/contracts/db-schema.sql` 作为兼容产物，并说明它不是实际数据库设计。
```

### 5.3 契约产物规则替换建议

```markdown
结构化契约根据 target_kind 选择格式：

- backend-java/backend-python：使用现有 Java/Python app-contract 模板，供 code-generation 确定性生成后端。
- desktop-electron-feature/frontend-only-feature/existing-app-feature：使用 app-contract v2 traceability 模板，记录对象、行为、规则、SOP 到 UI/service/IPC/helper/API 的映射；该契约默认不直接交给后端 code-generation。
```

## 6. 与本次扫码登录案例的对应关系

| 暴露问题 | 调整后处理方式 |
----------|----------------|
| 任务是 Electron 桌面端，不是后端生成 | target_kind = `desktop-electron-feature` |
| Java/Python 必选不适用 | 读取 Electron/Vue 目标规范，不问 Java/Python |
| 扫码票据不该建表 | 持久化决策门禁判定为 `external-auth-service`，设计文档记录“数据库影响：无”；只有兼容旧流程时才生成 no-op SQL |
| 行为不是 HTTP Controller | surfaces 映射到 Vue component / authService / preload / IPC / main helper |
| contract schema 不支持 TS/Electron | 使用 app-contract v2 |
| 用户没有逐步审批每一节 | 一次性 draft，文末列出审批点，未批准不实现 |

## 7. 推荐落地顺序

1. P0：先改 `SKILL.md` 的 target_kind 路由、后端语言条件化、持久化门禁、批量草案兜底。
2. P0：新增 `implementation-target-guidelines.md` 与 `mapping-electron-vue.md`。
3. P0：新增 contract v2 template/schema。
4. P1：更新 `code-generation`，明确只消费 backend target 的契约。
5. P1：更新 `code-verification`，支持 v2 traceability contract。
6. P2：补 2-3 个 forward-test 用例：
   - Electron 扫码登录增量功能。
   - 纯前端设置页功能。
   - Java 后端新模块，验证旧流程不被破坏。

## 8. 验收标准

- 使用 `app-design` 处理 Electron/Vue 增量功能时，不再强迫选择 Java/Python。
- 对无数据库变更的功能，不强制产出 `db-schema.sql`，但必须在设计文档中清晰记录持久化判断和“不改数据库”的理由。
- `app-contract` 能表达 UI/service/preload/IPC/main helper/external API 映射。
- Java/Python 后端项目原流程仍可使用现有模板和 schema。
- 设计阶段仍保留 100% 覆盖率门禁：对象、规则、SOP 必须全部映射到契约。
- 未经用户批准的设计不得进入实现。

## 9. 不建议的改法

- 不建议直接把 `typescript` 加进旧 `project.backend.language` 枚举；这会混淆“后端生成契约”和“桌面端追溯契约”。
- 不建议删除 Java/Python 规范；它们仍是后端生成流水线的核心。
- 不建议所有本体对象都建表；这会把外部服务状态和 UI 状态错误持久化。
- 不建议把 Electron/Vue 映射硬塞进 `controller/biz/service` 三字段；应使用更通用的 `surfaces`。
