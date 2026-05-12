# DSL 转核心代码规则

本文件给出将运筹 DSL 转成核心 Python 优化代码时的规则。

## 1. 任务定位

- 输入是一份完整 OR DSL
- 输出是一份核心 Python 模型代码
- 核心代码只承载核心业务逻辑
- 运行时外围壳层由其他生成物负责

这里的“核心代码”通常指 `model_builder.py` 这类文件，包括：

- `build_model(data)`
- `solve_model(model)`
- `parse_result(results, data, output_dir)`

## 2. 技术约束

- 建模框架必须使用 `pyomo.environ`
- 求解器通过 `pyomo.opt.SolverFactory` 创建
- 使用 DSL `solve_config` 指定的求解器和参数
- 不使用 ortools、gurobi Python API、cplex Python API 等替代框架

## 3. 数据输入边界

数据已经在运行时加载完成，并通过 `data` 字典传入。

典型结构：

```python
data = {
    "tables": {
        "resource": ...,
        "demand": ...,
        "transport": ...
    },
    "paths": [
        ["node1", "edge1", "node2", "edge2", "node3"]
    ]
}
```

代码中只允许：

- 访问 `data["tables"]`
- 访问 `data["paths"]`
- 将其转换为集合、参数和索引

代码中禁止：

- `pd.read_csv`
- `json.load`
- 数据库查询
- 从文件再次读取路径

## 4. 路径数据处理

如果 DSL 是路径型模型，遵循以下规则：

- `data["paths"]` 中的每个路径是节点和边交替的序列
- 路径需转换为元组以便作为 Pyomo 索引
- 资源端可通过 `path_seq[0]` 识别
- 需求端可通过 `path_seq[-1]` 识别
- 边应通过集合成员判断识别，而不是依赖切片位置

推荐模式：

```python
TRANSPORT_IDS_SET = set(transport_df["edge_id"])
FEASIBLE_PATHS = [tuple(path) for path in data["paths"]]

path_edges = [e for e in path_seq if e in TRANSPORT_IDS_SET]
```

## 5. 核心函数职责

### 5.1 `build_model(data)`

职责：

- 从 `data["tables"]` 取表数据
- 从 `data["paths"]` 取路径数据
- 构建 Python 层集合和参数
- 创建 `ConcreteModel`
- 定义变量、目标和约束

要求：

- 忠实映射 DSL 的 `decision_vars`、`objective`、`constraints`
- 不在这里做外部 IO

### 5.2 `solve_model(model)`

职责：

- 根据 DSL `solve_config` 创建求解器
- 配置超时、gap、threads 等参数
- 执行求解
- 返回结果对象

要求：

- 仅做求解相关逻辑
- 可把 `model` 绑定到 `results` 上供后续解析使用

### 5.3 `parse_result(results, data, output_dir)`

职责：

- 提取变量值和目标值
- 组织结构化结果
- 根据 `output_config` 生成核心结果输出

要求：

- 结果解析围绕 DSL 中定义的输出需求
- 可以输出 Excel/JSON 等结果文件
- 但不要扩展为完整报告系统或应用层展示逻辑

## 6. 代码边界

生成的代码应该包含：

- 必要 import
- 核心函数
- 为 DSL 映射服务的少量辅助逻辑

生成的代码不应该包含：

- `main()` 入口
- 命令行参数解析
- 数据加载器实现
- 与外层 orchestration 重复的控制流

## 7. 生成原则

- DSL 只是核心业务逻辑的建模，因此代码只生成核心代码
- 优先保证业务语义正确，再考虑模板化整洁
- 不要把运行时外壳职责挤进核心代码
- 不要臆造 DSL 中不存在的业务规则

## 8. 输出要求

最终输出应是单个完整 Python 文件内容，可直接作为 `model_builder.py` 一类核心模块使用。
