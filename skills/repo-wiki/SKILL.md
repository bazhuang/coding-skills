---
name: repo-wiki
description: "当用户要求为代码仓库生成项目文档、项目百科、技术文档站点时使用。从本地仓库的文件树和 README 出发，先让 LLM 生成文档目录结构（XML），解析后逐页生成包含 Mermaid 图表、源码引用、数据表格的 Markdown 内容，最终输出到 docs/wiki/ 目录。所有内容和文件名均使用中文。纯文档型，独立可用，无鉴权、无模型配置。"
---

# 仓库文档生成

为本地代码仓库生成结构化、带图表和源码引用的技术文档，输出到 `docs/wiki/` 目录。

参照 DeepWiki-Open 项目移植，去掉鉴权和模型配置，仅保留文档生成核心流程。由执行者（LLM agent）按提示词生成文档结构和页面内容，脚本负责文件扫描、XML 解析、Markdown 导出。

## 写文件规则（全局约束）

本 skill 运行过程中需要写多个临时文件（XML、JSON、Markdown）。所有临时文件的写入必须通过 shell 命令完成，禁止使用 Write 工具。

Write 工具在目标文件已存在时会报错 "File has not been read yet"，导致流程中断。shell 命令无此限制。

写入方式统一用 heredoc：

```bash
cat > /tmp/wiki_structure.xml << 'WIKI_EOF'
（文件内容）
WIKI_EOF
```

注意：heredoc 的结束标记（如 `WIKI_EOF`）必须独占一行、顶格无缩进。如果内容中包含 `EOF` 字样，换一个不会冲突的标记名。

以下文件一律用此方式写入：
- `/tmp/wiki_structure.xml`（步骤 3 生成的 XML 结构）
- `/tmp/wiki_pages/<page_id>.md`（步骤 4 每页生成的 Markdown 内容）
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
| 生成文档目录结构时的提示词模板和 XML 格式 | `references/structure-prompt.md` |
| 生成单个 文档页面内容时的提示词模板和内容结构 | `references/page-content-prompt.md` |

只读取当前任务需要的 reference，不要一次性加载所有细节。

脚本：用于文件树扫描、XML 解析、Markdown 导出，见 `scripts/`。

## 工作流程

### 0. 清理临时文件

```bash
rm -rf /tmp/wiki_scan.json /tmp/wiki_api_entries.json /tmp/wiki_structure.xml /tmp/wiki_structure.json /tmp/wiki_pages/
mkdir -p /tmp/wiki_pages
# 同时清理上一次的输出目录，避免残留文件
rm -rf docs/wiki
```

每次执行前必须清理上一次的临时文件，避免残留文件导致写入冲突。

### 1. 扫描仓库文件树和 README

```bash
python3 skills/repo-wiki/scripts/scan_repo.py <仓库路径> --output /tmp/wiki_scan.json
```

脚本会遍历仓库目录（排除 .git、node_modules、__pycache__ 等），输出 JSON：
- `file_tree`：排序后的文件路径列表（每行一个）
- `readme`：README.md 内容（如果存在）

### 2. 扫描 API 入口

```bash
python3 skills/repo-wiki/scripts/scan_api_entries.py <仓库路径> --output /tmp/wiki_api_entries.json
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

### 3. 生成文档目录结构

读取 `references/structure-prompt.md`，将其中提示词的占位符替换：
- `{REPO_NAME}` -> 仓库名称
- `{FILE_TREE}` -> scan_repo.py 输出的 file_tree
- `{README}` -> scan_repo.py 输出的 readme

根据用户需求选择模式：
- **全面模式**（默认）：8-12 个页面，按章节组织（概览、架构、核心功能、数据管理、前端、后端、部署等）
- **精简模式**：4-6 个页面，扁平结构

按提示词生成 XML 格式的文档目录结构，按「写文件规则」用 shell heredoc 写入 `/tmp/wiki_structure.xml`，然后解析：

```bash
python3 skills/repo-wiki/scripts/parse_structure.py /tmp/wiki_structure.xml --output /tmp/wiki_structure.json
```

解析后得到 JSON，包含：
- `title`：项目总标题
- `description`：仓库描述
- `pages`：页面列表，每个页面含 id、title、description、importance、filePaths、relatedPages
- `sections`：章节列表（全面模式），含 id、title、pages（page_id 列表）、subsections
- `rootSections`：顶层章节 id 列表

### 4. 逐页生成内容

读取 `references/page-content-prompt.md`，按 importance 分批生成：

**第一批（串行）：importance 为 high 的页面**
- 核心页面，通常 2-4 页，串行生成确保质量和一致性
- 每页生成后按「写文件规则」用 shell heredoc 写入 `/tmp/wiki_pages/<page_id>.md`

**第二批（可并行）：importance 为 medium 和 low 的页面**
- 派发子 agent 并行生成，每个子 agent 负责一页
- 各子 agent 独立读取提示词模板和源文件，生成 Markdown 后按「写文件规则」用 shell heredoc 写入 `/tmp/wiki_pages/<page_id>.md`
- 页面间通过 `relatedPages` 做链接，无内容依赖，并行安全

如果项目较小（4-6 页），全部串行即可，无需并行。

每页生成流程：
1. 从 structure.json 中取页面信息（title、description、filePaths）
2. 将提示词中的占位符替换：
   - `{PAGE_TITLE}` -> 页面标题
   - `{PAGE_DESCRIPTION}` -> 页面描述
   - `{FILE_PATHS}` -> 源文件列表（`- 文件路径` 格式）
   - `{FILE_PATHS_LINKED}` -> 可点击链接列表（`- [文件路径](../../文件路径)`）
3. 读取相关源文件内容，按提示词生成 Markdown 内容
4. 按「写文件规则」用 shell heredoc 写入 `/tmp/wiki_pages/<page_id>.md`

每页内容要求：
- 总结后以 `<details>` 块列出相关源文件（至少 5 个，放在页面底部）
- H1 标题（`# 页面标题`）
- 页内目录（导出脚本自动生成，列出本页 H2/H3 标题的锚点链接）
- 简介（1-2 段）
- 详细章节（H2/H3）
- Mermaid 图表（flowchart TD、sequenceDiagram、classDiagram 等，纵向布局）
- Markdown 表格汇总信息
- 源文件引用（`来源：[filename:行号]()` 格式，至少引用 5 个不同文件）
- 总结段落

全部使用中文。

### 5. 导出到 docs/wiki/

```bash
python3 skills/repo-wiki/scripts/export_wiki.py /tmp/wiki_structure.json /tmp/wiki_pages/ --output docs/wiki
```

脚本会：
- 将概览页面合并项目标题、描述、目录导航和概览正文为一个文件
- 为其余每个页面生成 `<中文标题>.md` 文件
- 全面模式下按章节组织目录

### 6. 验证产物

检查 `docs/wiki/` 目录：
- 概览页面 `.md` 存在且包含目录导航和所有页面链接
- 每个页面的 `.md` 文件存在
- 文件名均为中文
- 内容包含 Mermaid 图表、源码引用等关键元素

### 7. 清理临时文件

```bash
rm -rf /tmp/wiki_scan.json /tmp/wiki_api_entries.json /tmp/wiki_structure.xml /tmp/wiki_structure.json /tmp/wiki_pages/
```

验证产物无误后清理所有临时文件，保持工作目录干净。

## 模式说明

| 模式 | 页面数 | 目录结构 | 适用场景 |
|---|---|---|---|
| 全面模式 | 8-12 | 按章节组织（sections + subsections） | 需要完整文档覆盖的中大型项目 |
| 精简模式 | 4-6 | 扁平结构（仅 pages） | 快速概览或小型项目 |

默认使用全面模式。用户明确要求"精简"或项目较小时切换到精简模式。

## 脚本一览

| 脚本 | 作用 |
|---|---|
| `scripts/scan_repo.py` | 扫描仓库目录，输出文件树 + README |
| `scripts/scan_api_entries.py` | 扫描 API 入口（Controller/Router/Handler），输出端点列表 |
| `scripts/parse_structure.py` | 解析 XML 格式的 文档目录结构，输出 JSON |
| `scripts/export_wiki.py` | 将结构 JSON + 页面内容导出为 docs/wiki/ 下的 Markdown 文件 |

所有脚本仅使用 Python 标准库，无第三方依赖。
