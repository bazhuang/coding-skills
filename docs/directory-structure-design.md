# repo-wiki 目录结构设计方案

> 基于两篇 Harness Engineering 文章的方法论，结合同项目 `or-workflow-guide`、`app-design` 的成熟 skill 结构，给出 repo-wiki skill 自身目录与生成产物目录的调整方案。

---

## 参考来源

### 两篇文章中的 skill 结构

**应用宝文章**——skill 与知识库的目录结构：
```
llm-knowledge/
├── backend/
│   ├── overview.md                 # 总览层
│   ├── business/
│   │   └── {domain}/
│   │       ├── meta.yaml           # 机器可读索引（注册中心）
│   │       ├── custom/             # 手工沉淀
│   │       └── {service}/
│   │           ├── overview.md     # 8类自动生成文档
│   │           └── custom/
│   └── common/
│       ├── conventions/
│       ├── lib_usage/
│       └── tech/
└── .codebuddy/skills/              # Skill 定义
```
- 用 `meta.yaml` 作为注册中心，记录每个服务的文档状态、git hash
- 文档按"总览→域→服务"三层组织
- 每类文档有固定模板（overview/interfaces/architecture/dependencies/storage/config/pitfalls/log）

**TAB 文章**——11 个 Skill 按职责分组：
- 每个 Skill 是一份"标准操作手册"，按需加载
- 关键理念："Skill 不是 AI 的能力增强，是 AI 的注意力管理"

### 同项目成熟 skill 的结构对照

**`or-workflow-guide`**（最接近两篇文章方法论）：
```
or-workflow-guide/
├── SKILL.md
├── agents/
│   └── roles.yaml                  # 角色契约（模型中立，runtime adapter 映射）
├── references/
│   ├── state-ledger.md             # 状态账本规范
│   ├── sdd-state.example.yaml      # 状态文件示例（人读+机读）
│   ├── spec-change.md              # 规格变更流程
│   ├── spec-versions.example.json  # 规格版本示例
│   ├── runtime-assumptions.md      # 运行时适配
│   └── ...
└── scripts/
    └── sdd_doctor.py               # 体检脚本
```
关键做法：
- `agents/roles.yaml`——角色契约用 YAML，定义 model_slots、artifacts、必读/必写/不许做
- `references/sdd-state.example.yaml`——状态文件用 **example** 形式放在 references，不是模板
- `references/state-ledger.md`——状态文件的规范文档（怎么读、怎么写、字段语义）
- SKILL.md 中引用方式：`"读写 docs/sdd-state.yaml、断点恢复 → 读取 references/state-ledger.md，格式示例见 references/sdd-state.example.yaml"`
- 有 `scripts/sdd_doctor.py` 作为轻量门禁脚本

**`app-design`**：
```
app-design/
├── SKILL.md
└── references/
    ├── app-contract-template.yaml       # 契约模板（YAML）
    ├── app-contract-v2-template.yaml   # v2 契约模板
    ├── app-contract.schema.json        # JSON Schema 校验
    ├── app-contract-v2.schema.json     # v2 Schema 校验
    ├── backend-java-tech-guidelines.md
    ├── backend-python-tech-guidelines.md
    ├── db-design-rules.md
    ├── design-review-checklist.md      # 审查清单
    └── ...
```
关键做法：
- YAML 模板 + JSON Schema 双文件——模板定义结构，Schema 定义约束
- `design-review-checklist.md`——门禁检查清单

**`ontology-modeling`**：
```
ontology-modeling/
├── SKILL.md
├── examples.md                       # 示例（输入→输出对照）
└── references/
    ├── ontology_schema.schema.json   # JSON Schema
    ├── output-contract.md            # 输出契约
    ├── requirements-gate.md          # 准出门禁
    ├── schema-contract.md            # 结构契约
    └── ...
```

### ZCode skill-creator 定义的标准结构

```
my-skill/
├── SKILL.md          (required)
└── (optional)
    ├── references/   (extra docs the model reads on demand)
    ├── scripts/      (helper scripts the model can invoke)
    └── assets/       (templates, fixtures, etc.)
```

---

## 一、skill 自身目录结构

### 1.1 现状

```
repo-wiki/
├── SKILL.md                          # 主入口
├── references/
│   ├── structure-prompt.md            # 生成文档结构的提示词模板
│   ├── page-content-prompt.md         # 生成页面内容的提示词模板
│   └── harness-optimization-analysis.md  # 分析指导文档（非运行时）
└── scripts/
    ├── scan_repo.py                   # 扫描文件树 + README
    ├── scan_api_entries.py            # 扫描 API 入口
    ├── parse_structure.py             # 解析 XML 结构 → JSON
    └── export_wiki.py                 # 导出 Markdown 到 docs/wiki/
```

### 1.2 问题诊断

对照同项目 `or-workflow-guide` 和 `app-design`，当前 repo-wiki 缺少：

| 缺失 | 同项目的做法 | 两篇文章的对应 |
|---|---|---|
| **状态文件** | `or-workflow-guide` 有 `sdd-state.example.yaml` + `state-ledger.md` | TAB: checkpoint 文件 / 应用宝: e2e-state.json |
| **角色契约** | `or-workflow-guide` 有 `agents/roles.yaml` | TAB: 角色契约表 / 应用宝: 专家 Agent 体系 |
| **门禁脚本** | `or-workflow-guide` 有 `sdd_doctor.py` | TAB: 7道门禁 / 应用宝: 15个流程脚本 |
| **产物 schema** | `app-design` 有 `.schema.json` + `template.yaml` | 应用宝: meta.yaml 注册中心 |
| **示例文件** | `or-workflow-guide` 有 `.example.yaml` / `ontology-modeling` 有 `examples.md` | 应用宝: 每类文档有固定模板 |

### 1.3 调整方案

```
repo-wiki/
├── SKILL.md                          # 主入口（更新工作流程，引用各 reference）
├── references/
│   ├── structure-prompt.md            # 已有，不变
│   ├── page-content-prompt.md         # 已有，不变
│   ├── state-ledger.md               # 新增：状态文件规范（怎么读/写/恢复）
│   ├── wiki-state.example.yaml       # 新增：状态文件示例（参照 or-workflow-guide）
│   ├── agent-contracts.yaml          # 新增：子 agent 角色契约（参照 roles.yaml）
│   ├── wiki-structure.example.xml    # 新增：文档结构 XML 示例（参照 examples.md）
│   ├── verify-checklist.md           # 新增：验证检查清单（参照 design-review-checklist.md）
│   ├── harness-optimization-analysis.md  # 已有，非运行时分析文档
│   └── directory-structure-design.md  # 本文档，非运行时设计文档
└── scripts/
    ├── scan_repo.py                   # 已有，不变
    ├── scan_api_entries.py            # 已有，不变
    ├── parse_structure.py             # 已有，不变
    ├── export_wiki.py                 # 已有，需修改：支持按章节分层输出
    └── verify_wiki.py                 # 新增：产物验证门禁脚本（参照 sdd_doctor.py）
```

### 1.4 新增文件详细说明

#### `references/wiki-state.example.yaml`（状态文件示例）

**对应做法**：同 `or-workflow-guide/references/sdd-state.example.yaml`

**为什么用 example 而不是 template**：
- `template` 暗示"复制后填空"，但状态文件是运行时动态写入的
- `example` 的语义是"参照这个格式写"——LLM 看示例理解格式，然后根据实际运行情况写入
- 同项目 `or-workflow-guide` 用的就是 `.example.yaml`

**内容**：
```yaml
# wiki 生成状态文件示例。运行时制品写入 /tmp/wiki-state.yaml。
# 对话压缩后信任状态文件不信任记忆（参照 or-workflow-guide 的 state-ledger 原则）。

repo_path: "/path/to/repo"
mode: "full"                    # full | lite
git_hash: "a1b2c3d4"            # scan_repo.py 输出的当前仓库 commit hash
started_at: "2026-07-14T10:00:00+08:00"

# 阶段状态闭集：pending | in_progress | complete | failed
# complete 当且仅当对应门禁通过
current_step: "page_generation"

steps:
  cleanup:
    status: complete
    timestamp: "2026-07-14T10:00:00+08:00"

  scan_repo:
    status: complete
    output: "/tmp/wiki_scan.json"
    timestamp: "2026-07-14T10:00:15+08:00"

  scan_api:
    status: complete
    output: "/tmp/wiki_api_entries.json"
    timestamp: "2026-07-14T10:00:30+08:00"

  generate_structure:
    status: complete
    output: "/tmp/wiki_structure.json"
    timestamp: "2026-07-14T10:01:00+08:00"
    # 人工确认关卡：结构生成后、页面生成前，需用户确认
    human_review: passed        # passed | requested_changes

  generate_pages:
    status: in_progress
    total_pages: 10
    completed_pages: ["page-1", "page-2", "page-3"]
    pending_pages: ["page-4", "page-5", "page-6", "page-7", "page-8", "page-9", "page-10"]

  export:
    status: pending

  verify:
    status: pending
    # verify_wiki.py 的检查结果写入此处
    hard_gates_passed: null    # true | false
    soft_gates_warnings: []    # 软门禁警告列表

  cleanup_tmp:
    status: pending
```

#### `references/state-ledger.md`（状态文件规范）

**对应做法**：同 `or-workflow-guide/references/state-ledger.md`

**职责**：告诉 LLM "状态文件怎么读、怎么写、什么时候更新、中断后怎么恢复"。状态文件本身是 YAML，但规范是 Markdown——因为规范是给人（和 LLM）读的指导文档，不是机器消费的。

**内容要点**：
- 每个字段的语义和闭集值
- 哪些步骤需要更新状态
- 中断恢复决策树：读取 `current_step` → 检查该步骤状态 → 从断点继续
- "对话压缩后信任状态文件不信任记忆"的原则

#### `references/agent-contracts.yaml`（子 agent 角色契约）

**对应做法**：同 `or-workflow-guide/agents/roles.yaml`

**为什么用 YAML 而不是 Markdown**：
- `or-workflow-guide` 的 `roles.yaml` 就是 YAML 格式
- YAML 的结构化语义（必读/必写/不许做）比 Markdown 表格更清晰
- 同项目已有 `roles.yaml` 的先例

**内容**：
```yaml
schema_version: 1
description: >
  页面生成 Agent 的角色契约。定义子 agent 的输入输出边界，
  确保并行生成时各 agent 职责隔离、互不干扰。

roles:
  page_generator:
    purpose: "为单个文档页面生成 Markdown 内容"
    must_read:
      - references/page-content-prompt.md
      - /tmp/wiki_structure.json（本页 page 定义：title, description, filePaths）
      - filePaths 列表中的源文件内容
    must_write:
      - /tmp/wiki_pages/<page_id>.md   # 且仅此文件
    must_not:
      - 修改 /tmp/wiki_structure.json
      - 修改其他 page 的 .md 文件
      - 修改仓库源代码
      - 跳过 page-content-prompt.md 中的任何格式要求
    output_format: |
      Markdown 格式，包含：H1 标题、页内目录、简介、详细章节、
      Mermaid 图表、Markdown 表格、源文件引用（至少5个不同文件）、
      总结、<details> 相关源文件块。

  # 未来可扩展：structure_generator、overview_generator 等角色
```

#### `references/wiki-structure.example.xml`（文档结构示例）

**对应做法**：同 `ontology-modeling/examples.md`——输入→输出对照

**为什么需要**：
当前 `structure-prompt.md` 只有 XML 格式说明，没有完整的真实示例。LLM 看到完整的示例比看到抽象的格式说明更容易正确生成。应用宝文章也强调"每类文档有固定模板"。

**内容**：一个完整可解析的真实 XML 示例（类似于我之前测试时用的 `/tmp/test_parse.xml`），包含全面模式的 sections/subsections/pages 结构，每个字段都有真实填值。

#### `references/verify-checklist.md`（验证检查清单）

**对应做法**：同 `app-design/references/design-review-checklist.md`

**职责**：作为 `verify_wiki.py` 脚本的文档对照。脚本执行检查，清单文档说明"为什么查这些项、每项的判定标准是什么、软硬门禁的取舍依据"。

**内容要点**：
- 硬门禁项（失败即中止）：概览页存在、每页文件存在、每页 H1、文件名合法
- 软门禁项（失败留警告）：Mermaid 图表数、源文件引用数、表格数、链接有效性
- 软门禁取舍依据（参照 TAB 文章"硬门禁宁少不多"原则）

#### `scripts/verify_wiki.py`（产物验证门禁脚本）

**对应做法**：同 `or-workflow-guide/scripts/sdd_doctor.py`

**对应文章原则**：
- TAB 文章第六章："把'完成'这个词的定义权从 AI 手里拿了回来"
- 应用宝文章："执行步骤必须脚本化"

**职责**：替代当前 SKILL.md 步骤 6"让 LLM 自己检查"的做法。

**检查项**：

| 检查项 | 门禁类型 | 判定逻辑 |
|---|---|---|
| 概览页面存在 | 硬 | docs/wiki/ 下存在含"概览/概述/overview"关键词的 .md |
| structure.json 中每个 page 都有对应 .md | 硬 | 遍历 pages，检查文件是否存在 |
| 每页第一行为 H1（`# `） | 硬 | 读取文件首行 |
| 每页含至少 1 个 mermaid 代码块 | 软 | 正则 ` ```mermaid ` |
| 每页引用至少 5 个不同源文件 | 软 | 正则匹配 `来源：` 行中的文件引用 |
| 每页含至少 1 个 Markdown 表格 | 软 | 正则匹配 `\|.*\|.*\n\|[-:| ]+\|` |
| 文件名无非法字符 | 硬 | 检查 `/\:*?"<>|` |
| 页面间 `.md` 链接指向的文件存在 | 软 | 正则匹配 `[xxx](xxx.md)`，检查目标文件存在 |

**退出码**：硬门禁失败 → exit 1；软门禁失败 → exit 0 + warning 到 stderr。
检查结果同时写入状态文件的 `verify` 字段。

---

## 二、生成的 wiki 产物目录结构

### 2.1 现状

当前 `export_wiki.py` 的行为：
- 所有页面平铺在 `docs/wiki/` 一层
- 全面模式的 sections/subsections 只体现在概览页的目录导航里
- 实际文件没有按章节建子目录

```
docs/wiki/
├── 项目概览.md
├── 系统架构.md
├── 核心功能.md
├── 数据管理.md
├── 后端服务.md
└── 部署基础设施.md
```

### 2.2 问题

1. **页面超过 10 个时，平铺结构不清晰**——无法从文件系统层面看出页面属于哪个章节
2. **子章节页面无法体现层级**——subsection 下的页面和顶层页面混在一起
3. **源文件引用路径写死 `../../`**——如果按章节建子目录，路径深度会变化

### 2.3 调整方案

#### 全面模式（8-12 页）：按章节建子目录

```
docs/wiki/
├── 项目概览.md                       # 概览页在根目录（入口，含全局目录导航）
├── 系统架构/                          # 顶层 section → 子目录
│   ├── 整体架构设计.md               # section 下的 page
│   └── 组件关系.md
├── 核心功能/
│   ├── 用户管理.md
│   └── 权限控制.md
├── 数据管理/
│   ├── 数据流.md
│   └── 存储设计/                      # 子章节 → 嵌套子目录
│       └── 数据库Schema.md
└── 部署基础设施/
    └── 部署流程.md
```

#### 精简模式（4-6 页）：保持平铺

```
docs/wiki/
├── 项目概览.md
├── 系统架构.md
├── 核心功能.md
└── 部署配置.md
```

精简模式没有 sections，页面数少，平铺最清晰。

### 2.4 需要修改的代码

#### `export_wiki.py` — 按章节分层输出

**当前逻辑**（`export_wiki` 函数）：
```python
for page in pages_sorted:
    filename = page_id_to_file[page_id]
    file_path = os.path.join(output_dir, filename)  # 全部平铺
```

**修改后逻辑**：
```python
# 全面模式：根据 page 所属的 section 构建子目录路径
# 精简模式：保持平铺

def build_page_dir(page: dict, sections: list, root_sections: list) -> str:
    """返回页面应存放的子目录路径（相对于 output_dir）。

    精简模式（无 sections）返回空字符串 → 平铺。
    全面模式返回 "章节标题/子章节标题/" 形式的路径。
    """
    if not sections:
        return ""

    parent_section_id = page.get("parentSection", "")
    if not parent_section_id:
        return ""

    # 构建从根章节到该 page 所属章节的路径链
    section_map = {s["id"]: s for s in sections}
    path_parts = []
    current_id = parent_section_id

    # 向上找到根 section，构建路径链
    # （需要反向查找：哪个 section 的 subsections 包含 current_id）
    chain = []
    visited = set()
    while current_id and current_id not in visited:
        visited.add(current_id)
        sec = section_map.get(current_id)
        if sec:
            chain.append(sanitize_filename(sec["title"]))
            # 找父 section
        parent = _find_parent_section(current_id, sections)
        current_id = parent["id"] if parent else None

    chain.reverse()
    return os.path.join(*chain) if chain else ""
```

**`page_id_to_file` 映射也要更新**：
```python
# 当前
page_id_to_file[page["id"]] = build_page_filename(page, used_filenames)

# 修改后（路径包含子目录）
page_dir = build_page_dir(page, sections, root_sections)
page_filename = build_page_filename(page, used_filenames)
page_id_to_file[page["id"]] = os.path.join(page_dir, page_filename) if page_dir else page_filename
```

**`build_toc()` 中的链接路径**：
当前概览页目录链接直接用文件名 `[标题](文件名.md)`，修改后要用包含子目录的路径 `[标题](子目录/文件名.md)`。

**写入文件时创建子目录**：
```python
file_path = os.path.join(output_dir, page_id_to_file[page_id])
os.makedirs(os.path.dirname(file_path), exist_ok=True)  # 确保子目录存在
with open(file_path, "w", encoding="utf-8") as f:
    f.write("\n".join(parts))
```

#### `page-content-prompt.md` — 源文件引用路径动态化

**当前**（写死 `../../`）：
```
来源：[filename.ext:行号](../../filename.ext)
```

**修改后**（根据页面深度动态计算）：

提示词中的路径占位符从 `{FILE_PATHS_LINKED}` 改为由 SKILL.md 在步骤 4 中根据页面所属 section 深度动态生成。

SKILL.md 步骤 4 的占位符替换新增一条：
```
- {FILE_PATHS_LINKED} → 根据页面所在目录深度计算相对路径前缀
  - 平铺页面（精简模式或概览页）：../../
  - 一级子目录页面（如 系统架构/）：../../../
  - 二级子目录页面（如 数据管理/存储设计/）：../../../../
```

或者更简单的做法：所有源文件引用统一用仓库根目录的绝对路径风格 `[filename](/filename)`，不依赖相对路径深度。但这取决于目标 Markdown 渲染器是否支持。

#### `structure-prompt.md` — 无需修改

XML 结构已经支持 sections/subsections，不需要改提示词。变化只在导出阶段。

### 2.5 概览页目录导航的变化

当前概览页目录：
```markdown
## 目录

### 概览
- 项目概览（本页）

### 系统架构
- [整体架构设计](整体架构设计.md)

### 核心功能
- [用户管理](用户管理.md)
```

修改后概览页目录（路径包含子目录）：
```markdown
## 目录

### 概览
- 项目概览（本页）

### 系统架构
- [整体架构设计](系统架构/整体架构设计.md)

### 核心功能
- [用户管理](核心功能/用户管理.md)
```

---

## 三、调整前后目录结构对比

### 3.1 调整前

```
repo-wiki/
├── SKILL.md
├── references/
│   ├── structure-prompt.md
│   ├── page-content-prompt.md
│   ├── harness-optimization-analysis.md      # 分析文档
│   └── directory-structure-design.md          # 本文档
└── scripts/
    ├── scan_repo.py
    ├── scan_api_entries.py
    ├── parse_structure.py
    └── export_wiki.py
```

### 3.2 调整后

```
repo-wiki/
├── SKILL.md                                  # 更新：引用各 reference，新增状态/门禁/角色步骤
├── references/
│   ├── structure-prompt.md                    # 已有，不变
│   ├── page-content-prompt.md                # 已有，需修改：引用路径动态化
│   ├── state-ledger.md                       # 新增：状态文件规范（参照 or-workflow-guide）
│   ├── wiki-state.example.yaml               # 新增：状态文件示例（参照 sdd-state.example.yaml）
│   ├── agent-contracts.yaml                  # 新增：子 agent 角色契约（参照 roles.yaml）
│   ├── wiki-structure.example.xml            # 新增：文档结构 XML 示例（参照 examples.md）
│   ├── verify-checklist.md                   # 新增：验证检查清单（参照 design-review-checklist.md）
│   ├── harness-optimization-analysis.md      # 已有，非运行时分析文档
│   └── directory-structure-design.md         # 本文档，非运行时设计文档
└── scripts/
    ├── scan_repo.py                           # 已有，不变
    ├── scan_api_entries.py                    # 已有，不变
    ├── parse_structure.py                     # 已有，不变
    ├── export_wiki.py                         # 已有，需修改：支持按章节分层输出
    └── verify_wiki.py                         # 新增：产物验证门禁脚本（参照 sdd_doctor.py）
```

### 3.3 与同项目 skill 的结构对照

| 用途 | or-workflow-guide | app-design | repo-wiki（调整后） |
|---|---|---|---|
| 角色契约 | `agents/roles.yaml` | — | `references/agent-contracts.yaml` |
| 状态示例 | `references/sdd-state.example.yaml` | — | `references/wiki-state.example.yaml` |
| 状态规范 | `references/state-ledger.md` | — | `references/state-ledger.md` |
| 门禁脚本 | `scripts/sdd_doctor.py` | — | `scripts/verify_wiki.py` |
| 审查清单 | — | `references/design-review-checklist.md` | `references/verify-checklist.md` |
| 契约模板 | — | `references/app-contract-template.yaml` | —（repo-wiki 用 XML 提示词，不需要 YAML 契约模板） |
| Schema 校验 | — | `references/*.schema.json` | —（可选，未来可加 wiki-structure.schema.json） |
| 示例文件 | `references/*.example.json` | — | `references/wiki-structure.example.xml` |
| 分析文档 | — | — | `references/harness-optimization-analysis.md` |

**为什么 repo-wiki 不用 `agents/` 目录**：`or-workflow-guide` 有 `agents/roles.yaml` 是因为它有 4 个正式的 sub-agent 角色。repo-wiki 的角色只有一个（页面生成 agent），放在 `references/agent-contracts.yaml` 更自然，不需要单独建 `agents/` 目录。

**为什么 repo-wiki 不用 `assets/` 目录**：skill-creator 定义 `assets/` 用于"templates, fixtures, etc."，但同项目 `or-workflow-guide` 和 `app-design` 都没用 `assets/`，而是把 example/template 文件放在 `references/` 里。repo-wiki 保持与同项目一致的惯例。

---

## 四、对现有代码的影响

| 文件 | 变更类型 | 变更内容 |
|---|---|---|
| `SKILL.md` | 修改 | 步骤 0 新增状态文件初始化；步骤 3.5 新增人工确认关卡；步骤 4 引用 agent-contracts.yaml；步骤 6 改为调用 verify_wiki.py |
| `export_wiki.py` | 修改 | 新增 `build_page_dir()` 函数；`page_id_to_file` 映射含子目录路径；写入时 makedirs 创建子目录 |
| `page-content-prompt.md` | 修改 | 源文件引用路径说明改为动态深度计算 |
| `structure-prompt.md` | 不变 | — |
| `scan_repo.py` | 不变 | — |
| `scan_api_entries.py` | 不变 | — |
| `parse_structure.py` | 不变 | — |
| `verify_wiki.py` | **新增** | 产物验证门禁脚本 |
| `state-ledger.md` | **新增** | 状态文件规范 |
| `wiki-state.example.yaml` | **新增** | 状态文件示例 |
| `agent-contracts.yaml` | **新增** | 子 agent 角色契约 |
| `wiki-structure.example.xml` | **新增** | 文档结构 XML 示例 |
| `verify-checklist.md` | **新增** | 验证检查清单 |

---

## 五、对向后兼容的影响

- **增量更新场景**：如果用户已有旧版 `docs/wiki/`（平铺结构），新版本会按章节重建子目录。需要在 SKILL.md 步骤 0 的清理逻辑中说明这一点。
- **页面间链接**：旧版页面间的 `[标题](标题.md)` 链接在分层后会失效。但因为每次都是全量重新生成（当前无增量），所以不存在旧链接迁移问题。如果未来做增量更新，需要处理链接迁移。
- **状态文件**：旧版没有状态文件，首次运行时检测不到 `/tmp/wiki-state.yaml`，直接走全新流程。已有状态文件时走断点恢复。

---

## 六、风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| 章节标题含特殊字符导致子目录名异常 | 文件系统错误 | `sanitize_filename()` 已处理，子目录名同样经过清洗 |
| 子目录嵌套过深（3 层以上） | 路径过长，引用路径复杂 | 限制最大嵌套数为 2 层（section + subsection） |
| 源文件引用路径动态计算错误 | 链接失效 | verify_wiki.py 的"链接有效性检查"能捕获 |
| 精简模式误判为全面模式建子目录 | 不必要的嵌套 | `build_page_dir()` 先检查 `sections` 是否为空 |
| 状态文件格式被 LLM 写坏 | 断点恢复失败 | state-ledger.md 定义闭集值；verify_wiki.py 可加状态文件格式校验 |

---

## 七、实施路线

| 阶段 | 内容 | 依赖 | 新增/修改文件 |
|---|---|---|---|
| 第一阶段 | 新增状态文件 + 角色契约 + 验证脚本 + 示例文件 | 无 | `wiki-state.example.yaml`、`state-ledger.md`、`agent-contracts.yaml`、`verify-wiki.py`、`verify-checklist.md`、`wiki-structure.example.xml`；更新 `SKILL.md` |
| 第二阶段 | 修改 `export_wiki.py` 支持按章节分层输出 | 第一阶段完成 | `export_wiki.py` |
| 第三阶段 | 修改 `page-content-prompt.md` 源文件引用路径动态化 | 第二阶段完成 | `page-content-prompt.md` |
| 第四阶段 | 端到端测试：全面模式分层 + 精简模式平铺 + 验证脚本 | 前三阶段完成 | — |
