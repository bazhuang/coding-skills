# SDD 四步工作流视角下的 Skills 调整分析

> 分析对象：`gas_agents/skills/` 下 6 个 skill
> 分析框架：Requirements → Design → Tasks → Implementation（来自 claude-code-spec-workflow 的 SDD 四阶段）
> 目标：基于四步 SDD 流程，给出每个 skill 的调整建议，使流水线真正"规格驱动、可追溯、可闭环"

---

## 0. 当前 Skills 与 SDD 四阶段的映射

| SDD 阶段 | 当前对应 Skill | 当前评级 | 核心问题 |
|----------|---------------|---------|---------|
| **① Requirements**（需求规格） | `ontology-modeling` + `brd-generation` | ⚠️ 职责重叠 | 两个 skill 产出一份 `brd.md`，模板不同、入口不同 |
| **② Design**（详细设计） | `app-design` | ✅ 骨架完整 | 但产物`app-design.md`为自由 Markdown，下游需要 LLM 重新理解 |
| **③ Tasks**（任务分解） | ❌ **缺失** | 🔴 无独立阶段 | 被藏进`code-generation`步骤1内部，无独立产物、无门禁 |
| **④ Implementation**（实现） | `code-generation` + `code-verification` | ✅ 有 | code-generation 骨架/填充拆分合理；但缺少中间计划层 |

---

## 1. 问题诊断（针对四步调整）

### 1.1 阶段①：Requirements 存在双入口

**症状**：
- `ontology-modeling` 产出 `ontology_schema.json` + `brd.md`（双产出）
- `brd-generation` 只产出 `brd.md`，不走 schema，且有自己的模板和 examples
- 两个 skill 引用的 `brd-template.md` 结构已有差异（章节编号、RACI矩阵、数据生命周期、变更记录字段均不同）

**对四步流程的影响**：
- `or-workflow-guide` 路由时不确定该走哪个 skill
- 下游 `code-verification` 从 BRD 提取功能点时，因模板不同提取不固定
- 用户如果走 `brd-generation`，产出的 brd 没有 schema 支撑，app-design 缺少本体输入

**结论**：`brd-generation` 必须合并进 `ontology-modeling`，或转型为 `ontology-modeling` 的轻型入口。

### 1.2 阶段②：Design 产物结构化不足

**症状**：
- `app-design.md` 的自由 Markdown 文本是 code-generation 的唯一输入
- code-generation 的"骨架阶段"需要 LLM 从 Markdown 的三张映射表中"读懂"要生成什么类、什么签名
- DDL 写在 Markdown 代码块里而非可直接执行的 `.sql`
- 接口定义是 Markdown 表格而非 OpenAPI/契约文件

**对四步流程的影响**：
- 阶段②→③ 的传递不是确定性变换，而是"LLM 读文档再发挥"
- 每次骨架生成结果不可复现，同样的设计可能产出不同的代码
- code-verification 无法做 DDL 与设计的确定性校验

### 1.3 阶段③：Tasks 缺失——最根本的断裂

**症状**：
- 业界 SDD（含 claude-code-spec-workflow）在 Design 与 Implementation 之间有独立的 Tasks 阶段
- 本项目把 Task 分解塞进 code-generation 步骤1"骨架阶段"内部
- 没有独立的实现计划文档，没有独立的门禁

**对四步流程的影响**：
- **设计可行性的预演缓冲层缺失**：如果设计有问题，要等到生成骨架时才暴露
- **用户无法在写代码前审查实现计划**：只有设计文档可审，骨架写完才可见
- **code-generation 职责过重**：同时承担"task 分解 + 骨架生成 + 并行填充"三重职责，出错时难定位是设计问题还是实现问题
- 这是整条流水线上最需要解决的问题

### 1.4 阶段①→②→③→④ 之间的其他问题

| 断点 | 问题 | 影响 |
|------|------|------|
| ①→② 衔接 | BRD 无 schema 时 app-design 缺输入 | 本体依赖断裂 |
| ②→③ 无契约 | app-design.md 是非结构化 Markdown | 骨架推导不稳定 |
| ③→④ 无追踪 | 代码无"出处标注" | 验证只能靠方法名模糊匹配 |
| ④ 无回流 | code-verification 报告即终点 | 缺陷不改规格，迭代漂移 |

---

## 2. 调整建议（基于 SDD 四步流程）

### 2.1 重构阶段①：统一需求入口

**调整方案**（P1）：

- **合并 `brd-generation` 进 `ontology-modeling`**：删除独立 skill
- `ontology-modeling` 增加显式"需求基线"子环节：建模完成后、产 BRD 前单独做需求收敛确认
- 统一为单一 `brd-template.md`（仅保留一份，删冗余）
- 如果用户只需 BRD 不需 Schema，在 `ontology-modeling` 中加"轻量模式"标志（skip schema 持久化）

**调整后阶段①结构**：

```
ontology-modeling（单一入口）
  ├── 步骤1-5: 本体建模（产出 ontology_schema.json）
  ├── 步骤6: 需求收敛确认（单独门禁）
  └── 步骤7: 产 BRD（docs/brd.md）
```

### 2.2 升级阶段②：契约化设计产出

**调整方案**（P0）：

在 `app-design` 中新增结构化契约产出，而非仅自由 Markdown：

```
docs/
  ├── app-design.md         ← 人类可读视图（自动从契约生成）
  ├── contracts/
  │   ├── db-schema.sql     ← 可直接执行的 DDL（取代 Markdown 内嵌为权威源）
  │   └── app-contract.yaml ← 结构化接口/映射契约
  └── db-schema.md          ← 保留向后兼容（但引用 .sql 为权威源）
```

**`app-contract.yaml` 结构示例**：

```yaml
# 设计契约：确定性的输入给 code-generation
project:
  basePackage: "com.enn.gas"
  modules: ["web", "service", "dal", "client"]

objects:
  - code: "gas_contract"
    name: "GasContract"
    table: "biz_gas_contract"
    behaviors:
      - type: "CREATE"
        controller: "/api/gas-contract/create"
        biz: "createGasContract"
        service: "insertGasContract"
      - type: "QUERY"
        controller: "/api/gas-contract/query"
        biz: "queryGasContract"
        service: "selectGasContractList"

rules:
  - code: "profit_calc_rule"
    source: "ontology"
    type: "CALCULATION"
    location: "GasContractService.calculateProfit()"
  - code: "must_supply_rule"
    source: "ontology"
    type: "CONSTRAINT"
    location: "GasPlanBizService.validateMustSupply()"
```

**`app-design/SKILL.md` 调整点**：
- 增加"步骤7.5：生成设计契约"——完成设计的同时生成 `app-contract.yaml` 和 `db-schema.sql`
- DDL 以 `.sql` 为权威源，`docs/db-schema.md` 退化为引用说明文档
- 映射表从"SKILL.md 中约束"变为"实际产物"

### 2.3 新增阶段③：补独立 Tasks 阶段（最关键）

**调整方案**（P0）：

在 `app-design` 与 `code-generation` 之间新增一个**独立的 Tasks 阶段**，可以是：
1. 在 `or-workflow-guide` 中增加子路由"spec-execute"
2. 或在 `code-generation` 前加独立步骤，产出 `docs/impl-plan.md`

**建议方案**：**不新建 skill，而是在 code-generation 前加独立子阶段**

**`code-generation/SKILL.md` 调整**：

```
步骤 0：生成实现计划（实现计划作为独立门禁）
   ├── 对照 app-contract.yaml 和 db-schema.sql
   ├── 产出 docs/impl-plan.md（所有类、方法签名、文件路径、分组、依赖顺序）
   ├── 行为→接口确定性的完整映射
   └── 用户确认后进入步骤1
      （用户可提修改意见，修改设计契约后重新生成计划）

步骤 1：生成全局骨架（基于已批准的 impl-plan 确定性生成）
步骤 2：并行填充实现
步骤 3：可选测试代码
```

**`docs/impl-plan.md` 示例**：

```markdown
# 实现计划

## 分组 1：基础设施（无依赖）
- [x] GasContractPO.java — com.enn.gas.dal.po
- [x] GasContractVO.java — com.enn.gas.client.vo
- [x] GasContractMapper.java — com.enn.gas.dal.mapper
- [x] GasContractMapper.xml — resources/mapper

## 分组 2：数据访问（依赖 PO + Mapper）
- [x] GasContractService.java — com.enn.gas.service
- [x] GasResourceService.java — com.enn.gas.service

## 分组 3：业务编排（依赖 Service）
- [x] GasContractBizService.java — com.enn.gas.biz

## 分组 4：接口（依赖 Biz）
- [x] GasContractController.java — com.enn.gas.controller

## 映射完整性校验
- 对象覆盖：6/6 ✅（GasContract, GasResource, GasPlan, ...）
- 行为覆盖：24/24 ✅（每个对象 4 类行为）
- 规则覆盖：5/5 ✅
- SOP 覆盖：3/3 ✅
```

**关键变更**：
- 阶段③有了独立产物 `docs/impl-plan.md`
- 有了独立门禁：用户确认计划后再写代码
- 设计可行性的预演在写业务代码前完成
- 计划包含数量化的覆盖校验

### 2.4 加固阶段④：代码带追溯 + 验证闭环

**调整方案**（P1）：

**`code-generation/SKILL.md` 调整**：

在步骤1"生成全局骨架"中强制：
- 每个 Controller/Biz/Service 方法在 Javadoc 标注来源 ID
- 生成 `docs/traceability.json`

```java
/**
 * 创建燃气合同
 * @ontology object=gas_contract behavior=CREATE
 * @brd req=FR-003
 * @rule profit_calc
 */
public ServiceResult<GasContractVO> createGasContract(GasContractCreateVO vo) {
```

```json
// docs/traceability.json
{
  "objects": {
    "gas_contract": {
      "CREATE": {
        "controller": "GasContractController.createGasContract()",
        "biz": "GasContractBizService.createGasContract()",
        "service": "GasContractService.insertGasContract()"
      }
    }
  },
  "rules": {
    "profit_calc_rule": "GasContractService.calculateProfit()"
  },
  "sops": {
    "approval_flow": "GasContractBizService.executeApprovalFlow()"
  }
}
```

**`code-verification/SKILL.md` 调整**：

- 步骤3"功能完整性对照"改为**读 `traceability.json` 做确定性匹配**，不再靠方法名模糊匹配
- 增加"步骤6：缺陷根因识别与回流"——区分设计层缺陷与实现层缺陷，触发对应阶段局部修订

---

## 3. 调整路线图

### 第一波：补阶段 + 契约化（高价值，高影响）

| 调整项 | 涉及文件 | 工作量评估 |
|--------|---------|-----------|
| `code-generation` 前加 impl-plan 子阶段 | `code-generation/SKILL.md` | 中等（拆步骤0出来） |
| `app-design` 增加契约产物 | `app-design/SKILL.md` + 新增 `contracts/` | 中等（需定义 yaml 格式） |
| 删除 `brd-generation`，合并入 `ontology-modeling` | 删 skill + 改 manifest | 小 |

### 第二波：追溯 + 验证闭环（中价值，中影响）

| 调整项 | 涉及文件 | 工作量评估 |
|--------|---------|-----------|
| 代码标注来源 ID + traceability.json | `code-generation/SKILL.md` 步骤1 | 中等 |
| 验证改为确定性匹配 + 缺陷回流 | `code-verification/SKILL.md` | 中等 |

### 第三波：迭代治理（逐步完善）

| 调整项 | 涉及文件 | 工作量评估 |
|--------|---------|-----------|
| 变更影响分析 | `or-workflow-guide/SKILL.md` | 大 |
| 进度账本记录产物版本哈希 | `or-workflow-guide/SKILL.md` | 小 |
| 运行时统一 | `or-workflow-guide/agents/openai.yaml` | 需评估 |

---

## 4. 调整后 SDD 四步骤流程图

```
用户请求
   ↓
┌─────────────────────────────────────┐
│ ① Requirements（需求规格）           │
│    ontology-modeling                 │
│    产出：ontology_schema.json       │
│         + docs/brd.md               │
│    门禁：需求收敛确认                │
└──────────────────┬──────────────────┘
                   ↓
┌─────────────────────────────────────┐
│ ② Design（详细设计）                 │
│    app-design                        │
│    产出：docs/app-design.md          │
│         + contracts/db-schema.sql   │
│         + contracts/app-contract.yaml│
│    门禁：设计审批 + 映射覆盖率100%    │
└──────────────────┬──────────────────┘
                   ↓
┌─────────────────────────────────────┐
│ ③ Tasks（任务分解） ← ★ 补上 ★      │
│    code-generation 步骤0（独立阶段）  │
│    产出：docs/impl-plan.md           │
│    门禁：用户审查确认                │
└──────────────────┬──────────────────┘
                   ↓
┌─────────────────────────────────────┐
│ ④ Implementation（实现+验证）        │
│    code-generation 步骤1-3           │
│    产出：可运行代码                  │
│         + docs/traceability.json    │
│    code-verification                 │
│    产出：验证报告                    │
│    闭环：缺陷回流到对应阶段规格       │
└─────────────────────────────────────┘
```

---

## 5. 关键决策点

### 5.1 Tasks 阶段怎么实现？

有三个选项，按推荐顺序排列：

| 选项 | 做法 | 优点 | 缺点 |
|------|------|------|------|
| **A. code-generation 内部拆出步骤0**（推荐） | 不改 skill 结构，在 code-generation 入口增加"生成实现计划"子阶段 | 改动最小，产出可立即用 | impl-plan 不是独立 skill，复用性差 |
| **B. or-workflow-guide 新增 spec-execute 路由** | 在路由中加一层 spec-execute，类似 claude-code-spec-workflow | 对齐社区实践 | 改动大，需新增 skill 或 agent |
| **C. 新建独立的 task-planning skill** | 新建 skill 专门做 impl-plan | 职责最清晰 | 新增维护成本 |

**建议先用 A**，快速闭环验证，后续需要时再演进到 B 或 C。

### 5.2 契约化到什么程度？

| 程度 | 做法 | 适用时机 |
|------|------|---------|
| **轻量** | 仅约定 `app-contract.yaml` 的 JSON Schema，由 LLM 生成 | 立即可用，改造成本低 |
| **重量** | 用 OpenAPI 3.0 定义接口 + 用 JSV 做契约校验 | 高成熟度时引入 |

**建议先用轻量**：在当前结构上给 app-design 增加 yaml 产出 + 模板，后续逐步升级。

---

## 6. 与现有文档的关系

本文聚焦"基于四步 SDD 的调整路径"，与已有文档分工：

| 已有文档 | 关系 |
|---------|------|
| `sdd-four-phase-analysis.md` | 纵深问题诊断（9个问题的详细分析） |
| `skills-optimization-plan.md` | 第一轮优化方案（已落地大部分 P0/P1） |
| **本文（新）** | 基于四步 SDD 给出具体调整步骤和路径图 |

**下一步**可以先从第一波的三个调整项开始，我这边直接给你落地代码改动。
