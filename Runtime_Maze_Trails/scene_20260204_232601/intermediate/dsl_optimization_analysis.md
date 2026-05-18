# DSL优化分析报告

## LLM完整响应

# 运筹建模DSL非线性优化解决方案

## 1. 非线性要素系统化识别

经过对DSL的全面扫描，在目标函数中识别出以下非线性要素：

**非线性要素 1：照付不议惩罚成本中的 `max(0, x)` 函数**
- **位置**：`objective.obj_terms` 中的 `TERM_TAKE_OR_PAY_PENALTY`
- **数学表达式**：
  $$ \sum_{r \in RESOURCE\_CODES} \max(0, Q_{min}^{r} - \sum_{p \in P_r} x_p) \cdot P^{r} \cdot \alpha^{r} $$
  其中 $P_r$ 是以资源 $r$ 为起点的路径集合，$x_p$ 是路径流量，$Q_{min}^{r}$ 是资源最小提取量，$P^{r}$ 是单价，$\alpha^{r}$ 是惩罚系数。
- **变量依赖**：涉及决策变量 `VAR_PATH_FLOW` 的线性组合与参数 `PARAM_RESOURCE_MIN_QTY` 的差值。
- **非线性类型**：**非光滑函数**。`max(0, z)` 函数在 $z=0$ 处不可导，导致目标函数非线性。由于目标是最小化该项（系数为-1），且该项为非负值，这属于凸优化问题中的典型非线性项。

## 2. 非线性问题等价转化

针对识别出的 `max(0, z)` 非光滑函数，采用**辅助变量法**进行线性化转化。

**转化策略：**
1.  **引入辅助变量**：为每个资源 $r$ 引入非负连续变量 $y_r$，代表未满足最小提取量的缺口（即惩罚基数）。
    $$ y_r \geq 0, \quad \forall r \in RESOURCE\_CODES $$
2.  **构建线性约束**：利用 $y_r$ 替代 $\max(0, Q_{min}^{r} - \sum x_p)$。由于目标函数是最小化总成本（即最大化利润，惩罚项系数为负），求解器会自动将 $y_r$ 压至最小值，从而满足等价性。
    约束条件为：
    $$ y_r \geq Q_{min}^{r} - \sum_{p \in P_r} x_p, \quad \forall r \in RESOURCE\_CODES $$
    $$ y_r \geq 0 $$
    *注：在最小化问题中，$y_r$ 会自动取 $\max(0, Q_{min}^{r} - \sum x_p)$。*

**转化后的目标函数项：**
原非线性项：
$$ - \sum_{r} \max(0, Q_{min}^{r} - \sum_{p \in P_r} x_p) \cdot P^{r} \cdot \alpha^{r} $$
转化为线性项：
$$ - \sum_{r} y_r \cdot P^{r} \cdot \alpha^{r} $$

**等价性说明**：
- 若 $Q_{min}^{r} - \sum x_p \leq 0$，则约束 $y_r \geq \text{负数}$ 和 $y_r \geq 0$ 共同作用，最小化 $y_r$ 的结果为 $y_r = 0$，与 $\max(0, \dots)$ 一致。
- 若 $Q_{min}^{r} - \sum x_p > 0$，则约束 $y_r \geq \text{正数}$ 起主导作用，最小化 $y_r$ 的结果为 $y_r = Q_{min}^{r} - \sum x_p$，与 $\max(0, \dots)$ 一致。

## 3. 完整优化模型重构

基于上述转化策略，对DSL进行如下重构：

### 1. 决策变量扩展
在 `decision_vars` 中新增辅助变量：
- **变量名**：`VAR_TOP_GAP` (Take-Or-Pay Gap)
- **类型**：连续变量
- **索引集**：`RESOURCE_CODES`
- **下界**：0
- **物理含义**：资源 $r$ 的实际提取量低于照付不议基准量的差额（即需支付惩罚的基数）。

### 2. 目标函数线性化
修改 `objective` 中的 `TERM_TAKE_OR_PAY_PENALTY` 项：
- **原表达式**：`sum(max(0, ...) ...)`
- **新表达式**：`sum(VAR_TOP_GAP[r] * PARAM_RESOURCE_PRICE[r] * PARAM_NOP_PERCENT[r] for r in RESOURCE_CODES)`

### 3. 约束条件整合
在 `constraints` 中新增约束：
- **约束ID**：`CONST_TOP_GAP_DEF`
- **类型**：线性不等式
- **方向**：`>=`
- **左表达式**：`VAR_TOP_GAP[r] + sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[0] == r)`
- **右表达式**：`PARAM_RESOURCE_MIN_QTY[r]`
- **物理含义**：定义惩罚缺口变量，确保 $y_r + \text{实际提取量} \geq \text{最小提取量}$。结合目标函数的最小化倾向，等价于 $y_r = \max(0, \text{最小提取量} - \text{实际提取量})$。

### 4. 求解配置适配
转化后的模型为**混合整数线性规划（MILP）**模型（注：原模型无整数变量，转化后仍为LP，但具备扩展性；若原问题有路径开关变量则为MILP）。SCIP求解器非常适合此类问题。保持原有配置即可。

## 4. 模型验证与分析

1.  **等价性验证**：
    -   理论上，该转化是标准的凸函数分段线性化方法（Epigraph形式）。
    -   验证方法：可构造极端测试用例。
        -   用例1：某资源提取量 > 最小提取量。预期 $y_r=0$，惩罚成本为0。
        -   用例2：某资源提取量 < 最小提取量。预期 $y_r = \text{差值}$，惩罚成本为差值*单价*系数。
        -   对比转化前后模型的目标函数值，应完全一致。

2.  **求解效率分析**：
    -   **复杂度**：新增了 $|RESOURCE\_CODES|$ 个连续变量和 $|RESOURCE\_CODES|$ 个线性约束。对于典型的天然气管网问题，资源数量通常在几十到几百个，这对现代求解器（如SCIP/Gurobi）的计算开销影响微乎其微。
    -   **效率建议**：模型结构保持稀疏，无需特殊的求解器参数调整。

3.  **边界条件说明**：
    -   该转化策略在所有参数为非负数的情况下均有效。
    -   若 `PARAM_RESOURCE_MIN_QTY` 为空或0，约束自动变为 $y_r + \text{flow} \geq 0$，由于 $y_r \geq 0$ 且 $\text{flow} \geq 0$，该约束自然满足，$y_r$ 将被优化为0，符合业务逻辑。

## 终版完整DSL

```json
{
  "meta_info": {
    "scene_id": "gas_matching_optimization",
    "scene_type": "混合优化",
    "version": "v1.0.1",
    "creator": "auto_gen_by_llm",
    "create_time": "2023-10-27T10:00:00Z"
  },
  "data_def": {
    "tables": [
      {
        "table_name": "monthly_demand_pool",
        "fields": [
          {
            "name": "demand_plan_code",
            "type": "string",
            "desc": "需求计划编码",
            "is_required": true
          },
          {
            "name": "quantity",
            "type": "float",
            "desc": "需求量",
            "is_required": true
          },
          {
            "name": "unit_selling_price",
            "type": "float",
            "desc": "销售单价",
            "is_required": true
          },
          {
            "name": "minimum_satisfy_quantity",
            "type": "float",
            "desc": "最小满足量",
            "is_required": false
          }
        ],
        "primary_key": [
          "demand_plan_code"
        ]
      },
      {
        "table_name": "monthly_resource_pool",
        "fields": [
          {
            "name": "purchase_agreement_no",
            "type": "string",
            "desc": "采购合同号",
            "is_required": true
          },
          {
            "name": "quantity",
            "type": "float",
            "desc": "供应量上限",
            "is_required": true
          },
          {
            "name": "min_quantity",
            "type": "float",
            "desc": "最小提取量（照付不议基准）",
            "is_required": false
          },
          {
            "name": "unit_price",
            "type": "float",
            "desc": "采购单价",
            "is_required": true
          },
          {
            "name": "no_discuss_percent",
            "type": "float",
            "desc": "照付不议系数",
            "is_required": false
          }
        ],
        "primary_key": [
          "purchase_agreement_no"
        ]
      },
      {
        "table_name": "monthly_transport_pool",
        "fields": [
          {
            "name": "id",
            "type": "int",
            "desc": "主键ID",
            "is_required": true
          },
          {
            "name": "design_gas_capacity",
            "type": "float",
            "desc": "设计输气能力（上限）",
            "is_required": true
          },
          {
            "name": "unit_price",
            "type": "float",
            "desc": "运输单价",
            "is_required": true
          },
          {
            "name": "min_amount",
            "type": "float",
            "desc": "最小运输量",
            "is_required": false
          }
        ],
        "primary_key": [
          "id"
        ]
      },
      {
        "table_name": "ontology_city_gas_station_info",
        "fields": [
          {
            "name": "gate_station_code",
            "type": "string",
            "desc": "城燃门站编码",
            "is_required": true
          },
          {
            "name": "upper_bound",
            "type": "float",
            "desc": "门站业务上限",
            "is_required": false
          },
          {
            "name": "lower_bound",
            "type": "float",
            "desc": "门站业务下限",
            "is_required": false
          }
        ],
        "primary_key": [
          "gate_station_code"
        ]
      }
    ],
    "index_sets": [
      {
        "set_name": "DEMAND_CODES",
        "source": "monthly_demand_pool.demand_plan_code",
        "desc": "需求计划编码集合"
      },
      {
        "set_name": "RESOURCE_CODES",
        "source": "monthly_resource_pool.purchase_agreement_no",
        "desc": "资源采购合同号集合"
      },
      {
        "set_name": "TRANSPORT_IDS",
        "source": "monthly_transport_pool.id",
        "desc": "管输运力ID集合"
      },
      {
        "set_name": "GATE_STATION_CODES",
        "source": "ontology_city_gas_station_info.gate_station_code",
        "desc": "城燃门站编码集合"
      },
      {
        "set_name": "FEASIBLE_PATHS",
        "source": "path_query.paths",
        "desc": "可行路径集合，每个元素为[节点ID, 边ID, 节点ID, ..., 边ID, 节点ID]的列表，其中节点ID对应资源/门站/需求，边ID对应运力ID"
      }
    ],
    "parameters": [
      {
        "param_name": "PARAM_DEMAND_QTY",
        "source": "monthly_demand_pool.quantity",
        "index_sets": [
          "DEMAND_CODES"
        ],
        "data_type": "float",
        "desc": "需求量上限"
      },
      {
        "param_name": "PARAM_SELLING_PRICE",
        "source": "monthly_demand_pool.unit_selling_price",
        "index_sets": [
          "DEMAND_CODES"
        ],
        "data_type": "float",
        "desc": "销售单价（固定单价）"
      },
      {
        "param_name": "PARAM_MIN_SATISFY_QTY",
        "source": "monthly_demand_pool.minimum_satisfy_quantity",
        "index_sets": [
          "DEMAND_CODES"
        ],
        "data_type": "float",
        "desc": "需求最小满足量"
      },
      {
        "param_name": "PARAM_RESOURCE_QTY",
        "source": "monthly_resource_pool.quantity",
        "index_sets": [
          "RESOURCE_CODES"
        ],
        "data_type": "float",
        "desc": "资源供应量上限"
      },
      {
        "param_name": "PARAM_RESOURCE_PRICE",
        "source": "monthly_resource_pool.unit_price",
        "index_sets": [
          "RESOURCE_CODES"
        ],
        "data_type": "float",
        "desc": "资源采购单价（固定单价）"
      },
      {
        "param_name": "PARAM_RESOURCE_MIN_QTY",
        "source": "monthly_resource_pool.min_quantity",
        "index_sets": [
          "RESOURCE_CODES"
        ],
        "data_type": "float",
        "desc": "资源最小提取量（照付不议基准）"
      },
      {
        "param_name": "PARAM_NOP_PERCENT",
        "source": "monthly_resource_pool.no_discuss_percent",
        "index_sets": [
          "RESOURCE_CODES"
        ],
        "data_type": "float",
        "desc": "照付不议系数"
      },
      {
        "param_name": "PARAM_TRANSPORT_CAP",
        "source": "monthly_transport_pool.design_gas_capacity",
        "index_sets": [
          "TRANSPORT_IDS"
        ],
        "data_type": "float",
        "desc": "管输设计能力上限"
      },
      {
        "param_name": "PARAM_TRANSPORT_PRICE",
        "source": "monthly_transport_pool.unit_price",
        "index_sets": [
          "TRANSPORT_IDS"
        ],
        "data_type": "float",
        "desc": "管输运输单价（固定单价）"
      },
      {
        "param_name": "PARAM_TRANSPORT_MIN",
        "source": "monthly_transport_pool.min_amount",
        "index_sets": [
          "TRANSPORT_IDS"
        ],
        "data_type": "float",
        "desc": "管输最小运输量"
      },
      {
        "param_name": "PARAM_STATION_UPPER",
        "source": "ontology_city_gas_station_info.upper_bound",
        "index_sets": [
          "GATE_STATION_CODES"
        ],
        "data_type": "float",
        "desc": "门站业务上限"
      },
      {
        "param_name": "PARAM_STATION_LOWER",
        "source": "ontology_city_gas_station_info.lower_bound",
        "index_sets": [
          "GATE_STATION_CODES"
        ],
        "data_type": "float",
        "desc": "门站业务下限"
      }
    ]
  },
  "decision_vars": [
    {
      "var_name": "VAR_PATH_FLOW",
      "var_type": "continuous",
      "index_sets": [
        "FEASIBLE_PATHS"
      ],
      "lower_bound": 0,
      "desc": "路径上的天然气流量，索引为完整路径列表"
    },
    {
      "var_name": "VAR_TOP_GAP",
      "var_type": "continuous",
      "index_sets": [
        "RESOURCE_CODES"
      ],
      "lower_bound": 0,
      "desc": "照付不议惩罚缺口变量：实际提取量低于最小提取量的部分"
    }
  ],
  "objective": {
    "obj_type": "maximize",
    "obj_terms": [
      {
        "term_name": "TERM_SALES_REVENUE",
        "expression": "sum(VAR_PATH_FLOW[p] * PARAM_SELLING_PRICE[p[-1]] for p in FEASIBLE_PATHS)",
        "coefficient": 1,
        "desc": "销售收入：路径流量终点对应的需求单价"
      },
      {
        "term_name": "TERM_RESOURCE_COST",
        "expression": "sum(VAR_PATH_FLOW[p] * PARAM_RESOURCE_PRICE[p[0]] for p in FEASIBLE_PATHS)",
        "coefficient": -1,
        "desc": "资源采购成本：路径流量起点对应的资源单价"
      },
      {
        "term_name": "TERM_TRANSPORT_COST",
        "expression": "sum(VAR_PATH_FLOW[p] * sum(PARAM_TRANSPORT_PRICE[e] for e in p if type(e)==int) for p in FEASIBLE_PATHS)",
        "coefficient": -1,
        "desc": "管输运力成本：路径流量经过的所有边的运输单价之和"
      },
      {
        "term_name": "TERM_TAKE_OR_PAY_PENALTY",
        "expression": "sum(VAR_TOP_GAP[r] * PARAM_RESOURCE_PRICE[r] * PARAM_NOP_PERCENT[r] for r in RESOURCE_CODES)",
        "coefficient": -1,
        "desc": "照付不议惩罚成本：缺口变量 * 单价 * 系数"
      }
    ],
    "desc": "最大化总利润（销售收入 - 资源采购成本 - 管输运力成本 - 照付不议惩罚成本）"
  },
  "constraints": [
    {
      "constraint_id": "CONST_RESOURCE_SUPPLY_LIMIT",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[0] == r)",
      "right_expression": "PARAM_RESOURCE_QTY[r]",
      "index_sets": [
        "RESOURCE_CODES"
      ],
      "priority": 1,
      "desc": "资源供应量上限约束：从每个资源提取的总量不能超过该资源的最大供应量"
    },
    {
      "constraint_id": "CONST_DEMAND_SATISFY_LIMIT",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[-1] == d)",
      "right_expression": "PARAM_DEMAND_QTY[d]",
      "index_sets": [
        "DEMAND_CODES"
      ],
      "priority": 1,
      "desc": "需求满足量上限约束：供应给每个需求的总量不能超过该需求的最大需求量"
    },
    {
      "constraint_id": "CONST_TRANSPORT_CAP_LIMIT",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if t in p)",
      "right_expression": "PARAM_TRANSPORT_CAP[t]",
      "index_sets": [
        "TRANSPORT_IDS"
      ],
      "priority": 1,
      "desc": "管输运力上限约束：每条运输路径上的流量不能超过该管段的设计输气能力"
    },
    {
      "constraint_id": "CONST_STATION_CAP_LIMIT",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if s in p)",
      "right_expression": "PARAM_STATION_UPPER[s]",
      "index_sets": [
        "GATE_STATION_CODES"
      ],
      "priority": 1,
      "desc": "门站业务上限约束：经过门站的流量不能超过门站业务上限"
    },
    {
      "constraint_id": "CONST_STATION_MIN_LIMIT",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if s in p)",
      "right_expression": "PARAM_STATION_LOWER[s]",
      "index_sets": [
        "GATE_STATION_CODES"
      ],
      "priority": 1,
      "desc": "门站业务下限约束：经过门站的流量不能低于门站业务下限"
    },
    {
      "constraint_id": "CONST_TRANSPORT_MIN_LIMIT",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if t in p)",
      "right_expression": "PARAM_TRANSPORT_MIN[t]",
      "index_sets": [
        "TRANSPORT_IDS"
      ],
      "priority": 2,
      "relaxable": true,
      "desc": "管输最小量约束：使用管输运力时，运输量需满足最小运输量要求（可松弛）"
    },
    {
      "constraint_id": "CONST_DEMAND_MIN_SATISFY",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[-1] == d)",
      "right_expression": "PARAM_MIN_SATISFY_QTY[d]",
      "index_sets": [
        "DEMAND_CODES"
      ],
      "priority": 2,
      "relaxable": true,
      "desc": "需求最小满足量约束：供应给每个需求的总量应尽量满足最小满足量要求（软约束）"
    },
    {
      "constraint_id": "CONST_TOP_GAP_DEF",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "VAR_TOP_GAP[r] + sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[0] == r)",
      "right_expression": "PARAM_RESOURCE_MIN_QTY[r]",
      "index_sets": [
        "RESOURCE_CODES"
      ],
      "priority": 1,
      "desc": "照付不议缺口定义约束：实际提取量 + 缺口变量 >= 最小提取量。结合目标函数最小化惩罚，等价于 Gap = max(0, Min - Actual)"
    }
  ],
  "solve_config": {
    "solver_type": "scip",
    "solver_params": {
      "timeout": 300,
      "gap": 0.01,
      "threads": 4
    },
    "warm_start": false
  },
  "output_config": {
    "output_fields": [
      {
        "name": "path_flow",
        "expression": "VAR_PATH_FLOW",
        "desc": "路径分配流量"
      },
      {
        "name": "total_profit",
        "expression": "objective.value",
        "desc": "总利润"
      },
      {
        "name": "resource_usage",
        "expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[0] == r)",
        "desc": "资源使用量"
      },
      {
        "name": "demand_satisfaction",
        "expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[-1] == d)",
        "desc": "需求满足量"
      },
      {
        "name": "top_penalty_gap",
        "expression": "VAR_TOP_GAP",
        "desc": "照付不议惩罚缺口量"
      }
    ],
    "output_format": "csv",
    "output_path": "./optimization_result"
  }
}
```