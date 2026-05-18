---
name: or-dsl-nonlinear-optimization
description: Optimize an operations-research DSL by identifying nonlinear elements and rewriting them into an equivalent solver-friendly DSL. Use when Codex needs to analyze an existing OR DSL, linearize or reformulate nonlinear pieces, and output a complete optimized DSL that still conforms to the DSL schema.
---

# OR DSL Nonlinear Optimization

将已有的运筹 DSL 中的非线性要素识别出来，并在不改变核心业务逻辑的前提下，转化为更可求解的 DSL。

这个 skill 的职责是优化 DSL，不是生成实例数据，也不是直接生成求解代码。

## 适用输入

用户输入通常包括：

1. 一份完整的运筹 DSL JSON
2. 与非线性优化有关的补充要求

内置参考：

1. 非线性优化规则
   - 读取 [references/nonlinear-optimization-rules.md](references/nonlinear-optimization-rules.md)
2. DSL Schema
   - 读取 [references/dsl.schema.json](references/dsl.schema.json)

## 核心边界

- 输入是一份完整 DSL，不是标准化输入
- 目标是重写 DSL，使其更适配求解器
- 不得修改原问题的核心业务逻辑和数据定义
- 不得臆造输入数据
- 若无法做严格等价转化，必须明确说明原因、误差或风险

## Workflow

按下面顺序工作，不要跳步。

### 1. 读取并审视完整 DSL

先识别 DSL 中的：

- `decision_vars`
- `objective`
- `constraints`
- `solve_config`

重点关注目标函数和约束表达式中的非线性结构。

### 2. 系统识别非线性要素

读取 [references/nonlinear-optimization-rules.md](references/nonlinear-optimization-rules.md)。

对每一个非线性要素，至少识别：

- 所在位置
- 原表达式
- 涉及的变量与参数
- 非线性类型
- 是否可做严格等价转化

### 3. 选择转化策略

优先使用等价转化：

- 分段函数重写
- 非光滑函数辅助变量化
- 二元变量与连续变量乘积线性化
- 其他具有明确理论支撑的 reformulation

若只能近似：

- 明确说明近似方法
- 明确说明误差范围和影响
- 只有在用户接受或场景允许时才采用

### 4. 重构完整 DSL

在原 DSL 基础上更新：

- `decision_vars`：补充必要的辅助变量
- `objective`：重写非线性目标项
- `constraints`：替换非线性约束并补充辅助约束
- `solve_config`：根据 reformulation 后的模型类型调整求解器参数

输出必须是完整 DSL，不是局部 diff。

### 5. 验证转化结果

至少检查：

- 新 DSL 是否仍满足 schema
- 原业务语义是否保持
- 新增变量和约束是否只服务于转化
- 是否引入了无依据的复杂化

## 输出要求

- 先给出结构化分析，再输出完整优化后 DSL
- 最终 DSL 必须完整覆盖所有顶层模块
- 新增变量与约束必须可解释、可追溯
- 变量名、约束名、目标子项名必须遵守 schema 命名规则

## 常见非线性类型

优先检查：

- 分段函数
- `max` / `min` / `abs`
- 变量乘积
- 指数、对数
- 分式、根号
- 条件判断嵌套

## 禁止事项

- 不要改动核心业务目标
- 不要删改原始数据定义来回避非线性
- 不要引入与原问题无关的变量或约束
- 不要在没有说明的情况下使用不可验证的近似
- 不要只输出分析，不输出完整 DSL
