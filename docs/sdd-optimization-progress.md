# SDD Skills 优化 · 进展日志

> 本文件记录 skills/ 体系按 SDD（Spec-Driven Development）四阶段迭代的**实施进展**，供后续接续。
> 设计依据：[[sdd-four-phase-analysis.md]]（13 个问题的纵深诊断）、[[sdd-adjustment-analysis.md]]（文件级调整方案）、[[skills-optimization-plan.md]]（第一轮，已落地）。
> 更新日期：2026-06-24。

---

## 0. 一句话现状

第二轮优化（第一波 + 第二波，commit `dbcd259`）**已完成并自测通过**：流水线从「文档驱动」升级为「结构化契约驱动 + 代码级可追溯 + 阶段门禁 + 缺陷回流闭环」。

第三波（迭代治理）**部分完成**：✅ C1 变更影响分析（迭代重生成）、✅ C4 跳阶段 waiver 机制、✅ C3 运行时文档（安全子集，含 schema 读取路径已统一）；⏸️ C2 删除 brd-generation（用户未选）；⏸️ C3-code 剩余项（`finish_ontology.py` 的 `common/` 依赖、`openai.yaml` 编排）。

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

### 第三波（迭代治理）· 文件清单

**新增文件（2）**

| 文件 | 解决项 | 作用 |
|------|--------|------|
| `skills/or-workflow-guide/references/spec-versions.example.json` | C1 | 规格版本指纹账本格式示例（sha256，运行时真制品在 `docs/spec-versions.json`） |
| `skills/or-workflow-guide/references/runtime-assumptions.md` | C3 | 运行时假设与路径约定（`finish_ontology.py` 外部运行时事实、跨运行时状态真相源、C3-code 暂缓说明） |

**修改文件（4）**

| 文件 | 解决项 | 关键改动 |
|------|--------|---------|
| `skills/or-workflow-guide/SKILL.md` | C1/C4/C3 | C4：账本 `waived` 状态 + 结构化字段 + 准出门禁注解改写 + 交互规范升级；C1：进度账本记录规格版本 + 新增「规格变更处理」节（传播表 + 4 步流程）+ 工作流图补变更支线；C3：补一行指向 `runtime-assumptions.md` |
| `skills/code-generation/SKILL.md` | C1/C4 | 步骤0「两种模式」→「三种模式」新增「规格变更增量」+ 增量注意事项；C4：上游完整性 preflight（waived/契约缺失时降级告警） |
| `skills/code-verification/SKILL.md` | C1/C4 | 步骤6 衔接 C1 增量重生成分支；输入注解与关键原则的降级条件扩展到「上游 waived」 |
| `skills/ontology-modeling/SKILL.md` | C1 | G3 门禁末尾补「基线批准即冻结 `docs/spec-versions.json` 变更锚点」 |

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

## 5. 提交状态

- **第二轮（第一波+第二波）**：已提交（commit `dbcd259`）。
- **第三波（C1/C4/C3-文档）**：本日志此前误记为「尚未提交」，现已更正。第三波改动停留在工作区（未 commit）；`git status` 可见本轮修改 + 新增。按惯例，提交留给用户确认（或按团队流程处理）。
- **无关改动**：工作区另有 `skills/app-design/references/backend-tech-guidelines.md` 的一处未提交编辑（架构层由 `Controller → Biz → Service → DAL` 调整为 `Starter → Controller → Biz → Service → DAL`、移除 auth SDK 模块），**与本轮 SDD 第三波无关**，不纳入本轮、不触碰。
- **工作区既有脚本改动（非本轮 SDD 文档工作产生，已据实纳入文档）**：`skills/ontology-modeling/references/script/finish_ontology.py`（schema 读取路径统一为 `docs/ontology_schema.json`，已纳入 C3-code 文档）与 `validate_ontology.py`（`python`→`python3` 注释等小改）。二者本会话期间发现、**非我所编辑**；是否提交由用户决定。

---

## 6. 第三波状态

| 项 | 状态 | 落点 |
|----|------|------|
| C1 变更影响分析（迭代重生成） | ✅ 已完成 | §3 第三波清单；`or-workflow-guide`「规格变更处理」节 + `code-generation`「规格变更增量」模式 + `spec-versions.example.json` |
| C4 跳阶段 waiver 机制 | ✅ 已完成 | §3 第三波清单；`or-workflow-guide` 账本 `waived` + 准出门禁 + 交互规范；`code-generation`/`code-verification` 降级联动 |
| C3 运行时文档（安全子集） | ✅ 已完成 | `references/runtime-assumptions.md`（不改任何代码） |
| C2 删除 brd-generation 单一化入口 | ⏸️ 暂缓 | 见下「C2」（用户本轮未选） |
| C3-code schema 读取路径统一 | 🟡 部分落地 | `finish_ontology.py` 工作区已改为读 `docs/ontology_schema.json`（见下「C3-code」） |

### 仍暂缓：C2 — 完整 SDD 入口单一化
**当前状态**：brd-generation 已降级标注、模板已统一，但 skill 仍保留（未删除）。**本轮用户未选择删除，保持不动。**
**若决定彻底单一化**：删除 `skills/brd-generation/` 整个目录（无 skill manifest 需更新，删目录即可），所有 BRD 需求统一走 ontology-modeling；可在 ontology-modeling 增加「轻量模式」标志跳过 schema 持久化。**需产品定位确认后再动。**

### 部分落地：C3-code — 运行时与产物路径**代码**统一
**已文档化（C3 文档子集已完成）**：`references/runtime-assumptions.md` 写明 `finish_ontology.py` 为外部运行时脚本（依赖 `common/`、POST `127.0.0.1:8080`；仓内不可独立运行）、`openai.yaml` 隐式调用、跨运行时状态真相源为 `docs/workflow-progress.md`。
**已落地的代码项**：`finish_ontology.py` 的 schema 读取路径已从 `<repo>/../output/ontology_schema.json` 统一为 `<repo>/docs/ontology_schema.json`（本会话工作区改动，**非本轮 SDD 文档工作产生**；文档已同步）。
**仍暂缓的代码级改动**：
- 移除 `finish_ontology.py` 的 `common/` 依赖（`from config/http_proxy import ...`）——仓内 `common/` 不存在，脚本仍无法独立运行。
- 修改 `agents/openai.yaml` 隐式调用策略或编排假设。
**接续要点**：先评估 OpenAI agent 回调是否参与阶段流转；确认外部运行时结构后再处理 `common/` 依赖。**风险较高，建议单独评估后再做。**

---

## 7. 接续时的快速恢复步骤

1. 读本文件 §2（产物链）+ §6（第三波状态/暂缓项）。
2. 若继续推进暂缓项：从 §6 的 C2 / C3-code 小节开始；C3-code 务必先评估外部运行时（`common/` 模块、OpenAI agent 回调）。
3. 若要验证当前状态：重跑 §4 的校验命令（validator 路径 `skills/ontology-modeling/references/script/validate_ontology.py`）。
4. 若要端到端走查：以 `skills/ontology-modeling/examples.md` 的天然气场景为输入，按 §2 产物链逐步检查交接闭环。
