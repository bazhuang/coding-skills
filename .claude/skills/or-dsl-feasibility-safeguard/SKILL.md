---
name: or-dsl-feasibility-safeguard
description: Safeguard the feasible region of an operations-research DSL by classifying constraints into resource-like and non-resource-like boundary constraints, then adding prioritized slack variables and penalty terms to restore solvability while preserving core model logic and schema compliance.
---

# OR DSL Feasibility Safeguard

将已有的运筹 DSL 做“可行域保障”重写：先识别约束类型，再按优先级添加松弛变量和惩罚项，提升模型可解性。

这个 skill 的职责是重写 DSL 中的可软化边界约束，不是生成实例数据，也不是直接生成求解代码。

## 适用输入

用户输入通常包括：

1. 一份完整的运筹 DSL JSON
2. 与约束松弛、可行域恢复、feasibility safeguard 有关的补充要求

内置参考：

1. 可行域保障规则
   - 读取 [references/feasibility-safeguard-rules.md](references/feasibility-safeguard-rules.md)
2. DSL Schema
   - 读取 [references/dsl.schema.json](references/dsl.schema.json)

## 核心边界

- 输入是一份完整 DSL，不是标准化输入
- 目标是增强模型可解性，不是改变核心业务逻辑
- 只允许围绕可软化边界约束重写 `decision_vars`、`objective`、`constraints`
- 不得臆造输入数据
- 不得把 build-time 仓库变成运行时求解逻辑

## Workflow

按下面顺序工作，不要跳步。

### 1. 读取并审视完整 DSL

重点识别：

- `decision_vars`
- `objective`
- `constraints`
- `solve_config`

先确定哪些约束是边界约束，哪些属于定义、守恒、逻辑或拓扑约束。

### 2. 识别可软化候选约束

读取 [references/feasibility-safeguard-rules.md](references/feasibility-safeguard-rules.md)。

只把以下约束纳入候选集合：

- 上限类约束：`实际执行量 ≤ 边界值`
- 下限类约束：`实际执行量 ≥ 边界值`

明确排除不可软化约束。

### 3. 对候选约束做双重分类

对每条候选约束都要识别：

- 是资源型还是非资源型
- 是上限还是下限

资源型强调可通过调度、协调、计划调整改变；非资源型强调物理、工艺、安全、结构边界。

### 4. 按优先级设计松弛变量与惩罚

严格按以下顺序实现松弛优先级：

1. 资源型上限
2. 资源型下限
3. 非资源型上限
4. 非资源型下限

通过目标函数中的惩罚梯度显式体现优先级，而不是只做文字说明。

### 5. 重写完整 DSL

在原 DSL 基础上更新：

- `decision_vars`：新增松弛变量
- `constraints`：改写可软化边界约束
- `objective`：增加各类松弛惩罚项

其他顶层模块保持完整并尽量少改。

### 6. 检查结果

至少检查：

- 新 DSL 是否仍满足 schema
- 守恒、定义、逻辑类约束是否未被错误软化
- 惩罚系数是否严格体现四级顺序
- 新增变量和约束是否只服务于可行域保障

## 输出要求

- 先给出结构化分析，再输出完整保障后的 DSL
- 最终 DSL 必须完整覆盖所有顶层模块
- 必须显式说明约束分类结果与优先级设计
- 变量名、约束名、目标子项名必须遵守 schema 命名规则

## 禁止事项

- 不要改动核心业务目标和数据定义
- 不要软化守恒、定义、逻辑、可达性、安全红线类约束
- 不要只输出局部 diff
- 不要引入与原问题无关的变量、参数或约束
- 不要把“资源型”误解成仅限资源表字段
