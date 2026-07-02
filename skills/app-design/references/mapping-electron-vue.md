# Electron/Vue 映射规则

用于 `target_kind = desktop-electron-feature`，将本体对象、行为、规则、SOP 映射到 Electron + Vue + TypeScript 的应用表面。

## 应用表面

| 表面 | 典型职责 | 契约字段 |
|---|---|---|
| Vue Component | 触发用户动作、展示状态、处理组件生命周期 | `surfaces.renderer` 或 `surfaces.component` |
| Renderer service/composable/store | 管理 renderer 侧状态、轮询、请求编排 | `surfaces.renderer` |
| Preload API | 暴露安全的 `window.electron.*` 能力 | `surfaces.preload` |
| IPC channel | renderer 与 main 的边界契约 | `surfaces.ipc` |
| Main helper/service | 调用系统能力、外部 API、本地存储 | `surfaces.main` |
| External API | 外部认证、业务或平台服务 | `surfaces.external` |

## 行为映射

| 本体行为 | 默认调用链 |
|---|---|
| CREATE | component action -> renderer service -> preload -> IPC -> main helper |
| QUERY | component polling/query -> renderer service -> preload -> IPC -> main helper/external API |
| UPDATE | component action -> renderer service -> preload -> IPC -> main helper |
| DELETE/CANCEL | component cleanup/cancel -> renderer service -> preload -> IPC -> main helper |
| DERIVE | main/helper 或 renderer orchestration 将一个对象结果转换为下游对象输入 |

## 设计要求

- IPC 名称、preload 方法、renderer service 方法必须在契约中逐项列出，避免只写“调用登录接口”这类不可追溯描述。
- 外部系统权威对象、短生命周期票据、验证码、一次性授权态默认不建本地业务表；在对象的 `persistence` 写为 `external-service`、`transient-memory`、`existing-local-kv` 或 `none`。
- 涉及本地 KV 时，写明 key 名、value shape、读写时机、清理策略和兼容旧值策略。
- 涉及轮询或超时，写明启动条件、间隔、终止条件、失败重试、窗口关闭/组件卸载清理。
- 规则位置可以使用 `Module.method()`、`Component.method()`、`file:function` 或 `ipc:channel`。
- SOP 的 `calls` 按实际跨表面调用链书写，例如 `LoginPanel.startQrLogin -> authService.startQrLogin -> electron.auth.startQrLogin -> auth:startQrLogin -> startEnnewQrLogin -> POST /...`。

## 文档视图

`docs/app-design.md` 至少包含：

1. 桌面端模块边界：renderer、preload、main、external service。
2. 行为到应用表面映射表。
3. IPC/preload 契约表。
4. 状态流转、轮询/取消/清理策略。
5. 数据库影响说明；无 DB 变更时说明原因。
6. 当前审批点。
