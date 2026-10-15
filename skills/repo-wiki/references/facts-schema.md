# 事实层 Schema（wiki_facts.json）

> `build_facts.py` 生成的 `.repo-wiki/wiki_facts.json` 是 wiki 生成流程的统一事实层。
> 结构生成和页面生成消费此文件，而非直接消费多个原始扫描结果。

## 顶层结构

```json
{
  "schema_version": 1,
  "repository": {
    "path": "/abs/repo/path",
    "branch": "main",
    "git_commit": "abc123",
    "dirty": false
  },
  "build": {
    "system": "maven",
    "multi_module": true
  },
  "scan_mode": "git",
  "graph": {
    "cbm_commit": "abc123",
    "cbm_version": "0.10.0"
  },
  "facts": [ ... ],
  "facts_hash": "82215fd2c89e370e",
  "conflicts": [ ... ],
  "summary": {
    "total_facts": 42,
    "by_type": {"observed": 35, "inferred": 5, "repository_rule": 2},
    "by_category": {"module_dependency": 8, "endpoint_inbound_http": 12, ...},
    "conflicts": 0
  }
}
```

## 事实记录结构

每条事实是一个独立 JSON 对象：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 稳定 ID，格式 `fact.{category}.{name}`，支持增量比较和验证引用 |
| `type` | string | `observed` / `repository_rule` / `inferred` / `planned` / `recommendation` |
| `category` | string | 事实分类，如 `module_dependency` / `endpoint_inbound_http` / `architecture` |
| `value` | any | 事实值（字符串、布尔、数组、对象均可） |
| `evidence` | array | 证据列表，每条含 `source`（文件/扫描器/事实ID）、`signal`（匹配信号）、可选 `line`；`source=graph` 的事实必须为每条证据提供仓库相对源码路径和正整数行号 |
| `confidence` | float | 置信度 0.0-1.0。`observed` 和 `repository_rule` 通常为 1.0；`inferred` 根据信号数量调整 |

图谱事实额外使用 `source: "graph"` 标识来源。只有 CBM 提取成功、未降级且事实通过证据校验时才会进入 `facts`；此时顶层才出现 `graph.cbm_commit` / `graph.cbm_version`。CBM 不可用或未产生有效事实时，输出与未启用 CBM 的基线保持一致。

## 事实类型

| 类型 | 含义 | 示例 |
|---|---|---|
| `observed` | 来自源码或可执行配置的当前事实 | 某模块 packaging=jar |
| `repository_rule` | 来自 AGENTS.md 等仓库约束文件 | 跨模块调用必须通过 facade |
| `inferred` | 根据多个 observed 事实推导 | 唯一部署物是 web 模块 |
| `planned` | 设计文档中计划但源码尚未实现 | 规划中的服务拆分 |
| `recommendation` | Wiki 给出的建议，不代表现状 | 建议增加幂等键 |

## 事实 ID 约定

```
fact.module.{module_id}.depends_on
fact.module.{module_id}.runtime_role
fact.module.{module_id}.is_deployable
fact.module.{module_id}.is_placeholder
fact.module.{module_id}.entry_point.{entry}
fact.endpoint.{type}.{file}:{line}
fact.rule.{rule_file}.{heading}
fact.assertion.single_deployable
fact.assertion.multi_module
fact.assertion.entry_point_summary
fact.assertion.scan_mode
```

## 冲突检测

当两条事实有相同 ID 但不同的 value 时，记录到 `conflicts` 数组：

```json
{
  "fact_id": "fact.module.web.runtime_role",
  "conflicting_values": ["service", "library"],
  "evidence": [[...], [...]]
}
```

冲突事实不阻断生成，但在验证阶段以醒目标记进入待确认清单。

## facts_hash

`facts_hash` 是所有事实 ID + value 的确定性 SHA-256 前 16 位。写入 meta.yaml v2 的 `generator.facts_hash`。当事实层变化时（如模块依赖新增），facts_hash 变化，触发受影响页面重生成。

## 消费方式

- **结构生成（步骤 3）**：读取 `wiki_facts.json`，使用 `facts` 数组中的 observed/inferred 事实作为结构规划依据，不直接在原始扫描结果之间自由推断
- **页面生成（步骤 4）**：主执行者按页面 `filePaths` 与 evidence.source 的交集筛选事实子集，并追加到页面提示词；页面 agent 不直接查询 CBM
- **验证（步骤 6）**：检查关键断言（如 `single_deployable`）是否通过，冲突事实是否已处理
