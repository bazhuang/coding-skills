# DSL优化分析报告

## LLM完整响应

# 运筹建模DSL非线性优化解决方案

## 1. 非线性要素系统化识别

经过对输入DSL的详细遍历与分析，识别出以下非线性要素：

**1. 照付不议惩罚项中的非光滑函数**
- **位置**：目标函数 `objective` 中的 `TERM_TAKE_OR_PAY_PENALTY` 项。
- **数学表达式**：
  $$ \sum_{r \in RESOURCE\_IDS} \max(0, Q_{min}^{r} - \sum_{p \in P_r} x_p) \cdot P^{r} \cdot \alpha^{r} $$
  其中 $x_p$ 为 `VAR_PATH_FLOW`，$P_r$ 为以资源 $r$ 为起点的路径集合。
- **变量依赖**：涉及决策变量 `VAR_PATH_FLOW` 和参数 `PARAM_RESOURCE_MIN_QTY`、`PARAM_RESOURCE_PRICE`、`PARAM_TAKE_OR_PAY_RATIO`。
- **非线性类型**：**非光滑函数**。包含 `max(0, ...)` 操作，导致目标函数不可微，无法直接应用线性规划或标准凸规划求解器求解。

**2. 其他要素分析**
- 目标函数中的其他项（销售收入、资源成本、运输成本）均为决策变量的线性组合。
- 约束条件（资源上限、需求上限、管输能力等）均为线性不等式。
- **结论**：模型唯一的非线性来源为照付不议惩罚项中的 `max` 函数。

## 2. 非线性问题等价转化

针对识别出的 `max(0, ...)` 非光滑项，采用**辅助变量法**进行精确线性化转化。

**转化策略**：
对于每个资源 $r$，引入非负辅助连续变量 $y_r$，用于表示 $\max(0, Q_{min}^{r} - \sum_{p \in P_r} x_p)$ 的值。

**数学转化步骤**：
1. **变量定义**：
   定义 $y_r \ge 0$，物理含义为资源 $r$ 的未满足最小提取量（即惩罚基数）。

2. **目标函数替换**：
   原非线性项：$\max(0, Q_{min}^{r} - \sum_{p \in P_r} x_p) \cdot P^{r} \cdot \alpha^{r}$
   转化为线性项：$y_r \cdot P^{r} \cdot \alpha^{r}$
   由于目标函数是最大化利润，且惩罚项系数为负（$-1$），求解器会自动驱动 $y_r$ 趋近于其下界。

3. **约束构建**：
   为了保证 $y_r = \max(0, Q_{min}^{r} - \sum_{p \in P_r} x_p)$，添加以下线性约束：
   $$ y_r \ge Q_{min}^{r} - \sum_{p \in P_r} x_p, \quad \forall r \in RESOURCE\_IDS $$
   
   **等价性说明**：
   - 设 $Actual_r = \sum_{p \in P_r} x_p$。
   - 约束条件为 $y_r \ge Q_{min}^{r} - Actual_r$ 且 $y_r \ge 0$（变量定义）。
   - 在目标函数中，该项为 $-C \cdot y_r$（其中 $C = P^{r} \cdot \alpha^{r} > 0$）。
   - 为了最大化目标函数，求解器会尽可能减小 $y_r$。
   - 因此，最优解处必然满足 $y_r = \max(0, Q_{min}^{r} - Actual_r)$。
   - 该转化是**精确等价**的，无近似误差。

## 3. 完整优化模型重构

基于上述转化策略，对原DSL模型进行重构：

### 1. 决策变量扩展
在 `decision_vars` 中新增辅助变量：
- **变量名**：`VAR_TAKE_OR_PAY_SHORTAGE`
- **类型**：连续变量
- **索引集**：`RESOURCE_IDS`
- **下界**：0
- **物理含义**：资源 $r$ 的实际提取量低于最小提取量的差额（即照付不议惩罚的基数）。

### 2. 目标函数线性化
修改 `objective` 中的 `TERM_TAKE_OR_PAY_PENALTY`：
- **原表达式**：`sum(max(0, ...) * ...)`
- **新表达式**：`sum(VAR_TAKE_OR_PAY_SHORTAGE[r] * PARAM_RESOURCE_PRICE[r] * PARAM_TAKE_OR_PAY_RATIO[r] for r in RESOURCE_IDS)`

### 3. 约束条件整合
在 `constraints` 中新增辅助约束：
- **约束ID**：`CONST_TAKE_OR_PAY_LINEARIZATION`
- **类型**：线性不等式
- **方向**：`>=`
- **左表达式**：`VAR_TAKE_OR_PAY_SHORTAGE[r] + sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[0] == r)`
- **右表达式**：`PARAM_RESOURCE_MIN_QTY[r]`
- **物理含义**：辅助变量 $y_r$ 与实际流量之和必须至少等于最小提取量。结合 $y_r \ge 0$ 和最小化目标，即实现了 $y_r = \max(0, \text{min} - \text{actual})$。

### 4. 求解配置适配
- 模型类型由非线性规划（NLP）转化为**混合整数线性规划（MILP）**（注：此处仅引入了连续变量，若原问题无整数变量，则实际为LP；但考虑到运筹模型通常包含整数变量或求解器通用性，保持MILP配置）。
- 求解器 `scip` 非常适合此类转化后的MILP问题，无需修改 `solve_config`。

## 4. 模型验证与分析

### 1. 等价性验证
- **理论依据**：线性化方法基于线性规划的对偶理论和单纯形法的性质。在最小化（或带负系数的最大化）目标下，满足 $y \ge A$ 且 $y \ge 0$ 的变量 $y$ 必然收敛于 $\max(0, A)$。
- **验证方法**：
  - 构造测试用例：设定某资源 $r$ 的 `PARAM_RESOURCE_MIN_QTY` 为 100。
  - 场景A：实际流量为 120。此时 $120 \ge 100$，约束变为 $y_r + 120 \ge 100 \Rightarrow y_r \ge -20$。结合 $y_r \ge 0$ 和最小化 $y_r$，得 $y_r = 0$。惩罚为 0。符合预期。
  - 场景B：实际流量为 80。此时 $80 < 100$，约束变为 $y_r + 80 \ge 100 \Rightarrow y_r \ge 20$。结合最小化 $y_r$，得 $y_r = 20$。惩罚为 $20 \times \text{Price} \times \text{Ratio}$。符合预期。

### 2. 求解效率分析
- **复杂度**：新增了 $|RESOURCE\_IDS|$ 个连续变量和 $|RESOURCE\_IDS|$ 个线性约束。对于典型的天然气调度问题，资源数量级通常在几十到几百，对求解规模影响极小。
- **效率**：转化后的模型为纯线性模型，消除了非光滑性，SCIP/Gurobi等求解器可以利用成熟的基算法、预处理技术和割平面算法，求解速度和稳定性将显著优于原非线性模型。

### 3. 边界条件说明
- **适用范围**：该转化策略在所有参数为非负实数的情况下均有效。
- **失效场景**：无。该线性化是精确转化，不存在分段线性化在区间外的精度问题，也不依赖凸性假设。

## 终版完整DSL

```json
{
  "meta_info": {
    "scene_id": "gas_city_gate_dispatch_profit",
    "scene_type": "混合优化",
    "creator": "auto_gen_by_llm",
    "version": "v1.0.1",
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
            "is_required": false,
            "default_value": 0
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
            "is_required": false,
            "default_value": 0
          },
          {
            "name": "unit_price",
            "type": "float",
            "desc": "资源单价",
            "is_required": true
          },
          {
            "name": "no_discuss_percent",
            "type": "float",
            "desc": "照付不议系数",
            "is_required": false,
            "default_value": 0
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
            "desc": "设计输气能力上限",
            "is_required": true
          },
          {
            "name": "unit_price",
            "type": "float",
            "desc": "管输单价",
            "is_required": true
          },
          {
            "name": "min_amount",
            "type": "float",
            "desc": "最小输气量",
            "is_required": false,
            "default_value": 0
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
        "set_name": "DEMAND_IDS",
        "source": "monthly_demand_pool.demand_plan_code",
        "desc": "需求计划ID集合"
      },
      {
        "set_name": "RESOURCE_IDS",
        "source": "monthly_resource_pool.purchase_agreement_no",
        "desc": "资源采购合同ID集合"
      },
      {
        "set_name": "TRANSPORT_IDS",
        "source": "monthly_transport_pool.id",
        "desc": "管输运力ID集合"
      },
      {
        "set_name": "STATION_IDS",
        "source": "ontology_city_gas_station_info.gate_station_code",
        "desc": "城燃门站ID集合"
      },
      {
        "set_name": "FEASIBLE_PATHS",
        "source": "path_query.paths",
        "desc": "可行路径集合，每个元素为[资源节点ID, 边ID, ..., 门站节点ID, 边ID, 需求节点ID]的列表"
      }
    ],
    "parameters": [
      {
        "param_name": "PARAM_DEMAND_QUANTITY",
        "source": "monthly_demand_pool.quantity",
        "index_sets": [
          "DEMAND_IDS"
        ],
        "data_type": "float",
        "desc": "需求计划量"
      },
      {
        "param_name": "PARAM_SELLING_PRICE",
        "source": "monthly_demand_pool.unit_selling_price",
        "index_sets": [
          "DEMAND_IDS"
        ],
        "data_type": "float",
        "desc": "销售单价"
      },
      {
        "param_name": "PARAM_MIN_DEMAND_QTY",
        "source": "monthly_demand_pool.minimum_satisfy_quantity",
        "index_sets": [
          "DEMAND_IDS"
        ],
        "data_type": "float",
        "desc": "最小需求满足量"
      },
      {
        "param_name": "PARAM_RESOURCE_CAPACITY",
        "source": "monthly_resource_pool.quantity",
        "index_sets": [
          "RESOURCE_IDS"
        ],
        "data_type": "float",
        "desc": "资源供应上限"
      },
      {
        "param_name": "PARAM_RESOURCE_MIN_QTY",
        "source": "monthly_resource_pool.min_quantity",
        "index_sets": [
          "RESOURCE_IDS"
        ],
        "data_type": "float",
        "desc": "资源最小提取量（照付不议基准）"
      },
      {
        "param_name": "PARAM_RESOURCE_PRICE",
        "source": "monthly_resource_pool.unit_price",
        "index_sets": [
          "RESOURCE_IDS"
        ],
        "data_type": "float",
        "desc": "资源采购单价"
      },
      {
        "param_name": "PARAM_TAKE_OR_PAY_RATIO",
        "source": "monthly_resource_pool.no_discuss_percent",
        "index_sets": [
          "RESOURCE_IDS"
        ],
        "data_type": "float",
        "desc": "照付不议惩罚系数"
      },
      {
        "param_name": "PARAM_TRANSPORT_CAPACITY",
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
        "desc": "管输单价"
      },
      {
        "param_name": "PARAM_TRANSPORT_MIN_AMOUNT",
        "source": "monthly_transport_pool.min_amount",
        "index_sets": [
          "TRANSPORT_IDS"
        ],
        "data_type": "float",
        "desc": "管输最小输气量"
      },
      {
        "param_name": "PARAM_STATION_UPPER_BOUND",
        "source": "ontology_city_gas_station_info.upper_bound",
        "index_sets": [
          "STATION_IDS"
        ],
        "data_type": "float",
        "desc": "门站业务上限"
      },
      {
        "param_name": "PARAM_STATION_LOWER_BOUND",
        "source": "ontology_city_gas_station_info.lower_bound",
        "index_sets": [
          "STATION_IDS"
        ],
        "data_type": "float",
        "desc": "门站业务下限"
      }
    ],
    "links": []
  },
  "decision_vars": [
    {
      "var_name": "VAR_PATH_FLOW",
      "var_type": "continuous",
      "index_sets": [
        "FEASIBLE_PATHS"
      ],
      "lower_bound": 0,
      "desc": "路径上的天然气流量"
    },
    {
      "var_name": "VAR_TAKE_OR_PAY_SHORTAGE",
      "var_type": "continuous",
      "index_sets": [
        "RESOURCE_IDS"
      ],
      "lower_bound": 0,
      "desc": "照付不议惩罚基数：资源实际提取量低于最小提取量的差额"
    }
  ],
  "objective": {
    "obj_type": "maximize",
    "obj_terms": [
      {
        "term_name": "TERM_SALES_REVENUE",
        "expression": "sum(VAR_PATH_FLOW[p] * PARAM_SELLING_PRICE[p[-1]] for p in FEASIBLE_PATHS)",
        "coefficient": 1,
        "desc": "销售收入：路径流量 * 终点销售单价"
      },
      {
        "term_name": "TERM_RESOURCE_COST",
        "expression": "sum(VAR_PATH_FLOW[p] * PARAM_RESOURCE_PRICE[p[0]] for p in FEASIBLE_PATHS)",
        "coefficient": -1,
        "desc": "资源采购成本：路径流量 * 起点资源单价"
      },
      {
        "term_name": "TERM_TRANSPORT_COST",
        "expression": "sum(VAR_PATH_FLOW[p] * sum(PARAM_TRANSPORT_PRICE[e] for e in p if type(e)==int and e in TRANSPORT_IDS) for p in FEASIBLE_PATHS)",
        "coefficient": -1,
        "desc": "管输运力成本：路径流量 * 路径上所有边的管输单价之和"
      },
      {
        "term_name": "TERM_TAKE_OR_PAY_PENALTY",
        "expression": "sum(VAR_TAKE_OR_PAY_SHORTAGE[r] * PARAM_RESOURCE_PRICE[r] * PARAM_TAKE_OR_PAY_RATIO[r] for r in RESOURCE_IDS)",
        "coefficient": -1,
        "desc": "照付不议惩罚成本：辅助变量(差额) * 单价 * 系数"
      }
    ],
    "desc": "最大化总利润 = 销售收入 - 资源成本 - 运输成本 - 照付不议惩罚"
  },
  "constraints": [
    {
      "constraint_id": "CONST_RESOURCE_CAPACITY",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[0] == r)",
      "right_expression": "PARAM_RESOURCE_CAPACITY[r]",
      "index_sets": [
        "RESOURCE_IDS"
      ],
      "priority": 1,
      "desc": "资源供应上限约束：从资源r出发的流量总和不超过资源上限"
    },
    {
      "constraint_id": "CONST_DEMAND_CAPACITY",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[-1] == d)",
      "right_expression": "PARAM_DEMAND_QUANTITY[d]",
      "index_sets": [
        "DEMAND_IDS"
      ],
      "priority": 1,
      "desc": "需求满足上限约束：到达需求d的流量总和不超过需求计划量"
    },
    {
      "constraint_id": "CONST_TRANSPORT_CAPACITY",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if t in p)",
      "right_expression": "PARAM_TRANSPORT_CAPACITY[t]",
      "index_sets": [
        "TRANSPORT_IDS"
      ],
      "priority": 1,
      "desc": "管输运力上限约束：经过管道t的流量总和不超过设计能力"
    },
    {
      "constraint_id": "CONST_STATION_CAPACITY",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if s in p)",
      "right_expression": "PARAM_STATION_UPPER_BOUND[s]",
      "index_sets": [
        "STATION_IDS"
      ],
      "priority": 1,
      "desc": "门站业务上限约束：经过门站s的流量总和不超过业务上限"
    },
    {
      "constraint_id": "CONST_STATION_MIN_FLOW",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if s in p)",
      "right_expression": "PARAM_STATION_LOWER_BOUND[s]",
      "index_sets": [
        "STATION_IDS"
      ],
      "priority": 1,
      "desc": "门站业务下限约束：经过门站s的流量总和不低于业务下限"
    },
    {
      "constraint_id": "CONST_TRANSPORT_MIN_AMOUNT",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if t in p)",
      "right_expression": "PARAM_TRANSPORT_MIN_AMOUNT[t]",
      "index_sets": [
        "TRANSPORT_IDS"
      ],
      "priority": 2,
      "desc": "管输最小量约束：经过管道t的流量需满足最小输气量要求"
    },
    {
      "constraint_id": "CONST_DEMAND_MIN_SATISFY",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[-1] == d)",
      "right_expression": "PARAM_MIN_DEMAND_QTY[d]",
      "index_sets": [
        "DEMAND_IDS"
      ],
      "priority": 2,
      "relaxable": true,
      "desc": "需求最小满足量约束：到达需求d的流量需满足最小满足量"
    },
    {
      "constraint_id": "CONST_TAKE_OR_PAY_LINEARIZATION",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "VAR_TAKE_OR_PAY_SHORTAGE[r] + sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[0] == r)",
      "right_expression": "PARAM_RESOURCE_MIN_QTY[r]",
      "index_sets": [
        "RESOURCE_IDS"
      ],
      "priority": 1,
      "desc": "照付不议线性化约束：辅助变量 + 实际提取量 >= 最小提取量。结合最小化目标，使辅助变量等价于 max(0, 最小提取量 - 实际提取量)"
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
        "name": "take_or_pay_penalty_amount",
        "expression": "VAR_TAKE_OR_PAY_SHORTAGE[r] * PARAM_RESOURCE_PRICE[r] * PARAM_TAKE_OR_PAY_RATIO[r]",
        "desc": "照付不议惩罚金额"
      }
    ],
    "output_format": "csv",
    "output_path": "./optimization_result"
  }
}
```