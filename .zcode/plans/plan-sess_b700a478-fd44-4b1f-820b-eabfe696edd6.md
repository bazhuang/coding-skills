## 调整 repo-wiki skill：引入层级章节树（sections）

### 核心变更
将扁平布局 `docs/wiki/<模块中文名>.md` 改为章节树布局 `docs/wiki/<章节名>/<模块中文名>.md`，借鉴 DeepWiki 的 WikiSection 模型。保留全中文输出 + 中文文件名。

### 工作流：3 阶段 → 4 阶段
1. 模块合成（增强：加业务领域标签）
2. **章节规划（新增）**：LLM 分析模块树 → 输出章节树 XML → `.section-tree.md`
3. 按模块生成文件（调整：在章节目录下生成、frontmatter 加 section 字段）
4. 跨切面知识（不变）

### 文件变更清单（6 个文件）
1. **新建** `references/section-planning.md` — 章节规划流程定义
2. **修改** `SKILL.md` — 核心模型、产物表、工作流、门禁
3. **修改** `references/module-synthesis.md` — 新增业务领域标签提取
4. **修改** `references/module-file-format.md` — 章节目录布局 + _section.md + index.md 章节树视图
5. **修改** `references/coverage-gates.md` — 章节归属覆盖率检查
6. **修改** `scripts/validate_repo_wiki.py` — 扫描章节子目录验证

### 不改动
- repo-knowledge.md（6 跨切面类别）
- 模块文件内部知识维度章节结构
- 全中文输出原则