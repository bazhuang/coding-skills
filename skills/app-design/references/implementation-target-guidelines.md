# 实现目标规范入口

先判断本次设计的 `target_kind`，再读取对应技术规范。不要在非后端目标中强制选择 Java/Python 或强制生成数据库表。

## target_kind 路由

| target_kind | 适用场景 | 必读参考 | 契约格式 |
|---|---|---|---|
| `backend-java` | 新建或扩展 Java/Spring Boot 后端 | `backend-tech-guidelines.md` + `backend-java-tech-guidelines.md` | v2 契约（backend target，含 basePackage + api/biz/service surfaces） |
| `backend-python` | 新建或扩展 Python/FastAPI 后端 | `backend-tech-guidelines.md` + `backend-python-tech-guidelines.md` | v2 契约（backend target，含 basePackage + api/biz/service surfaces） |
| `existing-app-feature` | 在现有项目中增量新增功能 | 仓库规范、`AGENTS.md`、相关代码；必要时读取对应 target reference | v2 契约（traceability） |
| `desktop-electron-feature` | Electron 桌面端 IPC/UI/主进程功能 | `mapping-electron-vue.md` + 仓库规范 | v2 契约（traceability） |
| `frontend-only-feature` | 纯前端界面、交互、状态或组件 | 项目 UI 规范、组件库、路由/store 约定 | v2 契约（traceability） |
| `docs-or-process` | 流程、规范、文档类改造 | 相关文档和组织约束 | app-design.md；契约可选 |

所有 target 统一产出 v2 契约（`version: 2`，见 `app-contract-v2-template.yaml`）。旧 legacy 后端格式已弃用，仅对存量项目只读兼容。

## 判定顺序

1. 先看用户是否明确说了目标类型、技术栈或现有项目。
2. 再看仓库文件：`package.json`、`vite.config.*`、`electron.*`、`pom.xml`、`pyproject.toml`、`requirements.txt`、`AGENTS.md`、模块目录。
3. 如果是现有项目增量功能，以项目已有技术栈为准；不要重开后端语言选择。
4. 如果上下文只说明“生成后端/接口/服务端项目”，才进入 Java/Python 选择。
5. 无法确定且会影响产物格式时，最多提 1 个关于 `target_kind` 的澄清问题。

## 记录要求

在 `docs/app-design.md` 和 `docs/contracts/app-contract.yaml` 中记录：

- `target_kind`
- 实现语言、框架和关键模块
- 采用的 guideline 或仓库规范来源
- 是否需要数据库变更
- 契约是否可直接交给后端 `code-generation`

## 下游边界

只有 `project.targetKind` 明确为后端目标（`backend-java` / `backend-python`）的契约（含存量 legacy 旧契约），才允许直接进入后端 `code-generation`。非后端契约是追溯和评审契约，后续实现应按现有项目方式增量编码。
