# 技术栈与项目类型探测

本文件定义从代码信号判断项目类型/语言/框架的启发式，以及各栈对应的项目大纲维度提取入口。工作流程步骤 1（探测技术栈）及后续按栈提取时读取。

## 通用探测信号

按以下信号判断技术栈，优先级从高到低：

| 信号类型 | 文件/模式 | 判定 |
|---|---|---|
| 构建文件 | `pom.xml` / `build.gradle` / `pyproject.toml` / `requirements.txt` / `package.json` / `go.mod` | 语言与依赖管理工具 |
| 框架声明 | 构建文件依赖、`@SpringBootApplication` / `FastAPI()` / `createReactApp` | 框架 |
| 入口声明 | `Application.java` / `app/main.py` / `package.json#main` / `main.go` | 启动入口 |
| 目录约定 | `src/main/java` / `app/api` / `src/renderer` | 分层与项目形态 |
| 配置文件 | `application.properties` / `.env` / `config.yaml` | 数据源、外部依赖 |

多语言混合仓库（如 Java 后端 + Electron 前端）分别探测，项目大纲按子系统分块说明。

## Java / Spring Boot

- **探测**：`pom.xml`（或 `build.gradle`）含 `spring-boot-starter`；启动类 `@SpringBootApplication`。
- **分层**：`web`（`@RestController`）/ `biz` / `service`（`@Service`）/ `dal`（`@Mapper` + XML 或 JPA Repository）。
- **实体**：PO 类（`@TableName`/`@Table`）、MyBatis XML resultMap、JPA `@Entity`。
- **入口**：`@GetMapping`/`@PostMapping` 等映射；`@Scheduled` 定时任务；MQ `@RocketMQMessageListener`/`@RabbitListener`。
- **外部依赖**：`application.properties`/`application.yml` 的 `spring.datasource`、`rocketmq`、`redis`、`oss` 配置。
- **命名空间**：注意 `jakarta` vs `javax`，记入 §2。

## Python / FastAPI

- **探测**：`pyproject.toml`/`requirements.txt` 含 `fastapi`；`app/main.py` 出现 `FastAPI()`。
- **分层**：`api`（APIRouter）/ `biz` / `service` / `repository` / `schemas`(Pydantic) / `models`(SQLAlchemy)。
- **实体**：SQLAlchemy `Base` 子类（`__tablename__`）、Tortoise/Peewee 模型。
- **入口**：APIRouter 路由装饰器（`@router.post`）、CLI（click/typer）、定时任务（apscheduler/celery beat）、MQ consumer（celery `@app.task`）。
- **外部依赖**：`.env`/`config.yaml` 的 `DATABASE_URL`、`REDIS_URL`、`CELERY_BROKER`。

## Node / Electron

- **探测**：`package.json` 含 `electron`；`main`/`preload` 字段；`src/main` vs `src/renderer`。
- **分层**：`main`（主进程）/ `preload`（桥接）/ `renderer`（Vue/React 渲染层）。
- **入口**：`ipcMain.handle`/`ipcRenderer.invoke`（IPC channel）、路由组件、菜单/快捷键注册。
- **持久化**：`electron-store`、`better-sqlite3`、本地 JSON；记入 §2。
- **前端框架**：Vue（`*.vue`）/ React（`*.tsx`），记入 §2；前端组件不作为数据模型，仅作功能入口线索。

## Go

- **探测**：`go.mod`；`main.go` 的 `func main()`。
- **分层**：通常 `cmd`/`internal`/`pkg`；handler（`net/http` 或 gin/echo）/ service / repository。
- **实体**：struct + `db` tag（gorm/sqlx）、migration 文件。
- **入口**：`http.HandleFunc`/gin `router.POST`、cron（robfig/cron）、MQ consumer。
- **外部依赖**：`config.yaml`/env 的 DSN、broker 地址。

## 通用兜底

无法归入上述栈时：

- 按目录结构推断模块边界（顶层目录 = 模块）。
- 按「对外暴露点」找入口：搜索路由/handler/命令注册关键词（`route`/`handler`/`command`/`endpoint`/`controller`）。
- 按数据模型定义文件找实体（搜索 `model`/`entity`/`schema`/`table`/`CREATE TABLE`）。
- 技术栈细节能确定多少写多少，不确定的标 `(推断)` 进 §9。

## 项目规模判定

按以下阈值判定规模，决定是否走分区并行遍历（步骤 1 执行）：

| 规模 | 信号（满足其一） | 遍历策略 |
|---|---|---|
| 小 | 源码文件 ≤ 50 或入口点 ≤ 20 | 单代理一次性枚举 |
| 中 | 源码文件 50–200 或入口点 20–80 | 单代理枚举，按模块分批提取 |
| 大 | 源码文件 > 200 或入口点 > 80，或多模块/monorepo | 分区并行子代理枚举（见 `large-project-traversal.md`） |

入口点数先用下表信号 grep 一次得到近似值。拿不准规模时按"大"处理——分区遍历对中小项目无害，而单代理遍历对大项目必漏。

## 默认排除 glob 清单

枚举/搜索时一律排除以下路径与文件，避免把时间花在生成物、依赖、缓存上（ripgrep `--glob '!pattern'` 或枚举前过滤）：

```
.git/**  .svn/**  node_modules/**  vendor/**  **/vendor/**
target/**  dist/**  build/**  out/**  *.lock  *.class  *.dylib  *.so  *.dll  *.exe
*.log  *.tmp  *.pyc  *.pyo  *.jar  *.war  *.cache  *.min.js  *.min.css
.gradle/**  .idea/**  .vscode/**  .dart_tool/**  .zig-cache/**  CMakeFiles/**
.nuxt-dist/**  __pycache__/**  .next/**  .nuxt/**  coverage/**
**/lib32/**  **/lib64/**  **/private/**  **/Library/**
*.png  *.jpg  *.gif  *.bmp  *.ico  *.svg  *.pdf  *.zip  *.tar  *.rar
```

- 图片/二进制/压缩包不入枚举（除非要找资源依赖）。
- 与「噪音过滤清单」（`reverse-extraction-methodology.md`）配合：排除 glob 在搜索阶段挡掉，噪音过滤在归类阶段挡掉。

## 入口点全量枚举信号

全量枚举（步骤 2）用 grep/搜索确定性信号，不靠逐文件阅读。各栈的入口枚举信号：

| 栈 | 入口类型 | 枚举信号 |
|---|---|---|
| Java/Spring Boot | REST | `@(Get|Post|Put|Delete|Patch|Request)Mapping`、`@RestController` |
| Java/Spring Boot | 定时 | `@Scheduled` |
| Java/Spring Boot | MQ | `@RocketMQMessageListener`、`@RabbitListener`、`@KafkaListener` |
| Python/FastAPI | REST | `@(router|app)\.(get|post|put|delete|patch)\(` |
| Python | CLI | `@click.command`、`@app.command()`（typer） |
| Python | 任务 | `@app.task`（celery）、`@scheduler\.(add_job|cron)` |
| Node/Electron | IPC | `ipcMain\.(handle|on)\(` |
| Node | REST | `(router|app)\.(get|post|put|delete)\(` |
| Go | REST | `(\.HandleFunc|\.GET|\.POST|\.PUT|\.DELETE)\(`、`http.HandleFunc` |
| Go | 定时 | `cron.New`、`robfig/cron` |

实体与模块的枚举信号同理：实体用 `@Entity`/`@TableName`/`__tablename__`/`CREATE TABLE`；模块用顶层包/目录名。枚举得到的入口/实体/模块列表 = §5/§4 的归类基线 + 覆盖率核对的总数。枚举时务必套用「默认排除 glob 清单」并用 `--type` 限定语言，避免命中依赖与生成物。

## 技术栈信号 → 项目大纲章节映射

| 代码信号 | 填入章节 |
|---|---|
| 构建文件、框架声明、命名空间 | §2 架构与技术栈 |
| 顶层目录/包结构、分层约定 | §3 模块结构 |
| ORM 模型/实体类/DDL | §4 数据模型 |
| Controller/Router/IPC/CLI/Job/MQ | §5 功能与接口（含入口） |
| Biz/usecase 编排方法 | §6 核心流程 |
| 计算/校验逻辑 | §7 业务规则 |
| 数据源/MQ/存储/SDK 配置 | §2 架构与技术栈 |

探测完成后，按此映射把信号分拣到对应章节，避免重复提取。
