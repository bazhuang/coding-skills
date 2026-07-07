# 规格变更处理（迭代重生成）细则

完整流水线是「一次性线性」的——上游规格改一处，下游不会自动跟着改。本分支定义：上游产物变化时，计算 diff → 生成受影响产物清单 → 仅重生成受影响部分，而非整条流水线重跑。「轻量模式」通道的小型变更也走本分支。

## 触发条件

- **用户声明变更**：如「给本体加一个对象」「合同规则改了」「需求 F-003 改为 Should Have」。
- **恢复时检测漂移**：会话恢复时重新计算各权威规格制品指纹，若与 `docs/sdd-state.yaml` 中 `generated_against` 记录的不一致（旧项目兼容 `docs/spec-versions.json`），判定对应下游已落后于规格，主动提示用户。
- **分诊为轻量模式**：已有 SDD 项目上影响面可列全的小型功能变更。

## 变更处理 4 步

1. **确认变更**：对声明变更的权威规格制品重算 sha256 指纹（`shasum -a 256 docs/<artifact>`），与 `docs/sdd-state.yaml`（旧项目兼容 `docs/spec-versions.json`）比对，确认确实变化并定位到具体制品。
2. **分类 diff**：按稳定 code 分类变更——新增/删除/修改的 `object` code、`rule` code、`SopFlow` code、需求 `F-xxx`、对象 `behavior`。稳定 code 是变更影响的锚点。
3. **生成受影响产物清单**：用下方传播表定位受影响的下游阶段，再以 `docs/traceability.json` 把 spec code 映射到具体类/方法，得到精确到文件/方法的重生成清单。
4. **增量重生成 + 更新账本**：仅对受影响阶段触发重生成（code-generation 走「规格变更增量」模式），完成后更新 `docs/sdd-state.yaml` 的指纹、`generated_against` 与阶段状态。

> **轻量模式合并审批**：分诊为「轻量模式」时，把步骤 1–3 的结果（spec-diff、受影响契约条目、精确到类/方法的重生成清单）合成**一条**审批消息，用户确认一次后直接执行步骤 4 并进入针对受影响部分的增量验证（验证仅针对受影响部分执行规范合规与功能对照，其余按需），不再逐阶段暂停审批。

## 受影响产物传播表

| 上游变更的制品 | 受影响、需重生成的下游 |
|---|---|
| `docs/ontology_schema.json` / `docs/requirements-baseline.json` | app-design（重生成契约 + DDL）→ code-generation（增量）→ code-verification |
| `docs/contracts/app-contract.yaml` / `docs/contracts/db-schema.sql` | code-generation（增量）→ code-verification |
| 代码 / `docs/traceability.json` | code-verification |

> 上游规格若回退（如删除某对象），同样走本分支：受影响代码按删除/隔离处理，并更新 `traceability.json` 与 `sdd-state.yaml`。`acceptance-tests.yaml` 若存在，由 `requirements-baseline.json` 重新导出，不单独触发变更传播。
