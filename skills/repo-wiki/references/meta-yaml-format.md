# meta.yaml 格式规范

> repo-wiki 在 `docs/wiki/meta.yaml` 中持久化产物元数据，支持增量更新。
> **当前版本：schema v2**（向后兼容 v1 读取器）。

## 文件位置

`docs/wiki/meta.yaml` — 和生成的 wiki 文档同级，持久化在仓库内，不随临时文件清理删除。

## 用途

1. **增量更新** — 下次运行时，比较当前仓库的 git_hash/file_hashes/facts_hash 和 meta.yaml 里记录的 hash，只重新生成发生变化的页面
2. **产物追踪** — 记录每个页面的生成时间、关联的源文件列表、源文件内容 hash、实际引用的源文件
3. **手工编辑检测** — 通过 content_hash 和 manual_edit_hash 判断页面是否被手工修改

## 格式（schema v2）

```yaml
# wiki 产物元数据 (schema v2)，用于增量更新
schema_version: 2
repo_path: "/path/to/repo"
git_hash: "abc123def456"
generated_at: "2026-08-07T15:21:03"

repository:
  path: "/path/to/repo"
  branch: "main"
  git_commit: "abc123def456"
  dirty: false

generator:
  skill_version: "1.0.0"
  prompt_hash: "a1b2c3d4"
  facts_hash: "e5f6a7b8"      # 来自 build_facts.py 的 wiki_facts.json
  structure_hash: "c9d0e1f2"  # 来自 structure.json 的确定性 hash

pages:
  - id: "page-overview"
    title: "项目概览"
    file: "项目概览.md"
    importance: "high"
    source_files:
      - "README.md"
      - "package.json"
    source_hash: "af316ecb91a8ee7a"
    content_hash: "b4c5d6e7f8a9b0c1"       # 页面 .md 文件内容 hash
    manual_edit_hash: ""                    # 手工编辑 hash（下次运行时填充）
    actual_used_sources: []                 # 来自 used_sources sidecar 的实际引用
  - id: "page-arch"
    title: "整体架构"
    file: "系统架构/整体架构.md"
    importance: "high"
    source_files:
      - "src/core/orchestrator.ts"
    source_hash: "e7bf382f6e5915b3"
    content_hash: "d5e6f7a8b9c0d1e2"
    manual_edit_hash: ""
    actual_used_sources:
      - path: "src/core/orchestrator.ts"
        symbol: "Orchestrator#run"
        lines: [42, 87]

modules:
  - id: "web"
    title: "Web Module"
    scope: ["web/"]
    module_hash: "f8a9b0c1d2e3f4a5"
    pages: ["page-arch"]
```

## v2 新增字段

### 顶层

| 字段 | 说明 |
|---|---|
| `schema_version` | 元数据 schema 版本（当前 2） |
| `repository` | 仓库信息（path/branch/git_commit/dirty） |
| `generator` | 生成器信息（skill_version/prompt_hash/facts_hash/structure_hash） |

### pages 列表项新增

| 字段 | 说明 |
|---|---|
| `content_hash` | 页面 .md 文件内容 hash（SHA-256 前 16 位） |
| `manual_edit_hash` | 上次手工编辑的 hash（用于检测手工修改） |
| `actual_used_sources` | 页面实际引用的源文件列表（来自 used_sources sidecar），每条含 path/symbol/lines |

## v1 向后兼容

v2 保留了 v1 的顶层字段（`repo_path`、`git_hash`、`generated_at`），旧版本读取器仍可正常读取基本信息。新增的 `schema_version`、`repository`、`generator` 和 pages 内的 v2 字段对旧读取器透明（忽略未知字段）。

## 增量更新流程（v2）

### 1. 判断哪些页面需要重生成

对每个页面，依次检查：
1. `source_hash` 是否变化（源文件内容变了）
2. `content_hash` 是否变化但 `source_hash` 未变（用户手工编辑了页面——保留手工内容，除非显式要求重生成）
3. `generator.facts_hash` 是否变化（事实层变了——受影响页面需重生成）
4. `generator.structure_hash` 是否变化（结构变了——全量重生成）
5. `generator.prompt_hash` 是否变化（提示词变了——全部页面重生成）

### 2. 检测手工编辑

如果 `source_hash` 未变但 `content_hash` 与磁盘上实际文件内容 hash 不同，说明用户手工编辑了页面。此时：
- 将当前 `content_hash` 存入 `manual_edit_hash`
- 默认保留手工内容，不覆盖
- 除非用户显式要求全量重生成

## 与 wiki-state.yaml 的区别

| 维度 | meta.yaml | wiki-state.yaml |
|---|---|---|
| 位置 | `docs/wiki/meta.yaml`（持久化） | `docs/.wiki-state.yaml`（持久化，隐藏文件） |
| 生命周期 | 跨多次运行保留 | 一次运行后清理 |
| 内容 | 产物级元数据（git_hash、source_hash） | 流程级状态（步骤进度、断点恢复） |
| 核心用途 | 增量更新（哪些页面需要重新生成） | 断点恢复（从哪步继续执行） |

## 生成方式

由 `export_wiki.py` 在导出 wiki 时自动生成：

```bash
python3 skills/repo-wiki/scripts/export_wiki.py \
  docs/tmp/wiki_structure.json \
  --output docs/wiki \
  --scan docs/tmp/wiki_scan.json    # 提供 scan.json 以获取 git_hash 和 file_hashes
```

`--scan` 参数是可选的。如果不提供，meta.yaml 中的 git_hash 和 source_hash 为空字符串，无法进行增量更新。
