---
name: or-dsl-to-core-code
description: Transform an operations-research DSL into core Python optimization code using Pyomo. Use when Codex needs to generate the model-building, solving, and result-parsing code from a complete OR DSL, while keeping the output limited to core business-logic code rather than full runtime scaffolding.
---

# OR DSL To Core Code

将完整的运筹 DSL 转换为核心 Python 优化代码。

这个 skill 的职责是生成核心业务逻辑代码，也就是围绕模型构建、求解、结果解析的核心代码；不是生成完整运行时工程，不负责 `main.py`、数据加载器、命令行入口等外围壳层。

## 适用输入

用户输入通常包括：

1. 一份完整的运筹 DSL JSON
2. 与模型代码生成有关的补充要求

内置参考：

1. DSL 转核心代码规则
   - 读取 [references/dsl-to-core-code-rules.md](references/dsl-to-core-code-rules.md)
2. DSL Schema
   - 读取 [references/dsl.schema.json](references/dsl.schema.json)

## 核心边界

- 输入是一份完整 DSL，不是标准化输入
- 输出是核心模型代码，不是完整 runtime 项目
- 默认产物是 `model_builder.py` 风格的 Python 文件
- 必须使用 Pyomo，不使用 ortools、gurobi Python API、cplex Python API 等替代建模框架
- 数据已在运行时通过 `data` 字典传入，不在代码中读取文件

## Workflow

按下面顺序工作，不要跳步。

### 1. 读取并审视完整 DSL

重点识别：

- `data_def`
- `decision_vars`
- `objective`
- `constraints`
- `solve_config`
- `output_config`

先明确 DSL 中哪些是核心建模语义，哪些属于运行时外围逻辑。

### 2. 提取核心代码职责

读取 [references/dsl-to-core-code-rules.md](references/dsl-to-core-code-rules.md)。

代码只承担以下核心职责：

- 从 `data["tables"]` 和 `data["paths"]` 提取数据
- 将数据整理为 Pyomo 可用的集合和参数
- 构建 Pyomo 模型
- 调用求解器求解
- 解析求解结果并输出结构化结果

### 3. 生成核心函数

默认输出这 3 个核心函数：

- `build_model(data)`
- `solve_model(model)`
- `parse_result(results, data, output_dir)`

若用户明确要求更小范围，也可以只生成其中部分，但必须说明裁剪依据。

### 4. 把 DSL 映射到 Pyomo

重点完成：

- 把集合、参数、变量映射为 Python 数据结构和 Pyomo 组件
- 把目标函数映射为 `Objective`
- 把约束映射为 `Constraint`
- 把求解配置映射为 `SolverFactory` 及其参数

优先忠实映射 DSL 的核心业务逻辑，不额外发明运行时框架层逻辑。

### 5. 收口输出

输出应是单个核心 Python 文件，通常是 `model_builder.py` 风格，要求：

- 可被外部 `main.py` 调用
- 不包含 `main()` 入口
- 不包含文件读取逻辑
- 不包含命令行参数解析
- 不生成与数据加载职责重复的代码

### 6. 检查结果

至少检查：

- 是否使用 Pyomo
- 是否只依赖传入的 `data` 字典
- 是否覆盖 DSL 中的核心变量、目标和约束
- 是否把外围 runtime 逻辑错误混入核心代码

## 输出要求

- 输出完整核心 Python 代码
- 若需要，先给简短说明，再给代码
- 代码应清晰、可读、可直接被 runtime 外壳调用
- 对复杂映射可加少量注释，但不要写成教程文档

## 禁止事项

- 不要生成 `main.py`
- 不要生成数据加载器
- 不要在代码中读取 CSV、JSON、数据库或路径文件
- 不要把 DSL 之外的业务规则硬编码进去
- 不要把“核心代码”扩展成完整应用骨架
