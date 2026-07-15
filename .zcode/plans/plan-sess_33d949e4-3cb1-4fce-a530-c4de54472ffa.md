## 目标

在 `skills/` 下新建 `project-outline` skill（中文标题「项目大纲」），**逆向**从已有代码生成「业务功能全景图」作为项目大纲，供项目维护者无需通读源码即可了解功能全貌。

按已确认的选项：**纯文档型**，不与 SDD 流水线耦合——不产出 ontology/契约/代码，不写 `sdd-state.yaml`，不改 `or-workflow-guide`。

## 命名约定（沿用同仓惯例）

- 文件夹/frontmatter `name`：`project-outline`（英文 kebab-case，与 `app-design`/`code-generation` 一致）
- H1 标题：`# 项目大纲`（中文，与 `# 应用设计`/`# 代码生成` 一致）
- 主产物：`docs/business-panorama.md`；可选结构化伴侣：`docs/business-panorama.json`

> 若你本意是让 `name` 字段本身叫「项目大纲」而非英文，请在审批时纠正；默认按同仓惯例用英文 `name` + 中文 H1。

## 新建文件（5 个）

### 1. `skills/project-outline/SKILL.md`（主文件，~150 行，细则下沉 references）
- frontmatter：`name: project-outline` + 中文 description（触发词：逆向梳理存量项目 / 业务功能全景图 / 项目大纲 / 项目功能地图 / 新维护者了解全貌）
- `## 产物` 表（business-panorama.md 主、business-panorama.json 可选）
- `## 必读与按需参考` 表（场景 → 3 个 references + 1 脚本）
- `## 工作流程` 7 步：①探测技术栈 ②扫描模块 ③提取实体/关系 ④提取功能/入口 ⑤提取流程/规则 ⑥汇总外部依赖+维护者索引 ⑦自检汇报
- `## 逆向提取重点`（聚焦业务、剔除技术噪音）
- `## 推断项标注`（逆向必有推断，须标 `(推断)`）
- `## 准出门禁`（5 条检查 + 汇报模板，仿 app-design/design-review-checklist 的准出表达）
- `## 可视化伴侣`（仿 app-design：单独询问是否要架构图/依赖图）
- `## 关键原则`（代码为事实源、聚焦不罗列、推断显式标注、不耦合 SDD、主文件短小）

### 2. `skills/project-outline/references/panorama-structure.md`
- 全景图章节结构表 §1–§11：
  - §1 项目概述 / §2 技术栈与架构 / §3 模块地图 / §4 业务实体 / §5 业务功能清单 / §6 关键业务流程 / §7 关键业务规则 / §8 入口与接口 / §9 外部依赖 / §10 维护者索引 / §11 待确认推断清单
  - 标注必选/可选，并说明小项目可合并章节
- 维护者索引「想改 X 去哪里」表格格式
- Markdown 读写规则（每次覆盖写完整版、不写平台 artifact 标记，仿 ontology-modeling/output-contract）
- JSON 伴侣结构草图（meta/techStack/modules/entities/functions/flows/rules/entryPoints/externalDeps/assumptions）

### 3. `skills/project-outline/references/reverse-extraction-methodology.md`
- 通用原则（代码为事实源、标注推断、过滤噪音）
- 各维度提取启发式：模块/目录、业务实体与关系、功能清单与入口、关键业务流程、关键业务规则、外部依赖
- 调用链追踪方法（从入口 Controller/Router → Biz/编排 → Service → Repository/DB）
- 噪音过滤清单（审计基类、日志表、纯 helper、单步 CRUD、字段必填校验等剔除项）
- 推断项标注规则（`(推断)` / `(高置信推断)` 判定与 §11 格式）

### 4. `skills/project-outline/references/tech-detection-guide.md`
- 通用探测信号（构建文件、配置文件、入口声明）
- 按栈的检测启发式：Java/Spring Boot、Python/FastAPI、Node/Electron、Go、通用兜底
- 「技术栈信号 → 全景图章节」映射表

### 5. `skills/project-outline/scripts/validate_panorama.py`
- 仿 `sdd_doctor.py`：仅 Python 标准库、`argparse --root`、`[PASS]/[WARN]/[FAIL]/[INFO]` 汇报
- 检查：`docs/business-panorama.md` 存在 → 含全部必选章节关键词（作为 H2 标题）→ 无 TBD/TODO 占位符（WARN）→ 若 `business-panorama.json` 存在则可解析且含顶层键
- shebang + 顶部 docstring 写明运行方式

## 不做的事

- 不改 `or-workflow-guide`（不新增分诊通道、不注册到阶段表）——保持纯文档型、不耦合 SDD
- 不产出 `ontology_schema.json`/`app-contract.yaml`/任何代码
- 不改 `manifest.json`（其与 OR runtime 相关，非 skill 注册表；skill 由 `skills/` 文件夹自动发现）

## 验证

- 用 Bash 运行 `python3 skills/project-outline/scripts/validate_panorama.py` 自检脚本可执行、无语法错（对一个示例或空 docs 会给出 FAIL 但不崩）
- 人工核对 SKILL.md 与 references 的章节交叉引用、路径一致

## 风格对齐

中文叙述 + 英文技术术语；主文件短小、细则放 references；`## 必读与按需参考` 表；准出门禁 + 汇报模板；可视化伴侣单独询问——均与 `app-design`/`ontology-modeling` 一致。