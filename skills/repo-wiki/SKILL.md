---
name: repo-wiki
description: "当用户要求为代码仓库生成项目文档、项目百科、技术文档站点时使用。从本地仓库的文件树和 README 出发，先让 LLM 生成文档目录结构（XML），解析后逐页生成包含 Mermaid 图表、源码引用、数据表格的 Markdown 内容，最终输出到 docs/wiki/ 目录。所有内容和文件名均使用中文。纯文档型，独立可用，无鉴权、无模型配置。"
---

# 仓库文档生成

为本地代码仓库生成结构化、带图表和源码引用的技术文档，输出到 `docs/wiki/` 目录。

纯文档型，独立可用，无鉴权、无模型配置。由执行者（LLM agent）按提示词生成文档结构和页面内容，脚本负责文件扫描、XML 解析、Markdown 导出。

## 写文件规则（全局约束）

本 skill 运行过程中需要写多个临时文件（XML、Markdown）。统一用 Write 工具写入，跨平台无 shell 依赖。

目标文件已存在时，Write 工具会要求先 Read 再覆盖。两种处理方式任选其一：
- 先用 `rm -f <文件路径>` 删除，再 Write
- 先 Read 该文件，再 Write 覆盖

写入子目录前，若目录可能不存在，用 `mkdir -p <目录>` 先创建（脚本自身已对 `--output` 做了建目录兜底，这里只针对执行者主动写的文件）。

以下文件一律用 Write 工具写入：
- `docs/tmp/wiki_structure.xml`（步骤 3 生成的 XML 结构）
- `docs/wiki/<章节子目录>/<中文标题>.md`（步骤 4 生成的各页面）
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

脚本优先使用 `git ls-files` 构建源码清单（避免扫描生成物和缓存），非 Git 仓库回退到目录遍历。默认排除 Wiki 输出目录（`docs/wiki`、`.qoder/repowiki` 等）、构建缓存、敏感文件（`.env`、密钥、证书），输出 JSON：
- `file_tree`：排序后的文件路径列表（每行一个，正斜杠分隔）
- `readme`：根 README 内容（按确定性优先级选择，不依赖遍历顺序）
- `git_commit` / `git_hash`：当前仓库的 git commit hash（`git_hash` 为向后兼容别名）
- `branch`：Git 分支名
- `dirty`：工作区是否有未提交修改
- `scan_mode`：`git`（使用 git ls-files）或 `walk`（回退到目录遍历）
- `file_hashes`：每个文件的内容 hash（SHA-256 前 16 位），用于增量更新判断
- `excluded_paths`：被排除的目录/文件列表（含排除原因）
- `sensitive_file_count`：被排除的敏感文件数量（内容不进入任何产物）
- `repo_path`：仓库绝对路径

可选参数：`--allow-dir`（重新纳入被排除的目录）、`--allow-file`（按 glob 重新纳入文件）、`--symlinks {skip,internal-only,follow}`（默认 `internal-only`，带循环检测）、`--include-untracked`（纳入未跟踪但未忽略的文件）。排除规则可通过 `references/scan-excludes.json` 配置。

更新状态文件：`scan_repo.status=complete`，`scan_repo.output=docs/tmp/wiki_scan.json`。

### 2. 扫描 API 入口

```bash
python3 skills/repo-wiki/scripts/scan_api_entries.py <仓库路径> --output docs/tmp/wiki_api_entries.json --scan docs/tmp/wiki_scan.json
```

脚本按文件语言分派框架正则（Java 只扫 Spring/Feign/JMS；Python 只扫 FastAPI/Celery；Go 只扫 Gin 等），在匹配前剥离注释和字符串字面量，避免误报。输出 JSON 含入口类型分类：
- `entries`：全部入口列表，每条含 `type`（`inbound_http` / `outbound_http_client` / `message_consumer` / `message_producer` / `scheduled_job` / `event_listener`）、file、line、framework、method（HTTP 类）、route（HTTP 类，Spring 自动合并类级+方法级路径）、symbol
- `api_entries`：向后兼容字段，仅含 `inbound_http` 类型入口（供 `{API_ENTRIES}` 占位符使用）
- `controllers`：控制器类声明列表
- `summary`：`by_type`（按类型统计）、`by_framework`（按框架统计）、`languages_scanned`、`total_endpoints`（向后兼容）

将 `api_entries`（入站 HTTP 接口）格式化为文本（每行一条 `METHOD route -> file:line`），填入结构提示词的 `{API_ENTRIES}` 占位符。

脚本已内置 MQ、定时任务和事件监听器的识别（`@RabbitListener`、`@Scheduled`、`@EventListener`、Celery `@task` 等）。如果 `entries` 中已有非 HTTP 类型入口，可直接在结构生成时引用，无需再手动用 `rg` 补充。如果项目确实没有外部入口（纯库项目），`{API_ENTRIES}` 填"无 API 入口"即可。

更新状态文件：`scan_api.status=complete`，`scan_api.output=docs/tmp/wiki_api_entries.json`。

### 2.5 扫描模块结构（检测多模块项目）

```bash
python3 skills/repo-wiki/scripts/scan_modules.py <仓库路径> --output docs/tmp/wiki_modules.json --scan docs/tmp/wiki_scan.json
```

脚本按构建系统声明（Maven/Gradle/Cargo/go.work/npm workspaces/pnpm/Lerna/Nx）识别模块边界，并计算模块间依赖、运行角色和部署属性，输出模块树 JSON：
- `multi_module`：是否多模块项目
- `build_system`：检测到的构建系统
- `module_count` / `leaf_count`：模块数 / 叶子模块数
- `modules`：模块树，每个模块含：
  - 基础字段：`id`、`title`、`type`（aggregate/leaf）、`scope`、`children`、`parent`、`own_file_count`、`recursive_file_count`、`large`
  - **`depends_on`**：依赖的其他模块 ID 列表（从 Maven `<dependency>` / Gradle `project()` / npm `dependencies` 跨模块引用中计算）
  - **`runtime_role`**：`service` / `library` / `aggregator` / `cli` / `worker` / `unknown`
  - **`is_deployable`**：是否有可执行的部署物（Spring Boot fat jar / npm start / Go main 等）
  - **`is_placeholder`**：是否为空模块（无源码、无测试、无入口）
  - **`entry_points`**：启动入口（`@SpringBootApplication` 类 FQN / `package.json` main / `__main__.py` / `func main()` / `src/main.rs`）
  - **`packaging`**：`jar` / `pom` / `war` / `node-app` / `go-binary` 等
  - **`source_file_count`** / **`test_file_count`**：源码/测试文件数

更新状态文件：`scan_modules.status=complete`，`scan_modules.output=docs/tmp/wiki_modules.json`。

**深度模式判定与确认（关键）**：读取 `wiki_modules.json`：

- `multi_module == false` → 项目不是多模块，继续步骤 3，按全面模式或精简模式生成（不填 `{MODULES}` 占位符）。
- `multi_module == true` → 向用户报告并**等待显式确认**：

  > 检测到 N 个模块（构建系统：X，其中叶子模块 M 个）。这是一个多模块项目，建议使用**深度模式**：预计生成约 80-150 页，目录分 3 层（章节 → 模块组 → 模块页），全量生成约需 30-60 分钟。是否进入深度模式？
  >
  > - 确认深度模式 → 生成最细粒度的模块级文档
  > - 否 → 使用全面模式（15-25 页，更快）

  - 用户**确认深度模式** → 将 `wiki_modules.json` 的 `modules` 渲染为文本（用 `--format text` 或自行格式化为 `id | title | type | scope | children`），填入 structure-prompt 的 `{MODULES}` 占位符；状态文件记 `mode=deep`；进入步骤 3 的深度模式分支。
  - 用户**拒绝** → 回退全面模式，`{MODULES}` 填空，`mode=full`。

**不要自动进入深度模式**——必须用户明确同意。深度模式成本高（页数多、耗时长），误触发会浪费大量资源。

脚本识别的模块边界是初筛结果，**执行者可在结构生成阶段修正**：若发现某些模块划分不合理（过大、过碎、跨域），可在生成 XML 时调整章节/页面的组织方式。模块树是骨架建议，不是硬约束。

### 2.8 构建统一事实层

```bash
python3 skills/repo-wiki/scripts/build_facts.py --scan docs/tmp/wiki_scan.json --api docs/tmp/wiki_api_entries.json --modules docs/tmp/wiki_modules.json --output .repo-wiki/wiki_facts.json
```

脚本合并仓库扫描、接口扫描、模块扫描和仓库规则文件（AGENTS.md 等），输出 `.repo-wiki/wiki_facts.json`。每条事实带稳定 ID、类型（observed/repository_rule/inferred）、证据和置信度。结构生成和页面生成消费此文件而非原始扫描结果，确保关键架构结论只定义一次且可追溯。

输出 JSON 含：
- `schema_version`：1
- `repository`：路径/分支/提交/dirty
- `build`：构建系统、是否多模块
- `facts`：事实列表，每条含 id/type/category/value/evidence/confidence
- `facts_hash`：事实层确定性 hash（写入 meta.yaml v2 的 generator.facts_hash）
- `conflicts`：冲突事实列表（同 ID 不同 value）
- `summary`：按类型/分类统计

**关键原则**：结构生成（步骤 3）和页面生成（步骤 4）以事实层为依据，不直接在原始扫描结果之间自由推断。页面生成中新增的推断应回写为 `inferred` 类型，不能伪装为 observed。完整 schema 见 `references/facts-schema.md`。

更新状态文件：新增 `build_facts` 步骤，`status=complete`，`output=.repo-wiki/wiki_facts.json`。

### 3. 生成文档目录结构

读取 `references/structure-prompt.md`，将其中提示词的占位符替换：
- `{REPO_NAME}` -> 仓库名称
- `{FILE_TREE}` -> scan_repo.py 输出的 file_tree
- `{README}` -> scan_repo.py 输出的 readme
- `{API_ENTRIES}` -> scan_api_entries.py 格式化后的 API 入口列表
- `{MODULES}` -> （仅深度模式）scan_modules.py 渲染的模块树文本；非深度模式填空

根据用户需求选择模式：
- **深度模式**：80-150 个页面，3 层目录（章节 → 模块组 → 模块页）。仅当步骤 2.5 检测到多模块且用户确认后使用。模块详解章节是主体，覆盖大多数叶子模块；其他章节按项目特征从候选清单裁剪。
- **全面模式**（默认）：8-12 个页面（大型项目可上浮至 15-25），按章节组织（概览、架构、核心功能、数据管理、前端、后端、部署等）
- **精简模式**：4-6 个页面，扁平结构

完整 XML 示例见 `references/wiki-structure.example.xml`，生成时参照该示例的格式和填值方式。

按提示词生成 XML 格式的文档目录结构，按「写文件规则」用 Write 工具写入 `docs/tmp/wiki_structure.xml`，然后解析：

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
- 每页生成后按「写文件规则」用 Write 工具直接写入 `docs/wiki/<章节子目录>/<中文标题>.md`
- 全面模式下按章节组织子目录（如 `docs/wiki/系统架构/整体架构.md`）
- 深度模式下按三层目录组织（如 `docs/wiki/模块详解/业务域A/模块A1/概述.md`）
- 精简模式下直接写入 `docs/wiki/<中文标题>.md`
- 每完成一页，更新状态文件中该页面的状态：`status=complete`，`completed_at=<当前时间>`，更新 `completed_count`

**第二批（可并行）：importance 为 medium 和 low 的页面**
- 派发子 agent 并行生成，每个子 agent 负责一页
- **深度模式下按模块组分批**：同一模块组（聚合模块下的叶子模块页）派为一批，批次之间串行，避免一次性派出过多子 agent。模块组内页面并行。
- 各子 agent 独立读取提示词模板和源文件，生成 Markdown 后按「写文件规则」用 Write 工具直接写入 `docs/wiki/<章节子目录>/<中文标题>.md`
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
4. 按「写文件规则」用 Write 工具直接写入 `docs/wiki/<章节子目录>/<中文标题>.md`
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
python3 skills/repo-wiki/scripts/export_wiki.py docs/tmp/wiki_structure.json --output docs/wiki --scan docs/tmp/wiki_scan.json --overview-only [--modules docs/tmp/wiki_modules.json]
```

`--modules` 参数（深度模式提供）：传入步骤 2.5 的模块树，使 meta.yaml 记录模块级 scope 与聚合 hash，支撑模块级增量更新。非深度模式省略此参数。

脚本会：
- 生成概览页面（合并项目标题、描述、目录导航和概览正文）
- 生成 `docs/wiki/meta.yaml`（产物元数据，用于增量更新，参照 `references/meta-yaml-format.md`）。深度模式下 meta.yaml 额外含 `modules` 段（模块 scope、module_hash、归属 pages）

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
python3 skills/repo-wiki/scripts/verify_wiki.py docs/tmp/wiki_structure.json --wiki-dir docs/wiki [--modules docs/tmp/wiki_modules.json]
```

`--modules` 参数（深度模式提供）：启用模块覆盖率软门禁（检查大多数叶子模块是否有对应文档页）。非深度模式省略。

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
| 深度模式 | 80-150 | 3 层（章节 → 模块组 → 模块页） | 多模块项目（Maven/Gradle/monorepo 等），需细粒度模块级文档。**须用户确认** |
| 全面模式 | 8-12（大型项目可至 15-25） | 按章节组织（sections + subsections） | 需要完整文档覆盖的中大型项目 |
| 精简模式 | 4-6 | 扁平结构（仅 pages） | 快速概览或小型项目 |

默认使用全面模式。用户明确要求"精简"或项目较小时切换到精简模式。步骤 2.5 检测到多模块项目时建议深度模式，但需用户显式确认后启用。

## 脚本一览

| 脚本 | 作用 |
|---|---|
| `scripts/scan_repo.py` | Git 感知扫描（`git ls-files` 优先），排除 Wiki 输出/缓存/敏感文件，支持符号链接策略和循环检测，输出文件树 + README + repo_path/branch/git_commit/dirty + file_hashes + excluded_paths |
| `scripts/scan_api_entries.py` | 按语言分派扫描 API 入口，剥离注释防误报，分类入口类型（inbound_http/outbound_http_client/message_consumer/message_producer/scheduled_job/event_listener），Spring 自动合并类级+方法级路径 |
| `scripts/scan_modules.py` | 按构建系统声明识别模块边界，计算 depends_on / runtime_role / is_deployable / is_placeholder / entry_points / source-test 计数，输出增强模块树 |
| `scripts/parse_structure.py` | 解析 XML 格式的 文档目录结构，输出 JSON |
| `scripts/export_wiki.py` | 将结构 JSON + 页面内容导出为 docs/wiki/ 下的 Markdown 文件，生成 meta.yaml 元数据（支持模块级增量） |
| `scripts/verify_wiki.py` | 验证产物：硬门禁（概览页存在、每页文件存在、H1 标题、文件名合法）+ 软门禁（Mermaid 图表数、源文件引用数、表格数、链接有效性、深度模式模块覆盖率） |

所有脚本仅使用 Python 标准库，无第三方依赖。
