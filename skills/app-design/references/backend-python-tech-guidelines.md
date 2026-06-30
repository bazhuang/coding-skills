# Python 后端技术规范

本文件提供 Python 后端应用设计阶段的技术约束。仅当用户选择 Python，或现有项目已经明确是 Python 后端时读取并遵守。

## 项目概述

基于 FastAPI 的企业级分层后端项目。

**技术栈**: Python 3.11+ | FastAPI | Pydantic v2 | SQLAlchemy 2.x | Alembic | MySQL 5.7 | Pytest

**推荐工具**: Ruff（格式化与 lint）| mypy（类型检查）| uv 或 Poetry（依赖管理，优先沿用现有项目）

## 项目结构

```
{project}/
├── app/
│   ├── main.py                 # 应用入口
│   ├── api/                    # API Router 层
│   ├── biz/                    # 业务编排层
│   ├── service/                # 领域服务层
│   ├── repository/             # 数据访问层
│   ├── schemas/                # Pydantic 请求/响应模型
│   ├── models/                 # SQLAlchemy ORM 模型
│   ├── core/                   # 配置、鉴权、异常、日志
│   └── db/                     # session、metadata、连接管理
├── migrations/                 # Alembic 迁移
└── tests/
```

**约束**：仅在上述应用目录、迁移目录和测试目录中设计或编写后端代码。

## 分层架构

**调用链**: `main -> api -> biz -> service -> repository -> db`

| 层次 | 目录 | 命名 | 返回类型 | 说明 |
|------|------|------|----------|------|
| **API Router** | `app/api/` | `{object}_router.py` | Pydantic Response Schema | 路由、鉴权、参数接收，默认 POST |
| **Biz** | `app/biz/` | `{object}_biz.py` | Pydantic Schema 或 Result | 业务编排、事务边界、跨对象校验 |
| **Service** | `app/service/` | `{object}_service.py` | DTO/Schema/领域值 | 具体业务逻辑、计算规则 |
| **Repository** | `app/repository/` | `{object}_repository.py` | ORM Model 或数据行 | 数据访问，封装 SQLAlchemy 查询 |
| **Schemas** | `app/schemas/` | `{object}_schema.py` | Pydantic BaseModel | 请求、响应、内部 DTO |
| **Models** | `app/models/` | `{object}_model.py` | SQLAlchemy Declarative Model | 表结构映射 |

**架构关键原则**：
- API 层只做协议适配、认证、输入输出转换，不直接访问 Repository
- Biz 层负责业务编排、事务控制、跨实体一致性校验
- Service 层负责单对象业务逻辑和可复用计算
- Repository 层只负责数据访问，不写业务规则
- 数据转换方向：`Model -> Schema/DTO -> Response`；API/Biz 层禁止直接暴露 ORM Model
- 函数、变量、模块使用 `snake_case`；类名使用 `PascalCase`
- 所有公共函数必须带类型标注；复杂返回结构必须定义 Pydantic Schema

## FastAPI 应用约束

- 应用入口为 `app/main.py`，集中注册 routers、异常处理、生命周期事件
- API 使用 `APIRouter` 分文件组织，URL 使用小写连字符，如 `/api/gas-contract/create`
- 所有接口默认使用 POST；如确需 GET，必须在设计文档中说明原因
- 响应统一使用项目约定的 Result 包装；若现有项目没有约定，设计 `Result[T]`，包含 `success`、`code`、`message`、`data`
- 统一通过依赖注入获取当前用户、数据库会话和权限上下文
- 每个写操作必须记录操作人：创建时写入 `create_by`，更新时写入 `update_by`

## 认证与鉴权

- 每个 API 路由必须声明鉴权依赖，例如 `Depends(require_auth)` 或项目已有鉴权依赖
- 当前用户信息通过统一上下文或依赖获取，不允许在业务层解析原始 token
- 权限校验失败使用统一异常和错误码，不在各路由中散落返回结构

## Repository 与数据库规范

- SQLAlchemy 使用 2.x 风格；优先使用显式 Session，不在全局保存会话
- 事务边界放在 Biz 层；Repository 不主动提交事务，除非项目已有明确模式
- Model 字段必须与 `docs/contracts/db-schema.sql` 一致
- 时间字段与数据库保持 `datetime`
- 小数使用 `Decimal`，禁止使用 `float`
- 布尔/状态字段使用 `int`/`tinyint` 对应，字段名保持 `is_xxx`
- 禁止使用外键约束，关联完整性由应用层保证
- 禁止使用 MySQL 保留字作为字段名（如 `desc`、`range`、`match`）

## 配置和环境

- 配置集中在 `app/core/config.py`，使用 Pydantic Settings 或项目已有配置机制
- 支持 FAT、UAT、PROD 环境；数据库连接、鉴权密钥、消息队列等敏感配置必须来自环境变量或配置中心
- 不在代码中硬编码数据库连接、密钥或账号

## 单元测试规范

- 测试目录为 `tests/`，文件名 `test_{module}.py`
- 使用 Pytest；API 测试使用 FastAPI `TestClient` 或 `httpx.AsyncClient`
- 写数据库的测试必须使用事务回滚或隔离测试库
- Biz/Service 测试优先覆盖规则、SOP 编排和边界条件
- Repository 测试只验证 SQL 行为，不承载业务规则断言

## 对应用设计的影响

选择 Python 后，以下决策已被技术栈固定，**不需要**再作为可选方案提出：

| 设计维度 | 已确定方案 |
|---------|------------|
| 框架 | FastAPI，不可替换 |
| 数据校验 | Pydantic v2，不可替换 |
| ORM/迁移 | SQLAlchemy 2.x + Alembic，不可替换 |
| 数据库 | MySQL 5.7，不可替换 |
| 分层架构 | API Router -> Biz -> Service -> Repository -> DB，不可替换 |
| 接口风格 | REST POST 为主，统一 Result 包装 |
| 测试 | Pytest，不可替换 |

因此，应用设计的 2-3 种方案应聚焦于**业务逻辑的分解方式、模块划分、数据流设计**等层面，而非技术选型层面。
