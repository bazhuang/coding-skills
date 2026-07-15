# Requirements Gate

本文件定义 Requirements 阶段准出门禁。只有当用户准备进入下游 app-design / code-generation / code-verification，或要求标记 Requirements 阶段完成时读取。

## 目录

- G1. Schema 合法性校验
- G2. 稳定需求 ID
- G3. 需求基线 + 可选验收测试视图
- 用户确认与冻结锚点
- 准出回复

建模过程可以增量、边聊边产出，但**标记 Requirements 阶段「完成」之前，必须通过以下门禁**。门禁不通过不得进入下游 app-design。

## G1. Schema 合法性校验（硬门禁）

运行校验脚本（自包含、无需额外依赖）：

```bash
python3 skills/ontology-modeling/scripts/validate_ontology.py docs/ontology_schema.json
```

校验内容：

- 结构完整性。
- 各层级 `code` 唯一性。
- edge 的 `source_code` / `target_code` 引用完整性（无悬空指向）。
- 属性 `type` 枚举（仅 String / Integer / Double）。
- `code` 格式与长度。

退出码非 0（存在 ERROR）即未通过：必须修复后重跑，禁止带着已知错误放行。

字段约束详见 `references/ontology_schema.schema.json`（若环境装了 `jsonschema` 会自动附加结构校验）。

## G2. 稳定需求 ID（硬门禁）

BRD §4 中的每个 **Must Have（必须有）** 功能必须同时具备：

1. **稳定 ID**：形如 `F-001`，编号一旦分配不再变更。后续追溯、验收测试、变更影响分析都以此 ID 为锚点。
2. **可测试的验收标准**：能用“给定...当...则...”描述、可被验证的具体条件，而非“支持合同管理”这类模糊话术。
3. **来源 code**：标注其对应的本体 `object` / `behavior` / `rule` code（至少一项），实现需求 -> 本体 -> 代码的双向可追溯。

Should Have / Nice to Have 也建议补齐，但 Must Have 缺任一项视为门禁未过。

## G3. 需求基线 + 可选验收测试视图（产出物）

通过 G1/G2 后，必须产出一份确定性需求基线，供下游 app-design/code-verification 做确定性消费，而不是靠读 Markdown 自由发挥。验收测试 YAML 是由基线导出的派生测试视图，只有需要自动验收、接口冒烟或测试 runner 对接时才必须生成。

### `docs/requirements-baseline.json`

示例：

```json
{
  "baseline_version": "v1.0",
  "approved": false,
  "requirements": [
    {
      "id": "F-001",
      "title": "创建燃气合同",
      "priority": "MUST",
      "acceptance_criteria": ["创建后合同状态为草稿", "生成唯一合同号"],
      "source": { "object": "gas_contract", "behavior": "CREATE", "rules": ["profit_calc_rule"] }
    }
  ]
}
```

要求：

- `baseline_version` 初始可用 `v1.0`。
- `approved` 在用户确认前必须是 `false`。
- `requirements[]` 必须覆盖 BRD §4 的 Must Have 功能。
- `source` 至少包含 object / behavior / rules 中一项。
- `acceptance_criteria[]` 是验收条件的权威字段；下游若没有 `acceptance-tests.yaml`，直接使用本字段验收。
- **多场景迭代**：本文件跨场景累积，不按场景拆分。每条需求可带可选字段 `scenario`（场景 slug）与 `status`（`active` | `delivered`，缺省视为 `active`）；`delivered` 由 `sdd-archive` skill 在场景交付归档时标记。新场景的 F-xxx 编号在既有最大编号后递增，不复用已交付编号。

### `docs/contracts/acceptance-tests.yaml`

由 `requirements-baseline.json` 的 `acceptance_criteria[]` 派生：

```yaml
acceptance_tests:
  - requirement_id: F-001
    title: 创建燃气合同
    priority: MUST
    given: 一个合法的合同录入请求
    when: 调用 /api/gas-contract/create
    then: 返回成功且合同状态为草稿、生成唯一合同号
    source: { object: gas_contract, behavior: CREATE }
```

要求：

- 每个 Must Have 需求至少有一条 acceptance test。
- `requirement_id` 必须与 `requirements-baseline.json` 对齐。
- `given` / `when` / `then` 必须具体、可验证。
- 本文件不得引入 baseline 中没有的新需求或新验收口径；若发现需要新增验收口径，先修改并重新批准 `requirements-baseline.json`。

## 用户确认与冻结锚点

`approved` 字段在用户确认基线后置为 `true`，形成“已批准需求基线”，作为后续变更影响分析的比对起点。

基线批准（`approved=true`）的同时，由 or-workflow-guide 把当前权威规格制品指纹写入 `docs/sdd-state.yaml`（兼容旧项目时可同步 `docs/spec-versions.json`），其 `baseline_version` 与本基线版本一致。这是“规格变更处理”分支的比对起点；后续任何上游规格变更都以此版本为起点计算 diff 并仅重生成受影响下游。`acceptance-tests.yaml` 是派生视图，不单独作为漂移锚点。

## 准出回复

Gate 通过后，回复用户时包含：

- Schema 校验通过摘要。
- Must Have 需求覆盖数。
- 生成的 `requirements-baseline.json` 路径，以及是否导出了 `acceptance-tests.yaml`。
- 是否已由用户确认 `approved=true`。

Gate 未通过时，明确列出阻断项并修复，不进入下游。
