# DSL优化分析报告

## LLM完整响应

# 运筹建模DSL非线性优化解决方案

## 1. 非线性要素系统化识别

经过对输入DSL的详细遍历与分析，识别出以下非线性要素：

| 非线性要素名称 | 所在位置 | 数学表达式 | 变量依赖关系 | 非线性类型 |
| :--- | :--- | :--- | :--- | :--- |
| **照付不议惩罚项** | `objective.TERM_TAKE_OR_PAY_PENALTY` | $\sum_{r} VAR\_RESOURCE\_SHORTAGE[r] \times PARAM\_RESOURCE\_PRICE[r] \times PARAM\_TOP\_COEFF[r]$ | $VAR\_RESOURCE\_SHORTAGE[r]$ (连续变量) | **非光滑函数** (隐含 max(0, x)) |
| **照付不议缺口定义** | `constraints.CONST_TOP_SHORTAGE_DEF` | $VAR\_RESOURCE\_SHORTAGE[r] \ge PARAM\_RESOURCE\_MIN\_QTY[r] - \sum_{p \in P_r} VAR\_PATH\_FLOW[p]$ | $VAR\_RESOURCE\_SHORTAGE[r]$, $VAR\_PATH\_FLOW[p]$ | **非光滑函数** (max(0, ...) 的线性化形式) |

**详细分析：**
1.  **照付不议惩罚项**：虽然表达式本身是线性的（变量 $\times$ 常数），但其物理含义是计算“未满足最小提取量的部分”。在数学上，这对应于 $max(0, \text{MinQty} - \text{ActualQty})$。DSL中通过引入辅助变量 `VAR_RESOURCE_SHORTAGE` 并结合最小化目标函数来实现这一逻辑。
2.  **照付不议缺口定义**：约束 $VAR\_RESOURCE\_SHORTAGE[r] \ge \text{MinQty} - \text{ActualQty}$ 仅设定了下界。由于目标函数是最大化利润（即最小化成本，惩罚项系数为负），求解器会自动将 `VAR_RESOURCE_SHORTAGE` 压至最小值。如果 $\text{MinQty} - \text{ActualQty} < 0$，则 `VAR_RESOURCE_SHORTAGE` 的最优值为 0；如果为正，则取该正值。这构成了标准的 $max(0, x)$ 非光滑逻辑的线性化处理。

**结论：**
该DSL中**不存在**需要额外转化的非线性项（如乘积、指数、分段函数等）。原模型已经采用了标准的**混合整数线性规划（MILP）**技巧来处理“照付不议”这一非光滑业务逻辑。模型本质上是线性的。

## 2. 非线性问题等价转化

由于原模型已经是线性模型，无需进行复杂的非线性转化。仅需确认现有逻辑的等价性和完整性。

**现有逻辑验证：**
*   **目标**：Max Profit = Revenue - Cost - Penalty。
*   **惩罚项**：$Cost_{penalty} = \sum (Shortage_r \times Price_r \times Coeff_r)$。
*   **约束**：$Shortage_r \ge MinQty_r - Flow_r$ 且 $Shortage_r \ge 0$（隐含在变量定义中）。
*   **等价性**：
    *   当 $Flow_r \ge MinQty_r$ 时，约束变为 $Shortage_r \le 0$，结合 $Shortage_r \ge 0$，得 $Shortage_r = 0$，惩罚为0。
    *   当 $Flow_r < MinQty_r$ 时，约束变为 $Shortage_r \ge \Delta$。由于惩罚项在目标函数中是负向系数（最小化方向），求解器会强制 $Shortage_r = \Delta$，惩罚为 $\Delta \times Price \times Coeff$。
*   **结果**：该逻辑完美等价于 $Penalty = \max(0, MinQty - Flow) \times Price \times Coeff$。

**优化建议（模型增强）：**
虽然模型是线性的，但为了提高求解效率和数值稳定性，建议对 `CONST_TOP_SHORTAGE_DEF` 约束进行显式化处理，并补充 `VAR_RESOURCE_SHORTAGE` 的显式上界约束，以缩小可行域，辅助求解器进行定界。

## 3. 完整优化模型重构

基于上述分析，重构后的模型保持线性规划（LP）或混合整数线性规划（MILP）形式（取决于是否存在整数变量，当前DSL中全为连续变量，故为LP）。

### 1. 决策变量扩展
*   **保留变量**：
    *   `VAR_PATH_FLOW` ($p \in FEASIBLE\_PATHS$): 连续变量，$\ge 0$。
    *   `VAR_RESOURCE_SHORTAGE` ($r \in RESOURCE\_IDS$): 连续变量，$\ge 0$。
*   **变量物理含义明确**：`VAR_RESOURCE_SHORTAGE` 明确为“照付不议违约量”。

### 2. 目标函数线性化
目标函数已是线性形式，无需修改：
$$ \text{Maximize } Z = \sum_{p} Flow_p \times (Price_{sell, p[-1]} - Price_{buy, p[0]} - \sum_{e \in p} Price_{trans, e}) - \sum_{r} Shortage_r \times Price_{buy, r} \times Coeff_r $$

### 3. 约束条件整合
*   **保留原约束**：资源上限、需求上限、运力上限、门站上下限。
*   **优化约束**：
    *   `CONST_TOP_SHORTAGE_DEF`：保持不变，逻辑正确。
    *   **新增约束**：`CONST_TOP_SHORTAGE_UPPER`。虽然数学上由目标函数控制，但显式增加 $Shortage_r \le MinQty_r$ 可以显著缩小可行域，提升求解速度。

### 4. 求解配置适配
*   模型类型：线性规划（LP）。
*   求解器：SCIP（支持LP/MIP）。
*   参数调整：由于是LP问题，求解速度通常很快，保持默认参数即可。

## 4. 模型验证与分析

1.  **等价性验证**：
    *   原模型通过“大M法”或“目标函数惩罚法”的变体处理了 $\max(0, x)$ 函数。
    *   验证方法：构造极端测试用例。
        *   用例1：资源提取量 > 最小提取量。预期 `VAR_RESOURCE_SHORTAGE` = 0。
        *   用例2：资源提取量 < 最小提取量。预期 `VAR_RESOURCE_SHORTAGE` = 差值。
    *   结论：原模型逻辑完全正确，无需修改核心公式。

2.  **求解效率分析**：
    *   **复杂度**：模型为纯连续变量线性规划。变量数量为 $|P| + |R|$，约束数量约为 $|R| + |D| + |T| + |S|$。
    *   **优化建议**：
        *   显式增加 `VAR_RESOURCE_SHORTAGE` 的上界约束（$ \le PARAM\_RESOURCE\_MIN\_QTY$），这有助于单纯形法更快确定极点。
        *   由于是LP问题，无需设置MIP相关的Gap参数（虽然SCIP会自动忽略）。

3.  **边界条件说明**：
    *   模型在所有参数非负的情况下均有效。
    *   若 `PARAM_TOP_COEFF` 极大，模型会强制满足最小提取量（即 $Flow \ge MinQty$），除非受限于其他硬性约束（如资源上限、运力上限）。

## 终版完整DSL

```json
{
  "meta_info": {
    "scene_id": "gas_city_gate_matching_profit",
    "scene_type": "混合优化",
    "creator": "auto_gen_by_llm",
    "version": "v1.1.0_linear_optimized",
    "create_time": "2023-10-27T10:00:00Z",
    "description": "优化后的线性规划模型，显式约束了辅助变量范围以提升求解效率。"
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
            "desc": "运力ID",
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
        "set_name": "RESOURCE_IDS",
        "source": "monthly_resource_pool.purchase_agreement_no",
        "desc": "资源合同ID集合"
      },
      {
        "set_name": "DEMAND_IDS",
        "source": "monthly_demand_pool.demand_plan_code",
        "desc": "需求计划ID集合"
      },
      {
        "set_name": "TRANSPORT_IDS",
        "source": "monthly_transport_pool.id",
        "desc": "管输运力ID集合"
      },
      {
        "set_name": "GATE_STATION_IDS",
        "source": "ontology_city_gas_station_info.gate_station_code",
        "desc": "城燃门站ID集合"
      },
      {
        "set_name": "FEASIBLE_PATHS",
        "source": "path_query.paths",
        "desc": "可行路径集合，每个元素为[资源节点ID, 下载站ID, 运输边ID, 门站ID, 需求节点ID]的列表"
      }
    ],
    "parameters": [
      {
        "param_name": "PARAM_DEMAND_QTY",
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
        "desc": "需求最小满足量"
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
        "param_name": "PARAM_TOP_COEFF",
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
        "desc": "管输运输单价"
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
          "GATE_STATION_IDS"
        ],
        "data_type": "float",
        "desc": "门站业务上限"
      },
      {
        "param_name": "PARAM_STATION_LOWER",
        "source": "ontology_city_gas_station_info.lower_bound",
        "index_sets": [
          "GATE_STATION_IDS"
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
      "desc": "路径上的天然气流量"
    },
    {
      "var_name": "VAR_RESOURCE_SHORTAGE",
      "var_type": "continuous",
      "index_sets": [
        "RESOURCE_IDS"
      ],
      "lower_bound": 0,
      "desc": "资源未满足最小提取量的部分（用于计算惩罚），等价于 max(0, MinQty - ActualQty)"
    }
  ],
  "objective": {
    "obj_type": "maximize",
    "obj_terms": [
      {
        "term_name": "TERM_SALES_REVENUE",
        "expression": "sum(VAR_PATH_FLOW[p] * PARAM_SELLING_PRICE[p[-1]] for p in FEASIBLE_PATHS)",
        "coefficient": 1,
        "desc": "销售收入：路径流量 * 终点需求单价"
      },
      {
        "term_name": "TERM_RESOURCE_COST",
        "expression": "sum(VAR_PATH_FLOW[p] * PARAM_RESOURCE_PRICE[p[0]] for p in FEASIBLE_PATHS)",
        "coefficient": -1,
        "desc": "资源采购成本：路径流量 * 起点资源单价"
      },
      {
        "term_name": "TERM_TRANSPORT_COST",
        "expression": "sum(VAR_PATH_FLOW[p] * sum(PARAM_TRANSPORT_PRICE[e] for e in p if e in TRANSPORT_IDS) for p in FEASIBLE_PATHS)",
        "coefficient": -1,
        "desc": "管输运输成本：路径流量 * 路径上所有运输边的单价之和"
      },
      {
        "term_name": "TERM_TAKE_OR_PAY_PENALTY",
        "expression": "sum(VAR_RESOURCE_SHORTAGE[r] * PARAM_RESOURCE_PRICE[r] * PARAM_TOP_COEFF[r] for r in RESOURCE_IDS)",
        "coefficient": -1,
        "desc": "照付不议惩罚成本：资源缺口 * 单价 * 惩罚系数"
      }
    ],
    "desc": "最大化总利润（销售收入 - 采购成本 - 运输成本 - 惩罚成本）"
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
      "constraint_id": "CONST_DEMAND_LIMIT",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[-1] == d)",
      "right_expression": "PARAM_DEMAND_QTY[d]",
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
      "desc": "管输运力上限约束：经过运输边t的流量总和不超过设计能力"
    },
    {
      "constraint_id": "CONST_STATION_UPPER",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if s in p)",
      "right_expression": "PARAM_STATION_UPPER[s]",
      "index_sets": [
        "GATE_STATION_IDS"
      ],
      "priority": 1,
      "desc": "门站业务上限约束：经过门站s的流量总和不超过业务上限"
    },
    {
      "constraint_id": "CONST_STATION_LOWER",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if s in p)",
      "right_expression": "PARAM_STATION_LOWER[s]",
      "index_sets": [
        "GATE_STATION_IDS"
      ],
      "priority": 1,
      "desc": "门站业务下限约束：经过门站s的流量总和不低于业务下限"
    },
    {
      "constraint_id": "CONST_TOP_SHORTAGE_DEF",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "VAR_RESOURCE_SHORTAGE[r]",
      "right_expression": "PARAM_RESOURCE_MIN_QTY[r] - sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[0] == r)",
      "index_sets": [
        "RESOURCE_IDS"
      ],
      "priority": 1,
      "desc": "照付不议缺口定义：缺口 >= 最小提取量 - 实际提取量（结合最小化目标自动实现max(0, ...)）"
    },
    {
      "constraint_id": "CONST_TOP_SHORTAGE_UPPER",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "VAR_RESOURCE_SHORTAGE[r]",
      "right_expression": "PARAM_RESOURCE_MIN_QTY[r]",
      "index_sets": [
        "RESOURCE_IDS"
      ],
      "priority": 2,
      "desc": "照付不议缺口上界：缺口不超过最小提取量（辅助约束，缩小可行域，提升求解效率）"
    }
  ],
  "solve_config": {
    "solver_type": "scip",
    "solver_params": {
      "timeout": 300,
      "gap": 0.01,
      "threads": 4,
      "lp/emphasis": "optimal"
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
        "name": "resource_shortage",
        "expression": "VAR_RESOURCE_SHORTAGE",
        "desc": "资源照付不议缺口量"
      },
      {
        "name": "total_profit",
        "expression": "objective.value",
        "desc": "总利润"
      }
    ],
    "output_format": "csv",
    "output_path": "./optimization_result"
  }
}
```