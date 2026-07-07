---
name: sdd-archive
description: "SDD 产物归档：当一个需求场景完成交付（code-verification 通过）、开始新需求场景前、或用户要求整理/归档 docs 产物时使用。按需求场景在 docs/archive/ 下创建归档目录，快照当时的权威规格与派生视图、移入一次性过程产物，保持 docs/ 根目录只保留活跃权威制品，不破坏下游 skill 的固定读取路径。"
---

# SDD 产物归档

SDD 流水线每轮会在 `docs/` 下产生十余份产物。多个需求场景迭代后，`docs/` 根目录会堆积过期的 impl-plan、验证报告和历史版本，与活跃权威规格混在一起。本 skill 把**已完成场景**的产物收敛到按场景组织的归档目录，让 `docs/` 根目录始终只有「当前活跃制品」。

产物按生命周期分两类，处理方式不同：

| 类别 | 性质 | 例子 | 归档策略 |
|---|---|---|---|
| **系统态** | 累积演进，描述系统当前全貌，是下一场景的增量基础 | `ontology_schema.json`、`app-contract.yaml`、`db-schema.sql`、`traceability.json`、`requirements-baseline.json` | **原位不动，只快照复制**；按场景拆散会迫使下游回读多个归档重建全貌 |
| **轮次态** | 每场景一轮，交付即完结 | BRD 的场景需求章节、baseline 中已交付的 F-xxx、`impl-plan.md`、验证报告 | **归档 + 索引引用**；这是膨胀与干扰的来源 |

<HARD-GATE>
归档**绝不移动**权威规格（`ontology_schema.json`、`requirements-baseline.json`、`contracts/app-contract.yaml`、`contracts/db-schema.sql`）、当前有效的 `traceability.json` 和账本 `sdd-state.yaml` 本体——它们是下游 skill 按固定路径消费的活跃制品，只做**快照复制**。只有一次性过程产物才做**移动**。
</HARD-GATE>

## 触发时机

| 场景 | 行为 |
|---|---|
| code_verification 完成（gate=passed 或用户确认交付） | 建议归档本场景，用户确认后执行 |
| 用户在已有完整产物的项目上提出**新需求场景** | 先建议归档上一场景，再开始新场景 |
| 用户明确要求「归档 / 整理 docs 产物」 | 直接执行 |
| 规格变更迭代完成一轮 | 可选：归档该轮迭代快照（同一场景目录下的 `iterations/` 子目录） |

## 归档目录结构

```
docs/
├── ontology_schema.json            # 活跃权威规格（不动）
├── requirements-baseline.json      # 活跃权威规格（不动）
├── contracts/                      # 活跃契约与 DDL（不动）
├── traceability.json               # 当前有效实现证据（不动）
├── sdd-state.yaml                  # 账本（不动，追加 archives 记录）
├── brd.md / app-design.md / ...    # 活跃派生视图（brd.md 收敛为主文档+历史场景索引，见下）
└── archive/
    ├── index.md                    # 人读归档索引（本 skill 自动维护；机器权威仍是账本 archives:）
    └── <YYYY-MM-DD>-<场景slug>/
        ├── manifest.yaml           # 归档清单（见下）
        ├── specs/                  # 权威规格快照（复制）
        ├── views/                  # 派生视图快照（复制：brd.md、app-design.md、db-schema.md、acceptance-tests.yaml）
        ├── process/                # 一次性过程产物（移动：impl-plan.md、spec-diff 记录、workflow-progress.md 旧摘要）
        ├── evidence/               # 实现证据快照（复制 traceability.json；移动验证报告）
        └── iterations/             # 可选：同场景后续规格变更的轮次快照
```

**场景 slug 判定**（按序取第一个可用）：

1. 用户指定的场景名；
2. `requirements-baseline.json` 的场景/域名称字段；
3. `ontology_schema.json` 的 `domain`；
4. 询问用户（一句话，给推荐值）。

slug 用小写连字符（如 `gas-monthly-matching`），目录名前缀归档日期。

## 移动 vs 复制（对齐产物分层）

| 产物类型 | 处理 | 说明 |
|---|---|---|
| 权威规格（4 件） | **复制**到 `specs/` | 原位保留，下游继续按 `docs/<artifact>` 消费 |
| `brd.md` | **复制**到 `views/`，随后**收敛原位文件** | 完整快照进归档；原位 brd.md 保留系统态章节（§1-§3、§5-§10），§4 中本场景需求细节收敛为一行摘要，并在「历史场景索引」章节追加引用（见下节） |
| `requirements-baseline.json` | **复制**到 `specs/`，随后**标记原位条目** | 原位文件不搬走（code-verification 全系统对照依赖它）；本场景 `requirements[]` 逐条打上 `"status": "delivered"` 和 `"scenario": "<slug>"` |
| 其余派生视图（app-design.md、db-schema.md、acceptance-tests.yaml） | **复制**到 `views/` | 原位保留供当前迭代阅读；若开始全新场景，原位版本将被新场景覆盖，归档即历史底稿 |
| `impl-plan.md` | **移动**到 `process/` | 审查型过程产物，批准并生成完即失效 |
| 验证报告（`verification-report*.md` 等） | **移动**到 `evidence/` | 一次性交付证据 |
| spec-diff / 变更记录（如有落盘） | **移动**到 `process/` | 变更处理的过程记录 |
| `traceability.json` | **复制**到 `evidence/` | 活跃证据，快速通道漂移反查和增量重生成仍需要原位文件 |
| `sdd-state.yaml` | 不动；**追加** `archives:` 记录 | 唯一状态真相源 |
| `workflow-progress.md`（旧人读摘要） | **移动**到 `process/`（若用户不再需要兼容） | 移动前确认项目无旧运行时依赖 |

## BRD 收敛与归档索引

**原位 brd.md 的收敛**（归档时执行，保持 BRD 精简、消除新旧场景混杂）：

1. 系统态章节（§1 概述、§2 范围、§3 干系人、§5 流程、§6 数据、§7 规则等描述系统全貌的部分）原位累积维护，不删；
2. §4 功能需求中**本场景**的需求明细收敛为一行摘要（保留 F-xxx 编号区间与场景名），完整明细以归档快照为准；
3. 在 BRD 末尾的「历史场景索引」章节追加一行：

   ```markdown
   ## §11 历史场景索引

   | 场景 | 交付日期 | 需求范围 | 详情 |
   |---|---|---|---|
   | 月度需供匹配 | 2026-06-30 | F-001~F-008 | [归档 BRD](archive/2026-06-30-gas-monthly-matching/views/brd.md) |
   ```

**`docs/archive/index.md` 人读索引**（每次归档追加一行，与账本 `archives:` 保持一致）：

```markdown
# 归档索引

| 场景 | 归档日期 | 触发 | baseline | 路径 |
|---|---|---|---|---|
| gas-monthly-matching | 2026-07-07 | verification-complete | v1.0 | [2026-07-07-gas-monthly-matching](2026-07-07-gas-monthly-matching/) |
```

> 机器可读权威是 `sdd-state.yaml` 的 `archives:` 列表；index.md 只是它的人读镜像，两者由本 skill 同步维护，不一致时以账本为准。

**`requirements-baseline.json` 的场景标记**：本场景 Must Have 交付后，为对应条目补 `"status": "delivered"` 与 `"scenario": "<slug>"`。新场景的 F-xxx 编号在既有最大编号后继续递增，**不复用已交付编号**。code-verification 默认只对照未标 `delivered` 的需求，全量回归时才对照全部。

## manifest.yaml 格式

```yaml
scenario: gas-monthly-matching
archived_at: "2026-07-07T19:30:00+08:00"
baseline_version: "v1.0"
trigger: verification-complete        # verification-complete | new-scenario | manual | iteration
stages_snapshot:                      # 归档时各阶段状态（来自 sdd-state.yaml）
  ontology_modeling: "complete/passed"
  app_design: "complete/passed"
  code_generation: "complete/passed"
  code_verification: "complete/passed"
fingerprints:                         # 归档时权威规格指纹（sha256 前 16 位）
  ontology_schema.json: "a1b2c3d4e5f6a7b8"
  requirements-baseline.json: "1122334455667788"
  contracts/app-contract.yaml: "ccddeeff00112233"
  contracts/db-schema.sql: "445566778899aabb"
files:
  copied: [specs/ontology_schema.json, views/brd.md, evidence/traceability.json]
  moved: [process/impl-plan.md, evidence/verification-report.md]
```

## 执行流程

1. **前置检查**：读取 `docs/sdd-state.yaml`。若 `code_verification` 非 `complete` 且非用户强制归档，提示「场景尚未完成验证，归档的是中间状态」并让用户确认；若无账本，按实际存在的产物归档并注明 `stages_snapshot: unknown`。
2. **确定场景 slug 与触发类型**，创建 `docs/archive/<YYYY-MM-DD>-<slug>/` 及子目录（只建实际用到的子目录）。
3. **计算指纹**：对 4 件权威规格重算 sha256（存在的才算）。
4. **复制/移动**：按上表执行；同名归档目录已存在时不覆盖，改用 `iterations/<序号>-<日期>/` 或询问用户。
5. **收敛轮次态**：按「BRD 收敛与归档索引」节收敛原位 `brd.md`、标记 baseline 条目 `delivered`、追加 `docs/archive/index.md` 一行。
6. **写 manifest.yaml**，列全 copied/moved 清单。
7. **更新账本**：在 `docs/sdd-state.yaml` 顶层 `archives:` 列表追加一条：

   ```yaml
   archives:
     - scenario: gas-monthly-matching
       path: archive/2026-07-07-gas-monthly-matching
       archived_at: "2026-07-07T19:30:00+08:00"
       baseline_version: "v1.0"
       trigger: verification-complete
   ```

7. **汇报**：告知用户归档路径、移动/复制文件数、收敛动作（BRD 章节、delivered 标记、index.md），以及 `docs/` 根目录当前剩余的活跃制品清单。

## 开始新场景时的衔接

归档由 or-workflow-guide 在新场景启动前建议执行。归档完成后：

- **系统态制品**（`ontology_schema.json`、`contracts/*`、`traceability.json`、`requirements-baseline.json`）在原位继续累积演进——新场景是在已有系统模型上的增量，不是从零重建；
- `brd.md` 已收敛为「系统态章节 + 历史场景索引」，新场景的需求明细写入 §4，交付后再收敛；
- `sdd-state.yaml` 的 `stages` 重置为新场景的 `pending`，`baseline_version` 递增，`archives` 保留全部历史；
- 历史场景查询、回溯、对比一律指向 `docs/archive/<场景>/`，入口是 `archive/index.md` 或账本 `archives:`。

## 关键原则

- **系统态原位累积，轮次态归档引用**：权威规格永不按场景拆散；BRD 场景章节、impl-plan、验证报告等轮次态产物归档后以索引引用
- **活跃制品原位不动**：下游 skill 的固定读取路径（`docs/ontology_schema.json`、`docs/contracts/*` 等）永不因归档失效
- **移动仅限一次性过程产物**：impl-plan、验证报告、spec-diff 记录；拿不准就复制不移动
- **manifest 是归档的确定性索引**：查历史不靠翻目录，先读 manifest
- **账本是归档记录的权威源**：`archives:` 列表挂在 `sdd-state.yaml`；`archive/index.md` 只是人读镜像
- **不归档不属于 SDD 产物的文件**：`docs/` 下用户自己的文档不碰
