# meta.yaml 格式规范

> repo-wiki 在 `docs/wiki/meta.yaml` 中持久化产物元数据，支持增量更新。

## 文件位置

`docs/wiki/meta.yaml` — 和生成的 wiki 文档同级，持久化在仓库内，不随临时文件清理删除。

## 用途

1. **增量更新** — 下次运行时，比较当前仓库的 git_hash/file_hashes 和 meta.yaml 里记录的 hash，只重新生成源文件发生变化的页面
2. **产物追踪** — 记录每个页面的生成时间、关联的源文件列表、源文件内容 hash
3. **新鲜度检测** — 判断文档是否过期

## 格式

```yaml
# wiki 产物元数据，用于增量更新
# 生成时间: 2026-07-14T15:21:03.073347
# 仓库: /path/to/repo
# Git Hash: abc123def456

repo_path: "/path/to/repo"
git_hash: "abc123def456"
generated_at: "2026-07-14T15:21:03.073347"

pages:
  - id: "page-overview"
    title: "项目概览"
    file: "项目概览.md"
    importance: "high"
    source_files:
      - "README.md"
      - "package.json"
    source_hash: "af316ecb91a8ee7a"
  - id: "page-arch"
    title: "整体架构"
    file: "系统架构/整体架构.md"
    importance: "high"
    source_files:
      - "src/core/orchestrator.ts"
      - "src/core/skill-loader.ts"
    source_hash: "e7bf382f6e5915b3"
```

## 字段说明

### 顶层字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `repo_path` | string | 源仓库的绝对路径 |
| `git_hash` | string | 生成时的 git commit hash（非 git 仓库为空字符串） |
| `generated_at` | string | 生成时间，ISO 8601 格式 |
| `pages` | list | 页面元数据列表 |

### pages 列表项

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 页面 ID（如 `page-overview`） |
| `title` | string | 页面标题 |
| `file` | string | 输出文件路径（相对于 docs/wiki/） |
| `importance` | string | 重要程度：`high` / `medium` / `low` |
| `source_files` | list | 该页面关联的源文件列表（来自 structure.json 的 filePaths） |
| `source_hash` | string | 源文件内容组合 hash（SHA-256 前 16 位） |

## 增量更新流程

### 1. 读取 meta.yaml

下次运行时，先检查 `docs/wiki/meta.yaml` 是否存在：
- 不存在 → 全量生成（首次运行）
- 存在 → 进入增量判断

### 2. 比较 git_hash

读取 meta.yaml 中的 `git_hash`，和当前仓库的 git hash 比较：
- 相同 → 代码未变化，所有页面都不需要重新生成
- 不同 → 进入文件级判断

### 3. 比较 source_hash

对每个页面，计算当前源文件的组合 hash，和 meta.yaml 中记录的 `source_hash` 比较：
- 相同 → 该页面的源文件未变化，保留现有内容（包括用户手工编辑的部分）
- 不同 → 该页面需要重新生成

### 4. 执行增量生成

- 只重新生成 source_hash 发生变化的页面
- 未变化的页面保留原文件
- 更新 meta.yaml（新的 git_hash、generated_at、source_hash）

## 手工编辑保护

增量更新时，未变化的页面保留原内容。这意味着：
- 用户手工编辑的内容不会被覆盖
- 只有源文件发生变化的页面才会被重新生成
- 重新生成的页面会丢失手工编辑（这是预期行为——源文件变了，文档需要更新）

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
