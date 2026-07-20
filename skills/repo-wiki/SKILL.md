---
name: repo-wiki
description: "当用户要求为代码仓库生成项目文档、项目百科、技术文档站点时使用。从本地仓库的文件树和 README 出发，先让 LLM 生成文档目录结构（XML），解析后逐页生成包含 Mermaid 图表、源码引用、数据表格的 Markdown 内容，最终输出到 docs/wiki/ 目录。所有内容和文件名均使用中文。纯文档型，独立可用，无鉴权、无模型配置。"
---

# 仓库文档生成

为本地代码仓库生成结构化、带图表和源码引用的技术文档，输出到 `docs/wiki/` 目录。

纯文档型，独立可用，无鉴权、无模型配置。由执行者（LLM agent）按提示词生成文档结构和页面内容，脚本负责文件扫描、XML 解析、Markdown 导出。

## 写文件规则（全局约束）

本 skill 运行过程中需要写多个临时文件（XML、JSON、Markdown）。所有临时文件的写入必须通过 shell 命令完成，禁止使用 Write 工具。

Write 工具在目标文件已存在时会报错 "File has not been read yet"，导致流程中断。shell 命令无此限制。

写入方式统一用 heredoc：

```bash
cat > docs/tmp/wiki_structure.xml << 'WIKI_EOF'
（文件内容）
WIKI_EOF
```

注意：heredoc 的结束标记（如 `WIKI_EOF`）必须独占一行、顶格无缩进。如果内容中包含 `EOF` 字样，换一个不会冲突的标记名。

以下文件一律用此方式写入：
- `docs/tmp/wiki_structure.xml`（步骤 3 生成的 XML 结构）
- 其他所有需要执行者主动创建的临时文件

## 产物

| 产物 | 路径 | 说明 |
|---|---|---|
| 概览页面 | `docs/wiki/<概览标题>.md` | 项目概览 + 目录导航 + 概览正文，合并为一个页面 |
| 文档页面 | `docs/wiki/<页面标题>.md` | 其余每个页面一个文件，中文文件名 |

默认只产出 Markdown。章节结构、提示词模板见 `references/`。

## 必读与按需参考

先读本文件，再按场景读取 references：

| 场景 | 读取 |
|---|---|
| 生成文档目录结构时的提示词模板和 XML 格式 | `references/structure-prompt.md`，完整示例见 `references/wiki-structure.example.xml` |
| 生成单个文档页面内容时的提示词模板和内容结构 | `references/page-content-prompt.md` |
| 读写状态文件、断点恢复、了解各步骤状态闭集值 | `references/state-ledger.md`，格式示例见 `references/wiki-state.example.yaml` |
| 派发子 agent 前加载角色契约（必读/必写/不许做） | `references/agent-contracts.yaml` |
| 验证产物的检查项和软硬门禁判定标准 | `references/verify-checklist.md` |
| 产物元数据 meta.yaml 的格式、增量更新流程、手工编辑保护 | `references/meta-yaml-format.md` |

只读取当前任务需要的 reference，不要一次性加载所有细节。

脚本：用于文件树扫描、XML 解析、Markdown 导出、产物验证，见 `scripts/`。

## 工作流程

### 0. 增量判断 + 清理临时文件

```bash
rm -rf docs/tmp
mkdir -p docs/tmp
```

每次执行前清理 `docs/tmp/` 下的临时文件（扫描结果、中间结构），避免残留文件导致写入冲突。

**注意**：`docs/.wiki-state.yaml`（流程状态文件）不在 `docs/tmp/` 下，不会被清理，用于断点恢复。

**增量更新判断**：检查 `docs/wiki/meta.yaml` 是否存在（参照 `references/meta-yaml-format.md`）：

- **不存在** → 首次运行，全量生成。继续步骤 1。
- **存在** → 读取 meta.yaml，向用户报告上次生成信息（git_hash、generated_at、页面数）。询问用户：
  - **全量重新生成** → `rm -rf docs/wiki`，继续步骤 1 全量流程
  - **增量更新** → 保留 `docs/wiki/` 和 `meta.yaml`，进入增量模式（步骤 1-4 只处理 source_hash 变化的页面）

**断点恢复**：如果 `docs/.wiki-state.yaml` 已存在（上次中断未清理），不要删除它——先读取状态文件，按 `references/state-ledger.md` 的中断恢复决策树从断点继续。格式示例见 `references/wiki-state.example.yaml`。

全新流程时，按 `references/wiki-state.example.yaml` 的格式初始化状态文件，写入 `docs/.wiki-state.yaml`，记录 repo_path、mode、started_at，所有步骤 status 初始为 pending。

### 1. 扫描仓库文件树和 README

```bash
python3 skills/repo-wiki/scripts/scan_repo.py <仓库路径> --output docs/tmp/wiki_scan.json
```

脚本会遍历仓库目录（排除 .git、node_modules、__pycache__ 等），输出 JSON：
- `file_tree`：排序后的文件路径列表（每行一个）
- `readme`：README.md 内容（如果存在）
- `git_hash`：当前仓库的 git commit hash（非 git 仓库为空字符串）
- `file_hashes`：每个文件的内容 hash（SHA-256 前 16 位），用于增量更新判断

更新状态文件：`scan_repo.status=complete`，`scan_repo.output=docs/tmp/wiki_scan.json`。

### 2. 扫描 API 入口

```bash
python3 skills/repo-wiki/scripts/scan_api_entries.py <仓库路径> --output docs/tmp/wiki_api_entries.json
```

脚本用正则扫描常见框架的 API 入口（Spring/FastAPI/Django/Express/Gin/.NET/Rails），输出 JSON：
- `api_entries`：API 端点列表，每条含 file、line、method（GET/POST/...）、route、framework
- `controllers`：控制器类声明列表
- `summary`：端点数、控制器数、检测到的框架

将 API 入口列表格式化为文本（每行一条 `METHOD route -> file:line`），填入结构提示词的 `{API_ENTRIES}` 占位符。

兜底：如果脚本扫描结果为空（`summary.total_endpoints == 0`），说明项目不使用主流框架或非 API 类项目。此时执行者自行用 `rg` 搜索以下信号补充识别：
- 命令行入口：`argparse`、`click`、`sys.argv`、`commander`、`cobra`
- 消息队列消费者：`@RabbitListener`、`@KafkaListener`、`consumer`、`subscribe`
- 定时任务：`@Scheduled`、`@cron`、`celery`、`scheduler`
- 事件处理：`@EventHandler`、`@EventListener`、`emitter`
- RPC 服务：`grpc`、`thrift`、`@Service`

将补充识别到的入口同样格式化后填入 `{API_ENTRIES}`。如果项目确实没有外部入口（纯库项目），`{API_ENTRIES}` 填"无 API 入口"即可。

更新状态文件：`scan_api.status=complete`，`scan_api.output=docs/tmp/wiki_api_entries.json`。

### 3. 生成文档目录结构

读取 `references/structure-prompt.md`，将其中提示词的占位符替换：
- `{REPO_NAME}` -> 仓库名称
- `{FILE_TREE}` -> scan_repo.py 输出的 file_tree
- `{README}` -> scan_repo.py 输出的 readme

根据用户需求选择模式：
- **全面模式**（默认）：8-12 个页面，按章节组织（概览、架构、核心功能、数据管理、前端、后端、部署等）
- **精简模式**：4-6 个页面，扁平结构

完整 XML 示例见 `references/wiki-structure.example.xml`，生成时参照该示例的格式和填值方式。

按提示词生成 XML 格式的文档目录结构，按「写文件规则」用 shell heredoc 写入 `docs/tmp/wiki_structure.xml`，然后解析：

```bash
python3 skills/repo-wiki/scripts/parse_structure.py docs/tmp/wiki_structure.xml --output docs/tmp/wiki_structure.json
```

解析后得到 JSON，包含：
- `title`：项目总标题
- `description`：仓库描述
- `pages`：页面列表，每个页面含 id、title、description、importance、filePaths、relatedPages
- `sections`：章节列表（全面模式），含 id、title、pages（page_id 列表）、subsections
- `rootSections`：顶层章节 id 列表

更新状态文件：`generate_structure.status=complete`，`generate_structure.output=docs/tmp/wiki_structure.json`。

### 4. 逐页生成内容（实时写入 docs/wiki/）

读取 `references/page-content-prompt.md`，按 importance 分批生成。每生成一个页面，立刻写入到 `docs/wiki/` 对应位置，用户可以实时看到进度。

**增量模式判断**：如果步骤 0 选择了增量更新模式，需要判断哪些页面需要重新生成：

1. 读取 `docs/wiki/meta.yaml`，获取每个页面的 `source_hash`
2. 从 `docs/tmp/wiki_scan.json` 获取当前文件的 `file_hashes`
3. 对每个页面，计算其 `filePaths` 中所有文件的组合 hash
4. 比较新旧 hash：
   - **hash 相同** → 源文件未变化，跳过该页面（保留原有内容），状态标记为 `skipped`
   - **hash 不同** → 源文件已变化，需要重新生成该页面
5. 只重新生成 hash 变化的页面

**派发子 agent 前**：先读取 `references/agent-contracts.yaml`，按其中 `page_generator` 角色的契约约束子 agent 的必读/必写/不许做。

更新状态文件：`generate_pages.status=in_progress`，初始化 `pages` 列表，为每个页面创建状态记录（包含 id、title、source_hash、output_file）。

**第一批（串行）：importance 为 high 的页面（除概览页外）**
- 核心页面，通常 2-4 页，串行生成确保质量和一致性
- 每页生成后按「写文件规则」用 shell heredoc 直接写入 `docs/wiki/<章节子目录>/<中文标题>.md`
- 全面模式下按章节组织子目录（如 `docs/wiki/系统架构/整体架构.md`）
- 精简模式下直接写入 `docs/wiki/<中文标题>.md`
- 每完成一页，更新状态文件中该页面的状态：`status=complete`，`completed_at=<当前时间>`，更新 `completed_count`

**第二批（可并行）：importance 为 medium 和 low 的页面**
- 派发子 agent 并行生成，每个子 agent 负责一页
- 各子 agent 独立读取提示词模板和源文件，生成 Markdown 后按「写文件规则」用 shell heredoc 直接写入 `docs/wiki/<章节子目录>/<中文标题>.md`
- 页面间通过 `relatedPages` 做链接，无内容依赖，并行安全
- 每完成一页，更新状态文件中该页面的状态：`status=complete`，`completed_at=<当前时间>`，更新 `completed_count`

如果项目较小（4-6 页），全部串行即可，无需并行。

每页生成流程：
1. 从 structure.json 中取页面信息（title、description、filePaths）
2. 将提示词中的占位符替换：
   - `{PAGE_TITLE}` -> 页面标题
   - `{PAGE_DESCRIPTION}` -> 页面描述
   - `{FILE_PATHS}` -> 源文件列表（`- 文件路径` 格式）
   - `{FILE_PATHS_LINKED}` -> 可点击链接列表（`- [文件路径](../../文件路径)`）
3. 读取相关源文件内容，按提示词生成 Markdown 内容
4. 按「写文件规则」用 shell heredoc 直接写入 `docs/wiki/<章节子目录>/<中文标题>.md`
5. 更新状态文件中该页面的状态

每页内容要求：
- 总结后以 `<details>` 块列出相关源文件（至少 5 个，放在页面底部）
- H1 标题（`# 页面标题`）
- 页内目录（列出本页 H2/H3 标题的锚点链接）
- 简介（1-2 段）
- 详细章节（H2/H3）
- Mermaid 图表（flowchart TD、sequenceDiagram、classDiagram 等，纵向布局）
- Markdown 表格汇总信息
- 源文件引用（`来源：[filename:行号]()` 格式，至少引用 5 个不同文件）
- 总结段落

全部使用中文。

**注意**：概览页面（overview page）暂不生成，等步骤 5 统一生成（因为需要包含目录导航，列出所有页面）。

全部页面生成完成后，更新状态文件：`generate_pages.status=complete`。

### 5. 生成概览页面 + meta.yaml

所有页面生成完成后，生成概览页面和元数据：

```bash
python3 skills/repo-wiki/scripts/export_wiki.py docs/tmp/wiki_structure.json --output docs/wiki --scan docs/tmp/wiki_scan.json --overview-only
```

脚本会：
- 生成概览页面（合并项目标题、描述、目录导航和概览正文）
- 生成 `docs/wiki/meta.yaml`（产物元数据，用于增量更新，参照 `references/meta-yaml-format.md`）

**注意**：步骤 4 已经生成的普通页面不会被覆盖，只有概览页面和 meta.yaml 是这一步新生成的。

**增量模式行为**：
- 读取已有的 `docs/wiki/meta.yaml`，比较每个页面的 `source_hash`
- 只重新生成 `source_hash` 发生变化的页面
- 未变化的页面保留原有文件（包括用户手工编辑的内容）
- 输出日志显示跳过了哪些页面、重新生成了哪些页面

`--scan` 参数提供 scan.json 以获取 git_hash 和 file_hashes，写入 meta.yaml。如果不提供，meta.yaml 中的 hash 信息为空，无法进行增量更新。

更新状态文件：`export.status=complete`。

### 6. 验证产物（门禁脚本）

```bash
python3 skills/repo-wiki/scripts/verify_wiki.py docs/tmp/wiki_structure.json --wiki-dir docs/wiki
```

脚本替代"让 LLM 自己检查"的做法，执行硬门禁（失败即中止）和软门禁（失败留警告）检查。检查项和判定标准见 `references/verify-checklist.md`。

- 硬门禁失败（exit 1）：必须修复问题后重新导出（回到步骤 5）
- 软门禁警告（exit 0）：不阻断流程，但应在产物中关注

更新状态文件：`verify.status=complete`，`verify.hard_gates_passed=true/false`，`verify.soft_gates_warnings=[...]`。

### 7. 清理临时文件

```bash
rm -rf docs/tmp
```

验证产物无误后清理 `docs/tmp/` 下的所有临时文件（扫描结果、中间结构、页面草稿），保持工作目录干净。

**注意**：`docs/.wiki-state.yaml`（流程状态文件）不在此处清理，保留用于下次断点恢复。如需完全重置，手动删除该文件即可。

## 模式说明

| 模式 | 页面数 | 目录结构 | 适用场景 |
|---|---|---|---|
| 全面模式 | 8-12 | 按章节组织（sections + subsections） | 需要完整文档覆盖的中大型项目 |
| 精简模式 | 4-6 | 扁平结构（仅 pages） | 快速概览或小型项目 |

默认使用全面模式。用户明确要求"精简"或项目较小时切换到精简模式。

## 脚本一览

| 脚本 | 作用 |
|---|---|
| `scripts/scan_repo.py` | 扫描仓库目录，输出文件树 + README + git_hash + file_hashes（用于增量更新） |
| `scripts/scan_api_entries.py` | 扫描 API 入口（Controller/Router/Handler），输出端点列表 |
| `scripts/parse_structure.py` | 解析 XML 格式的 文档目录结构，输出 JSON |
| `scripts/export_wiki.py` | 将结构 JSON + 页面内容导出为 docs/wiki/ 下的 Markdown 文件，生成 meta.yaml 元数据 |
| `scripts/verify_wiki.py` | 验证产物：硬门禁（概览页存在、每页文件存在、H1 标题、文件名合法）+ 软门禁（Mermaid 图表数、源文件引用数、表格数、链接有效性） |

所有脚本仅使用 Python 标准库，无第三方依赖。
