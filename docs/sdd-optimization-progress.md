# SDD Skills 优化 · 进展日志

> 本文件记录 skills/ 体系按 SDD（Spec-Driven Development）四阶段迭代的**实施进展**，供后续接续。
> 设计依据：[[sdd-four-phase-analysis.md]]（13 个问题的纵深诊断）、[[sdd-adjustment-analysis.md]]（文件级调整方案）、[[skills-optimization-plan.md]]（第一轮，已落地）。
> 更新日期：2026-06-23。

---

## 0. 一句话现状

第二轮优化（第一波 + 第二波）**已完成并自测通过**：流水线从「文档驱动」升级为「结构化契约驱动 + 代码级可追溯 + 阶段门禁 + 缺陷回流闭环」。**第三波（迭代治理）暂缓未做**。

---

## 1. 本轮决策记录

| 决策点 | 结论 | 理由 |
|--------|------|------|
| 实施范围 | **第一波（契约化 + 补 Tasks 阶段）+ 第二波（追溯 + 门禁 + 闭环）** | 这两波是「是不是真 Spec-Driven」的核心；第三波偏治理、价值低、且 C3 依赖对外部运行时的理解，存在不确定性 |
| brd-generation 去留 | **保留为降级轻量入口 + 统一两份模板**（不删除） | 删除是破坏性变更；保留轻量入口有真实用例（仅需文档）；降级标注 + 模板统一即可消除入口重叠危害 |
| Tasks 阶段实现方式 | **在 code-generation 内拆出「步骤1 实现计划」**（选项 A） | 改动最小、产出可立即用；不新增 skill，复用性足够 |
| 契约化程度 | **轻量**：定义 `app-contract.yaml` 结构 + JSON Schema，由 LLM 生成 | 立即可用，改造成本低；后续可演进到 OpenAPI 重型校验 |
| 运行时/路径统一（C3） | **本轮不动** `finish_ontology.py` / `openai.yaml` | 属第三波，且需评估 OpenAI agent 回调机制 |

---

## 2. 已落地：改造后的确定性产物链

```
ontology-modeling ──→ ontology_schema.json(+校验) + brd.md
                      + requirements-baseline.json + contracts/acceptance-tests.yaml
        ↓ gate G1/G2/G3：schema校验通过 & Must需求有稳定ID+验收标准 & 基线/验收契约产出
app-design ─────────→ app-design.md(人读视图) + contracts/db-schema.sql(权威DDL)
                      + contracts/app-contract.yaml(结构化契约)
        ↓ gate：契约覆盖 ontology 全部 对象/行为/规则/SOP 达 100%
code-generation ────→ 步骤1: impl-plan.md(独立审查门禁) → 步骤2: 骨架 → 步骤3: 并行填充
                      → 代码(方法带 @ontology/@brd/@rule) + traceability.json
        ↓
code-verification ──→ 步骤3 读 traceability.json 确定性匹配 + 步骤6 缺陷根因回流[spec-gap]/[impl-gap]
or-workflow-guide ──→ 进度账本扩展 gate/质量字段 + 各阶段准出标准
```

---

## 3. 已落地：文件清单

### 新增文件（4）

| 文件 | 作用 |
|------|------|
| `skills/app-design/references/app-contract-template.yaml` | 结构化契约模板（objects/behaviors/rules/sops 字段说明） |
| `skills/app-design/references/app-contract.schema.json` | app-contract.yaml 的 JSON Schema（字段/枚举/必填/code 唯一性/格式） |
| `skills/ontology-modeling/references/ontology_schema.schema.json` | Ontology 接口的 JSON Schema |
| `skills/ontology-modeling/references/script/validate_ontology.py` | **自包含校验脚本**（无第三方依赖）：结构、code 唯一性、edge 引用完整性、属性 type 枚举、code 格式 |

### 修改文件（9）

| 文件 | 解决的分析问题 | 关键改动 |
|------|--------------|---------|
| `skills/ontology-modeling/SKILL.md` | 问题13、10、12 | 文件路径表补 baseline/acceptance；步骤6 后新增「阶段准出门禁」G1(schema 校验) / G2(Must 需求稳定 ID+验收标准) / G3(产出 baseline + acceptance-tests) |
| `skills/app-design/SKILL.md` | 问题2、3、5 | 检查清单/流程图/数据库规则/接口规则：产出 `db-schema.sql`(权威)+`app-contract.yaml`；规范自审第7项升级为**可执行覆盖率门禁(100%)**；用户审查话术更新 |
| `skills/app-design/references/ontology-mapping-rules.md` | 问题2 | 末节改写：三张映射表 = app-contract.yaml 字段（人读视图 vs 机器可消费权威源）+ 准出门禁 |
| `skills/code-generation/SKILL.md` | 问题1、4 | **新增步骤1 实现计划(impl-plan.md, 独立门禁)**；步骤重排 0→1→2→3→4；骨架/子代理强制 `@ontology/@brd/@rule` Javadoc；产出 `traceability.json`；输入/输出表与关键原则更新；description 更新 |
| `skills/code-verification/SKILL.md` | 问题4、7、12 | 步骤3 改读 traceability.json **确定性匹配**；**新增步骤6 缺陷根因回流** `[spec-gap]`/`[impl-gap]`/`[scope]`；输入表补 traceability/baseline/acceptance；报告模板与关键原则更新；description 更新 |
| `skills/or-workflow-guide/SKILL.md` | 问题5 | 进度账本格式扩展 `gate=passed/质量` 字段（向后兼容）；新增「各阶段准出标准」表；完整工作流图补新产物；上下文传递更新；核心原则#1 标注 brd-generation 不进下游 |
| `skills/brd-generation/SKILL.md` | 问题8 | description + 正文开头加**降级轻量入口标注**（不产 schema、不能进下游、需完整 SDD 须补跑 ontology-modeling） |
| `skills/brd-generation/references/brd-template.md` | 问题8 | 重写为统一规范（与 ontology-modeling 版**完全一致**） |
| `skills/ontology-modeling/references/brd-template.md` | 问题8 | 重写为统一规范（§1–§10 + RACI + 数据生命周期 + 审批流程 + 变更记录 + 编写人/审核人） |

---

## 4. 已执行的校验（全部通过）

1. **两份 brd 模板一致性**：`diff` 完全相同 ✅
2. **两个 JSON Schema**：均可被 `json.load` 解析 ✅
3. **validator 脚本**：`python3 -m py_compile` 语法 OK；合法 schema→exit 0、非法 schema（重复 code / 悬空 edge / 非法 type / 重复规则）→exit 1 ✅
4. **6 个 SKILL.md frontmatter**：name/description 均非空 ✅
5. **交叉引用文件**：所有 references 文件存在 ✅
6. **产物链连贯性**：每个产物都有明确的产出方与消费方，上下游输入/输出对齐无缺口 ✅

> 环境说明：当前环境未安装 `pyyaml` / `jsonschema`。validator 脚本因此被设计为**自包含**（核心约束内置检查），不依赖这两个库；模板作为 LLM 参考无需可执行校验。

---

## 5. 改动尚未提交

所有改动停留在工作区（未 commit）。`git status` 可见 9 个修改 + 4 个新增。提交前需用户确认（或按团队流程处理）。

---

## 6. 未完成：第三波（迭代治理）· 接续指南

### C1 — 变更影响分析（支持迭代重生成）
**当前缺口**：流水线是一次性线性的。上游 schema/brd/契约改一处，下游不自动跟着改，第二版起靠人脑同步。
**接续入口**：`skills/or-workflow-guide/SKILL.md`
**待做**：
- 新增「规格变更处理」分支：上游产物变化 → 计算 diff → 生成「受影响产物清单」→ 仅重生成受影响部分。
- 进度账本记录「代码对应的规格版本（hash/序号）」，使「代码是否落后于规格」可判定。
- 配合 code-generation 的增量模式（当前只解决文件冲突，不解决规格 diff→代码 diff）。

### C2 — 完整 SDD 入口单一化（本轮仅做了一半）
**当前状态**：brd-generation 已降级标注、模板已统一，但 skill 仍保留（未删除）。
**若决定彻底单一化**：删除 `skills/brd-generation/` 整个目录（无 skill manifest 需更新，删目录即可），所有 BRD 需求统一走 ontology-modeling；可在 ontology-modeling 增加「轻量模式」标志跳过 schema 持久化。**需产品定位确认后再动**。

### C3 — 运行时与产物路径统一（本轮明确未动）
**已知不一致点**：
- `skills/ontology-modeling/references/script/finish_ontology.py` 第 17 行读取 `output/ontology_schema.json` 并回调本地代理 `http://127.0.0.1:8080/.../skill/complete`，**与主流程约定的 `docs/ontology_schema.json` 路径不一致**。
- 该脚本还 `from common import ...`（`common/` 目录在**本仓库不存在**，属更大系统的一部分）——修改前需先搞清楚外部运行时结构。
- `skills/or-workflow-guide/agents/openai.yaml` 表明 skill 可能被 OpenAI agent 入口隐式调用，其运行时假设（进度状态权威、产物路径、阶段触发）未与本地 skill 文件对齐。
**接续要点**：先评估 OpenAI agent 回调是否参与阶段流转；选定 `docs/workflow-progress.md` 为跨运行时唯一状态真相源；统一所有产物路径；在 skill 文档写明运行时假设。**风险较高，建议单独评估后再做**。

### C4 — 跳阶段 waiver 机制
**当前缺口**：or-workflow-guide 允许跳过阶段，但进度账本无法表达「带风险豁免的非完整 SDD 流程」。
**接续入口**：`skills/or-workflow-guide/SKILL.md`（准出标准表里已预留 `waived` 占位说明）。
**待做**：跳过阶段时记录 `waived` 状态 + 跳过原因 + 缺失产物 + 风险 + 补齐建议；下游读取到 `waived` 后降低自动化承诺（如 code-generation 提示「非完整 SDD 输入，追溯完整无保障」）。

---

## 7. 接续时的快速恢复步骤

1. 读本文件 §2（产物链）+ §6（未完成项）。
2. 若继续第三波：从 §6 对应小节的「接续入口」文件开始；C3 务必先评估外部运行时（`common/` 模块、OpenAI agent 回调）。
3. 若要验证当前状态：重跑 §4 的校验命令（validator 路径 `skills/ontology-modeling/references/script/validate_ontology.py`）。
4. 若要端到端走查：以 `skills/ontology-modeling/examples.md` 的天然气场景为输入，按 §2 产物链逐步检查交接闭环。
