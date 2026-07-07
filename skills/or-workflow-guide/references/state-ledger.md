# SDD 进度账本细则

对话压缩后内存会丢失，没有持久化记录会导致重复执行已完成的阶段。结构化进度账本是跨会话恢复的依据。本文件是账本的格式、恢复、自愈与门禁核对的完整细则；阶段键与 status/gate 枚举的权威定义见 SKILL.md「进度账本」一节。

## 文件位置

- **首选**：`docs/sdd-state.yaml`，格式见 `sdd-state.example.yaml`。
- **兼容**：`docs/workflow-progress.md`。旧项目只有该文件时仍可读取恢复；新项目可把它作为人读摘要，不作为机器恢复首选。

## 账本格式

首选格式为 `docs/sdd-state.yaml`：

- 顶层记录 `schema_version`、`updated_at`、`baseline_version`、`artifact_policy`；如有历史场景归档，另有 `archives:` 列表（由 sdd-archive skill 追加，每条含 `scenario`/`path`/`archived_at`/`baseline_version`/`trigger`，只增不删）。`docs/archive/index.md` 是 `archives:` 的人读镜像，不一致时以账本为准。
- `stages.<阶段键>` 记录 `status`、`gate`、`substage`、`artifacts`、`fingerprints`、`generated_against`、`coverage`、`waiver`。
- `fingerprints` 只记录权威规格和实现证据，不记录人读派生视图，避免派生文档改写造成无意义漂移。

> `status=complete` **当且仅当** `gate=passed`；二者绑定，不要写「complete 但 gate=failed」这类矛盾组合。阶段内的细粒度进度（如「impl-plan 已批准但代码尚未生成完」）不要塞进 `gate`，记入阶段专属字段 `substage`。

兼容旧格式时，每阶段一行仍可读：`<标识符>: <status> (gate=<枚举>, 其余为阶段专属自由括注)`。

```
ontology_modeling: complete (gate=passed, objects=8 rules=5, 产物=ontology_schema.json+brd.md+requirements-baseline.json, 可选导出=contracts/acceptance-tests.yaml)
app_design: complete (gate=passed, 覆盖率=对象8/8 行为40/40 规则5/5 SOP3/3, 产物=app-design.md+contracts/{db-schema.sql,app-contract.yaml})
code_generation: in_progress (gate=failed, substage=impl-plan-approved, 已生成对象=6/8, 计划已确认，骨架3/填充中)
code_verification: pending
```

> **向后兼容**：旧格式仍可被读取恢复——
> - 旧中文键（`本体建模`/`应用设计`/`代码生成`/`代码验证`）按 SKILL.md 阶段标识符表映射回标识符；
> - 旧值 `gate=impl-plan-approved` 视为代码生成阶段的子进度，归一为 `gate=failed, substage=impl-plan-approved`（impl-plan 已批准但代码未全量生成 = 门禁未通过）；
> - `status=in progress`（带空格）归一为 `in_progress`；
> - `gate`/`产物` 字段缺失时按「未记录」处理，触发恢复时门禁重检（见下）。

## `waived` 状态（跳阶段风险豁免）

当用户明确选择跳过某阶段（如「直接做应用设计，不做本体建模」「跳过设计，基于已有代码增量」）时，记录 `waived`（`gate=n/a`）而非裸 `complete`/`pending`，并补 4 个结构化字段，使下游能据此降低承诺：

```
ontology_modeling: waived (gate=n/a, reason=用户已有遗留库表与接口仅做增量适配; missing=ontology_schema.json,requirements-baseline.json; risk=高: 契约覆盖率/代码追溯无保障; remediation=后续补建模或手写契约后回到 complete)
app_design: complete (gate=passed, 覆盖率=对象8/8 行为40/40 规则5/5 SOP3/3, 产物=app-design.md+contracts/{db-schema.sql,app-contract.yaml})
code_generation: pending
```

`waived` 字段含义：`reason`（跳过原因）/ `missing`（因此缺失的产物）/ `risk`（风险等级与说明）/ `remediation`（补齐建议）。下游阶段（app-design / code-generation / code-verification）启动时若读到上游为 `waived`，必须**降低自动化承诺**（如 code-generation 提示「非完整 SDD 输入，追溯完整无保障」），不得假装完整 SDD 输入。

## 规格版本记录（迭代重生成依据）

每阶段完成时，or-workflow-guide 同步把当时权威规格制品的 sha256 指纹写入 `docs/sdd-state.yaml` 的 `fingerprints` / `generated_against`。旧项目可继续写 `docs/spec-versions.json`（格式见 `spec-versions.example.json`），但它是兼容制品；若同时存在，以 `docs/sdd-state.yaml` 为准。

指纹范围只包含权威规格：`ontology_schema.json`、`requirements-baseline.json`、`contracts/app-contract.yaml`、`contracts/db-schema.sql`。`brd.md`、`app-design.md`、`acceptance-tests.yaml` 等派生视图不参与漂移判定。

## 账本规则

- **由 or-workflow-guide 统一管理**：各个 skill 只负责执行自己的流程，不知道账本的存在。or-workflow-guide 在每个 skill 执行完毕或中断时，负责写入和更新 `sdd-state.yaml`，必要时同步更新 `workflow-progress.md` 人读摘要
- **阶段完成后同步更新**：在标记阶段完成的同时，同一轮操作中写入账本
- **压缩后信任账本**：不信任自己的记忆，以账本记录为准

## 启动恢复决策树

优先读取 `docs/sdd-state.yaml`；不存在时读取 `docs/workflow-progress.md` 兼容格式，按顺序判定第一个待处理阶段：

1. **指纹漂移优先**：先重新计算各权威规格制品指纹，与 `docs/sdd-state.yaml` 的 `generated_against` 比对（旧项目兼容 `docs/spec-versions.json`）。任一下游相对上游漂移 → 走「规格变更处理」分支（见 `spec-change.md`），**不**走普通恢复。
2. 遍历阶段，对第一个非 `complete` 的阶段，按其 `status`/`gate` 处置：
   - `pending` → 从该阶段开始执行。
   - `in_progress` 且 `gate=passed` → 异常状态（complete 才允许 gate=passed），回该阶段重检门禁。
   - `in_progress` 且 `gate∈{failed,blocked}` 或 gate 缺失 → **回该阶段补门禁**，不从下游续跑。
   - `waived` → 视为**已放行**，跳过不重跑；但必须向用户复述其 `risk`/`remediation`，并在进入下游时执行降级承诺。
   - `in_progress` 且 `gate=n/a` → 视同 `waived` 处置。
3. 已 `complete` 的阶段绝不重复执行。

可选快速体检：需要交付前检查状态文件和关键制品是否齐全时，可运行 `python3 skills/or-workflow-guide/scripts/sdd_doctor.py`。它只做轻量存在性、JSON 解析和基本形状检查，不替代各阶段准出门禁。

## 账本自愈（账本与制品不一致时）

恢复时以**实际制品存在性 + 指纹**校验账本，不盲信账本字面值：若账本写 `complete` 但关键产物缺失/指纹不匹配，**以制品为准**，将该阶段降为 `in_progress`/`gate=failed` 并提示用户；反之产物齐全而账本写 `pending`，据实升级。自愈改动须同步写回账本。

## 各阶段准出标准（gate=passed 的判定依据）

只有准出门禁通过才在账本写 `gate=passed` 并放行下游。各 skill 负责执行自己的门禁，or-workflow-guide 在 skill 执行完毕后核对门禁结果并写入账本：

| 标识符 | 准出门禁（全满足才 `gate=passed`） | 不通过的后果 |
|------|---------|-------------|
| `ontology_modeling` | `ontology_schema.json` 通过 `validate_ontology.py` 校验；每个 Must Have 功能有稳定 ID + 可测试验收标准 + 来源 code；产出并批准 `requirements-baseline.json`。如需自动验收，可从 baseline 导出 `contracts/acceptance-tests.yaml` | 不得进入 app_design |
| `app_design` | `app-contract.yaml` 覆盖 `ontology_schema.json` 的对象/行为/规则/SOP 达 **100%**；`db-schema.sql` 可执行；契约与 `app-design.md` 一致 | 不得进入 code_generation（单向依赖，这是最后补救点） |
| `code_generation` | `impl-plan.md` 已获用户审查批准（记 `substage=impl-plan-approved`）**且**代码全量生成完成；代码方法带 `@ontology/@brd/@rule` 标注；产出符合 `code-verification/references/traceability.schema.json` 的 `traceability.json`。仅 impl-plan 批准而代码未生成完 → `gate=failed` | 不得进入 code_verification |
| `code_verification` | Critical 问题清零（自动修复后重检）；Important 问题已分类为 `[spec-gap]`/`[impl-gap]` 并给出回流建议 | 不阻断交付，但待处理事项须回流对应阶段 |

> **跳过阶段（灵活分支）**用 `waived` 状态记录（`gate=n/a`）：必须带 `reason`/`missing`/`risk`/`remediation` 四字段。下游若读取到上游为 `waived`，或某阶段 `gate∈{failed,blocked}`/缺失，必须**降低自动化承诺并提示用户**（如追溯完整无保障、覆盖率无法核对）。`waived` 不等于 `complete`——它明确表达「这一环的保障被豁免了」。
