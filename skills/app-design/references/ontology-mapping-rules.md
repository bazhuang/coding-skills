# 本体到应用表面映射规则

从 ontology-modeling 的本体三要素（对象、行为、规则）推导到应用设计和实现表面的映射规则。设计时必须严格遵循，确保对象、行为、规则、SOP 不丢失，完整传导至契约层面。

## 通用追溯要求

- 每个 `objects[].code` 必须与 `docs/ontology_schema.json` 对齐。
- 每个对象的业务行为必须映射到目标应用的可实现表面：HTTP API、IPC、preload、renderer service、component、store、main helper、external API 等。
- 每个 `rules[].code` 必须映射到明确位置，格式可为 `Class.method()`、`Module.method()`、`Component.method()`、`file:function` 或 `ipc:channel`。
- 每个 `sops[].code` 必须映射到一个编排入口和按顺序排列的调用链。
- Markdown 表格只是人读视图，`docs/contracts/app-contract.yaml` 是权威结构化源。

## 后端行为到接口映射

`target_kind = backend-java` 或 `target_kind = backend-python` 时，每个核心对象的 5 类行为分别映射为接口层端点。接口层在 Java 中是 Controller，在 Python 中是 API Router。

| 行为类型 | HTTP 方法 | URL 模式 | Biz 方法模式 | Service 方法模式 |
|---------|----------|---------|-------------|-----------------|
| Create [C] | POST | /api/{object}/create | create{Object}() | insert{Object}() |
| Update [U] | POST | /api/{object}/update | update{Object}() | update{Object}() |
| Query [Q] | POST | /api/{object}/query | query{Object}() | select{Object}List() / select{Object}ById() |
| Delete [D] | POST | /api/{object}/delete | delete{Object}() | delete{Object}() |
| Derive [->] | POST | /api/{source}/derive{Target} | derive{Target}From{Source}() | 源对象 Service 查询 + 目标对象 Service 创建 |

**说明**：
- 所有接口统一使用 POST 方法（遵循技术规范）
- URL 使用小写+连字符的对象名（如 `/api/gas-contract/create`）
- Java 选择下：每个 Controller 方法必须有 `@Authorize` 注解，返回 `ServiceResult<VO>`，方法名使用 camelCase
- Python 选择下：每个 API Router 必须声明鉴权依赖，响应使用统一 Result 包装，方法名使用 snake_case

## 规则到代码逻辑映射

后端 target 使用下表。非后端 target 使用相同规则类型，但 `location` 可落到 renderer service、main helper、store、component 或文档流程节点。

| 规则类型 | 实现位置 | 实现方式 | 说明 |
|---------|---------|---------|------|
| 计算规则 | Service 层 | 独立方法，返回计算结果 | 计算是独立的业务逻辑，不涉及事务和编排 |
| 约束规则 | Biz 层 | 校验方法，不通过抛业务异常 | 约束校验通常在业务编排过程中执行，且可能涉及多对象 |
| 跨实体一致性 | Biz 层 | 事务内校验 | 必须在事务内校验，Biz 层负责事务管理 |

### Biz 层的典型编排模式

约束校验（约束规则）→ 调用 Service 计算（计算规则）→ 执行操作

Java 示例：

```java
public ServiceResult<ContractVO> createContract(ContractCreateVO vo) {
    // 1. 约束校验（约束规则 → Biz 层）
    validateContractConstraints(vo);

    // 2. 调用 Service 计算衍生字段（计算规则 → Service 层）
    BigDecimal profit = contractService.calculateProfit(vo);

    // 3. 执行创建
    ContractPO po = contractService.createContract(vo, profit);

    return ServiceResult.success(convertToVO(po));
}
```

Python 示例：

```python
def create_contract(vo: ContractCreateSchema) -> Result[ContractResponseSchema]:
    validate_contract_constraints(vo)
    profit = contract_service.calculate_profit(vo)
    contract = contract_service.create_contract(vo, profit)
    return Result.success(ContractResponseSchema.model_validate(contract))
```

## SOP 流程到编排方法映射

后端 target 中，一个 SOP 流程对应一个 Biz 方法，方法内部按步骤依次调用对应的 Service。非后端 target 中，一个 SOP 流程对应一个编排入口，`calls` 按 UI/service/IPC/helper/external 的真实顺序列出。

### 映射示例

```
SOP: 合同审批流程
  步骤1: 提交合同 → contractService.submitContract()
  步骤2: 审批合同 → contractService.approveContract()
  步骤3: 生效合同 → contractService.activateContract()

映射为 Biz 方法：
  contractBizService.executeApprovalFlow(contractId)
    → 依次调用 submitContract → approveContract → activateContract
```

### 条件分支

如果 SOP 有条件分支（如"审批不通过则退回"），在 Biz 方法中用 if-else 实现。

Java 示例：

```java
public ServiceResult<Void> executeApprovalFlow(Long contractId) {
    // 步骤1: 提交
    contractService.submitContract(contractId);

    // 步骤2: 审批
    ApprovalResult result = contractService.approveContract(contractId);

    // 条件分支
    if (result.isApproved()) {
        // 步骤3a: 审批通过 → 生效
        contractService.activateContract(contractId);
    } else {
        // 步骤3b: 审批不通过 → 退回
        contractService.rejectContract(contractId);
    }

    return ServiceResult.success(null);
}
```

Python 示例：

```python
def execute_approval_flow(contract_id: int) -> Result[None]:
    contract_service.submit_contract(contract_id)
    result = contract_service.approve_contract(contract_id)

    if result.is_approved:
        contract_service.activate_contract(contract_id)
    else:
        contract_service.reject_contract(contract_id)

    return Result.success(None)
```

### 说明

- SOP 的每一步可能跨越多个对象的行为，放在 Biz 层做编排
- 不需要独立的流程引擎，用 Biz 方法的顺序调用即可表达
- 一个 SOP 流程 = 一个 Biz 方法，保持可追溯性

## 非后端应用表面映射

非后端 target 使用 app-contract v2 的 `surfaces` 表达行为到应用表面的映射：

| 表面 | 示例 |
|---|---|
| `component` | `LoginPanel.onQrLoginClick` |
| `renderer` | `authService.startQrLogin`、`useAuthStore.setToken` |
| `preload` | `electron.auth.startQrLogin` |
| `ipc` | `auth:startQrLogin` |
| `main` | `startEnnewQrLogin` |
| `external` | `POST /userCenter/unify/auth/qr/create` |
| `route` | `/login` |
| `store` | `authStore.currentUser` |

Electron/Vue target 的细则见 `mapping-electron-vue.md`。

## 设计文档中的映射表达

映射规则有两种产出形态，二者必须保持一致：**结构化契约是权威源，Markdown 表格是其人类可读视图**。

### 形态一：结构化契约 `docs/contracts/app-contract.yaml`（权威、机器可消费）

所有 target 统一使用 v2 契约（`version: 2`）。后端 target（`backend-java` / `backend-python`）将三张映射规则物化为契约字段，供下游后端 `code-generation` **确定性解析**（而非读 Markdown 自由推导）：

| 映射规则 | 契约字段（v2 后端约定） |
|---------|---------|
| 行为→接口映射（上文） | `objects[].behaviors[]`：`type`(CREATE/UPDATE/QUERY/DELETE/DERIVE) / `surfaces.api`(接口 URL) / `surfaces.biz`(Biz 方法) / `surfaces.service`(Service 方法) |
| 规则→代码逻辑映射（上文） | `rules[]`：`code` / `source`(ontology/design) / `type`(CALCULATION/CONSTRAINT/CROSS_ENTITY) / `location`(类.方法()) |
| SOP→Biz 编排映射（上文） | `sops[]`：`code` / `entry`(Biz 编排类.方法) / `calls`[](按步骤顺序的 Service 方法) |

契约模板与字段约束见同目录 `app-contract-v2-template.yaml` 与 `app-contract-v2.schema.json`。后端 target 额外要求 `project.basePackage`。

命名必须与后端语言一致：Java 使用 PascalCase 类名和 camelCase 方法名；Python 使用 PascalCase schema/model 名和 snake_case 函数名。surfaces 键名 `api` / `biz` / `service` 表达逻辑角色，不要求 Python 代码中存在 Controller 类。

非后端 target 使用 `objects[].persistence`、`objects[].behaviors[].surfaces`（component/renderer/ipc/main/external 等键）、`rules[].location`、`sops[].entry` 和 `sops[].calls`。

> 旧 legacy 后端格式（无 `version` 字段，behaviors 用 `controller`/`biz`/`service` 平铺、SOP 用 `bizMethod`）已弃用：存量契约只读兼容，字段对应关系见 `app-contract-template.yaml` 头部注释。

### 形态二：Markdown 三张映射表（人读视图，写入 `docs/app-design.md`）

在 `docs/app-design.md` 的接口设计部分，必须包含以下三张映射表（与契约字段一一对应，便于人工评审）：

1. **行为→应用表面映射表**：每个对象的每个行为对应哪个接口、IPC、component、service、helper 或 external API
2. **规则→代码位置映射表**：每条规则对应哪个层级、哪个方法名
3. **SOP→编排方法映射表**：每个 SOP 流程对应哪个编排入口，内部调用哪些实现表面

### 准出门禁

`app-contract.yaml` 中 `objects` / `rules` / `sops` 的 `code` 必须与 `docs/ontology_schema.json` 的 `objects` / `rules` / `sop_flows` 的 `code` **逐项对齐**，覆盖率不达 100% 不得进入下游（详见 app-design `SKILL.md` 的「准出门禁」）。非后端契约不得被后端 code-generation 当作后端契约消费。
