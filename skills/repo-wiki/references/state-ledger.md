# 状态文件规范（State Ledger）

> wiki 生成流程的状态文件规范。状态文件是流程的唯一真相源，对话压缩后**信任状态文件不信任记忆**。

## 状态文件位置

- **运行时制品**：`docs/.wiki-state.yaml`
- **格式示例**：`references/wiki-state.example.yaml`

## 为什么需要状态文件

在对话式 AI Coding 中，整个生成过程依赖对话历史来传递上下文。随着流程推进，对话历史会迅速膨胀，出现三个问题：

1. 上下文有损压缩导致 AI 遗忘早期信息或偏离既定规则
2. 流程中断后无法恢复——对话窗口关闭后中间状态全部丢失
3. 流程推进缺乏可观测性，人和 AI 都不知道现在执行到哪一步了

状态文件解决这三个问题：把流程中的每一步进度、产出路径持久化到文件，让上下文脱离对话窗口独立存在。

## 字段规范

### 顶层字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `repo_path` | string | 目标仓库的绝对路径 |
| `mode` | string | `full`（全面模式 8-12页）或 `lite`（精简模式 4-6页） |
| `incremental` | boolean | `true`（增量更新）或 `false`（全量生成）。增量模式下只重新生成源文件发生变化的页面 |
| `git_hash` | string | 当前仓库的 commit hash（无 git 仓库则为空字符串） |
| `started_at` | string | 流程开始时间，ISO 8601 格式 |
| `current_step` | string | 当前正在执行的步骤标识符 |

### steps 字段

每个步骤是一个 key-value 对象，key 为步骤标识符（稳定英文键，不得改写为中文）：

| 标识符 | 显示别名 | 对应 SKILL.md 步骤 |
|---|---|---|
| `cleanup` | 清理临时文件 | 步骤 0 |
| `scan_repo` | 扫描仓库文件树 | 步骤 1 |
| `scan_api` | 扫描 API 入口 | 步骤 2 |
| `generate_structure` | 生成文档目录结构 | 步骤 3 |
| `generate_pages` | 逐页生成内容 | 步骤 4 |
| `export` | 导出到 docs/wiki/ | 步骤 5 |
| `verify` | 验证产物 | 步骤 6 |
| `cleanup_tmp` | 清理临时文件 | 步骤 7 |

### 步骤状态闭集

每个步骤的 `status` 字段只能取以下值：

| 值 | 含义 |
|---|---|
| `pending` | 尚未开始 |
| `in_progress` | 正在执行 |
| `complete` | 已完成且门禁通过 |
| `failed` | 执行失败 |

**规则**：`status=complete` 当且仅当该步骤的门禁检查通过。

### 各步骤特有字段

| 步骤 | 特有字段 | 说明 |
|---|---|---|
| `scan_repo` | `output` | scan_repo.py 输出的 JSON 路径 |
| `scan_api` | `output` | scan_api_entries.py 输出的 JSON 路径 |
| `generate_structure` | `output` | parse_structure.py 解析后的 JSON 路径 |
| | `raw_xml` | LLM 生成的原始 XML 路径 |
| `generate_pages` | `total_pages` | 总页面数 |
| | `completed_count` | 已完成页面数 |
| | `skipped_count` | 跳过页面数（增量模式） |
| | `failed_count` | 失败页面数 |
| | `pages` | 页面详细状态列表（见下方说明） |
| `verify` | `hard_gates_passed` | 硬门禁是否全通过：`true` / `false` / `null`（未执行） |
| | `soft_gates_warnings` | 软门禁警告列表 |

### generate_pages.pages 详细结构

每个页面的状态记录包含以下字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 页面 ID（如 `page-1`） |
| `title` | string | 页面标题 |
| `status` | string | 页面状态：`pending` / `in_progress` / `complete` / `failed` / `skipped` |
| `source_hash` | string | 源文件组合 hash（SHA-256 前 16 位），用于增量更新判断 |
| `output_file` | string | 输出文件路径（相对于 docs/wiki/） |
| `completed_at` | string | 完成时间（ISO 8601 格式），仅当 status=complete 时存在 |
| `error` | string | 失败原因，仅当 status=failed 时存在 |
| `skip_reason` | string | 跳过原因，仅当 status=skipped 时存在（如 `source_hash_unchanged`） |

**页面状态说明**：
- `pending`：尚未开始生成
- `in_progress`：正在生成中
- `complete`：已成功生成
- `failed`：生成失败（记录 error 原因）
- `skipped`：跳过生成（增量模式下源文件未变化，或用户手动跳过）

## 更新时机

执行者（LLM）在以下时机更新状态文件：

1. **步骤开始时**：将该步骤 `status` 设为 `in_progress`，更新 `current_step`
2. **步骤完成时**：将该步骤 `status` 设为 `complete`，填写 `output` 等特有字段
3. **步骤失败时**：将该步骤 `status` 设为 `failed`
4. **页面生成时**（generate_pages 步骤内）：
   - 步骤开始时：初始化 `pages` 列表，为每个页面创建状态记录（status=pending）
   - 每个页面开始生成时：更新该页面 `status=in_progress`
   - 每个页面生成完成时：更新该页面 `status=complete`，填写 `completed_at`，更新 `completed_count`
   - 每个页面生成失败时：更新该页面 `status=failed`，填写 `error`，更新 `failed_count`
   - 增量模式跳过页面时：更新该页面 `status=skipped`，填写 `skip_reason`，更新 `skipped_count`

## 中断恢复决策树

重新启动时，执行者先读取 `docs/.wiki-state.yaml`：

1. 文件不存在 → 全新流程，从步骤 0 开始
2. 文件存在 → 读取 `current_step` 和对应步骤的 `status`：
   - `status=complete` → 跳到下一个未完成的步骤
   - `status=in_progress` → 该步骤可能执行了一半，根据步骤类型决定：
     - `generate_pages`：检查 `pages` 列表中每个页面的状态：
       - `status=complete` 或 `status=skipped` → 跳过该页面
       - `status=in_progress` 或 `status=pending` → 重新生成该页面
       - `status=failed` → 重新生成该页面（可参考 error 字段了解失败原因）
     - 其他步骤：重新执行该步骤（幂等操作，重新执行无副作用）
   - `status=failed` → 重新执行该步骤
   - `status=pending` → 直接执行该步骤

## 增量更新模式

当 `incremental=true` 时，流程进入增量更新模式：

1. **步骤 0 判断**：读取 `docs/wiki/meta.yaml`，比较 git_hash 和 source_hash
2. **步骤 1-3**：正常执行（扫描、生成结构）
3. **步骤 4 选择性生成**：只重新生成 source_hash 发生变化的页面，未变化的页面保留原内容
4. **步骤 5 导出**：正常导出，更新 meta.yaml

增量更新的优势：
- 节省 token 消耗（只重新生成变化的页面）
- 保留用户手工编辑（未变化的页面不会被覆盖）
- 更快完成（跳过未变化页面的生成）

增量更新的限制：
- 结构变化（新增/删除页面）需要全量重新生成
- 源文件 hash 计算有开销（但比重新生成页面便宜）

## 写入方式

状态文件是 YAML 格式。更新时：
- 使用 shell heredoc 写入（参照 SKILL.md 的「写文件规则」）
- 每次更新写全整个文件（不做增量 patch，避免格式错乱）
- 更新后向用户简要说明当前进度
