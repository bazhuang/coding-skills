# 本体到代码映射规则

从 ontology-modeling 的本体三要素（对象、行为、规则）推导到应用设计和代码结构的映射规则。设计时必须严格遵循，确保行为和规则不丢失，完整传导至代码层面。

## 行为到接口映射

每个核心对象的 5 类行为分别映射为 Controller 接口：

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
- 每个 Controller 方法必须有 `@Authorize` 注解，返回 `ServiceResult<VO>`

## 规则到代码逻辑映射

| 规则类型 | 实现位置 | 实现方式 | 说明 |
|---------|---------|---------|------|
| 计算规则 | Service 层 | 独立方法，返回计算结果 | 计算是独立的业务逻辑，不涉及事务和编排 |
| 约束规则 | Biz 层 | 校验方法，不通过抛业务异常 | 约束校验通常在业务编排过程中执行，且可能涉及多对象 |
| 跨实体一致性 | Biz 层 | 事务内校验 | 必须在事务内校验，Biz 层负责事务管理 |

### Biz 层的典型编排模式

约束校验（约束规则）→ 调用 Service 计算（计算规则）→ 执行操作

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

如果 SOP 有条件分支（如"审批不通过则退回"），在 Biz 方法中用 if-else 实现：

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

### 说明

- SOP 的每一步可能跨越多个对象的行为，放在 Biz 层做编排
- 不需要独立的流程引擎，用 Biz 方法的顺序调用即可表达
- 一个 SOP 流程 = 一个 Biz 方法，保持可追溯性

## 设计文档中的映射表达

在 `docs/app-design.md` 的接口设计部分，必须包含以下三张映射表，确保下游 code-generation skill 可以直接从设计文档推导出完整的代码骨架：

1. **行为→接口映射表**：每个对象的每个行为对应哪个 Controller 接口、Biz 方法、Service 方法
2. **规则→代码位置映射表**：每条规则对应哪个层级、哪个方法名
3. **SOP→Biz 编排方法映射表**：每个 SOP 流程对应哪个 Biz 方法，内部调用哪些 Service 方法
