# 本体到代码映射规则

从 ontology-modeling 的本体三要素（对象、行为、规则）推导到应用设计和代码结构的映射规则。设计时必须严格遵循，确保行为和规则不丢失，完整传导至代码层面。

## 行为到接口映射

每个核心对象的 5 类行为分别映射为接口层端点。接口层在 Java 中是 Controller，在 Python 中是 API Router。

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

## SOP 流程到 Biz 编排方法映射

一个 SOP 流程对应一个 Biz 方法，方法内部按步骤依次调用对应的 Service。

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

## 设计文档中的映射表达

映射规则有两种产出形态，二者必须保持一致——**结构化契约是权威源，Markdown 表格是其人类可读视图**。

### 形态一：结构化契约 `docs/contracts/app-contract.yaml`（权威、机器可消费）

三张映射规则物化为契约字段，供下游 `code-generation` **确定性解析**（而非读 Markdown 自由推导）：

| 映射规则 | 契约字段 |
|---------|---------|
| 行为→接口映射（上文） | `objects[].behaviors[]`：`type`(CREATE/UPDATE/QUERY/DELETE/DERIVE) / `controller` / `biz` / `service` |
| 规则→代码逻辑映射（上文） | `rules[]`：`code` / `source`(ontology/design) / `type`(CALCULATION/CONSTRAINT/CROSS_ENTITY) / `location`(类.方法()) |
| SOP→Biz 编排映射（上文） | `sops[]`：`code` / `bizMethod`(类.方法) / `calls`[](按步骤顺序的 Service 方法) |

契约模板与字段约束见同目录 `app-contract-template.yaml` 与 `app-contract.schema.json`。

命名必须与 `project.backend.language` 一致：Java 使用 PascalCase 类名和 camelCase 方法名；Python 使用 PascalCase schema/model 名和 snake_case 函数名。契约字段名保持 `controller` / `biz` / `service` 不变，用于表达逻辑角色，不要求 Python 代码中存在 Controller 类。

### 形态二：Markdown 三张映射表（人读视图，写入 `docs/app-design.md`）

在 `docs/app-design.md` 的接口设计部分，必须包含以下三张映射表（与契约字段一一对应，便于人工评审）：

1. **行为→接口映射表**：每个对象的每个行为对应哪个 Controller 接口、Biz 方法、Service 方法
2. **规则→代码位置映射表**：每条规则对应哪个层级、哪个方法名
3. **SOP→Biz 编排方法映射表**：每个 SOP 流程对应哪个 Biz 方法，内部调用哪些 Service 方法

### 准出门禁

`app-contract.yaml` 中 `objects` / `rules` / `sops` 的 `code` 必须与 `docs/ontology_schema.json` 的 `objects` / `rules` / `sop_flows` 的 `code` **逐项对齐**，覆盖率不达 100% 不得进入下游（详见 app-design SKILL.md「规范自审」第 7 项）。
