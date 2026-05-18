# DSL硬约束松弛优化分析报告

## LLM完整响应

# DSL约束软化方案

## 1. 可软化约束识别
根据模型定义，识别出以下可软化的硬约束及不可软化约束：

**可软化约束（需添加松弛变量）：**
- **资源供应上限约束 (CONST_RESOURCE_CAPACITY)**：属于场景1-上限松弛，允许突破资源上限。
- **管输运力上限约束 (CONST_TRANSPORT_CAPACITY)**：属于场景1-上限松弛，允许突破设计运力。
- **门站业务上限约束 (CONST_STATION_UPPER)**：属于场景1-上限松弛，允许突破门站业务上限。
- **门站业务下限约束 (CONST_STATION_LOWER)**：属于场景1-下限松弛，允许未达下限。
- **需求满足上限约束 (CONST_DEMAND_LIMIT)**：属于场景2-最小量兜底，原模型为`<=`，但业务含义为“需求量”，通常需尽量满足。此处将其转化为“最小量达标”逻辑进行兜底，允许未满足需求量。

**不可软化约束（严格保留）：**
- **照付不议缺口定义 (CONST_TOP_SHORTAGE_DEF)**：属于数学定义类约束，定义了`VAR_RESOURCE_SHORTAGE`与实际流量的关系，不可修改。
- **照付不议缺口上界 (CONST_TOP_SHORTAGE_UPPER)**：属于辅助变量范围约束，用于提升求解效率，不可修改。

## 2. 松弛变量设计
根据场景分类，设计以下松弛变量：

**场景1：硬边界约束松弛（惩罚系数 100）**
1. **资源过剩松弛** `VAR_resource_surplus_slack`：索引集`RESOURCE_IDS`，用于突破资源上限。
2. **运力过剩松弛** `VAR_transport_surplus_slack`：索引集`TRANSPORT_IDS`，用于突破管输运力上限。
3. **门站过剩松弛** `VAR_station_surplus_slack`：索引集`GATE_STATION_IDS`，用于突破门站业务上限。
4. **门站不足松弛** `VAR_station_slack`：索引集`GATE_STATION_IDS`，用于弥补门站业务下限缺口。

**场景2：最小量达标兜底松弛（惩罚系数 50）**
1. **需求缺口松弛** `VAR_demand_min_cover_slack`：索引集`DEMAND_IDS`，用于记录未满足需求计划量的缺口。

## 3. 约束软化实施
- **上限约束软化**：将`实际量 <= 上限`修改为`实际量 <= 上限 + surplus_slack`。
- **下限约束软化**：将`实际量 >= 下限`修改为`实际量 + slack >= 下限`。
- **需求约束软化**：将`实际量 <= 需求量`修改为`实际量 + min_cover_slack >= 需求量`（即允许缺口存在，尽量满足）。
- **目标函数调整**：在最大化利润目标中，减去所有松弛变量的惩罚成本（`sum(slack * penalty)`）。

## 4. 设计说明总结
本方案针对天然气资源流动模型，新增5类松弛变量以解决潜在无解问题。其中4类用于硬边界松绑（资源、运力、门站上下限），惩罚系数100；1类用于需求量达标兜底，惩罚系数50。共修改5个业务约束，保留2个核心定义约束。通过高惩罚优先保障边界合规，低惩罚鼓励满足需求，在提升模型可解性的同时，严格维持利润最大化核心逻辑及物理守恒定律。

## 终版完整DSL

```json
{
  "meta_info": {
    "scene_id": "gas_city_gate_matching_profit",
    "scene_type": "混合优化",
    "creator": "auto_gen_by_llm",
    "version": "v1.1.0_linear_optimized",
    "create_time": "2023-10-27T10:00:00Z",
    "description": "优化后的线性规划模型，显式约束了辅助变量范围以提升求解效率，并添加松弛变量以增强模型可解性。"
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
    },
    {
      "var_name": "VAR_resource_surplus_slack",
      "var_type": "continuous",
      "index_sets": [
        "RESOURCE_IDS"
      ],
      "lower_bound": 0,
      "desc": "【场景1-上限松弛】资源硬边界上限过剩松弛变量，代表突破资源上限的规模，非负"
    },
    {
      "var_name": "VAR_transport_surplus_slack",
      "var_type": "continuous",
      "index_sets": [
        "TRANSPORT_IDS"
      ],
      "lower_bound": 0,
      "desc": "【场景1-上限松弛】运力硬边界上限过剩松弛变量，代表突破运力上限的规模，非负"
    },
    {
      "var_name": "VAR_station_surplus_slack",
      "var_type": "continuous",
      "index_sets": [
        "GATE_STATION_IDS"
      ],
      "lower_bound": 0,
      "desc": "【场景1-上限松弛】门站硬边界上限过剩松弛变量，代表突破门站业务上限的规模，非负"
    },
    {
      "var_name": "VAR_station_slack",
      "var_type": "continuous",
      "index_sets": [
        "GATE_STATION_IDS"
      ],
      "lower_bound": 0,
      "desc": "【场景1-下限松弛】门站硬边界下限不足松弛变量，代表未达门站业务下限的缺口，非负"
    },
    {
      "var_name": "VAR_demand_min_cover_slack",
      "var_type": "continuous",
      "index_sets": [
        "DEMAND_IDS"
      ],
      "lower_bound": 0,
      "desc": "【场景2-最小量兜底】需求最小量达标缺口松弛变量，代表未达需求计划量的缺口，非负；达标时取值为0"
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
      },
      {
        "term_name": "TERM_SLACK_PENALTY",
        "expression": "sum(VAR_resource_surplus_slack[r] * 100 for r in RESOURCE_IDS) + sum(VAR_transport_surplus_slack[t] * 100 for t in TRANSPORT_IDS) + sum(VAR_station_surplus_slack[s] * 100 for s in GATE_STATION_IDS) + sum(VAR_station_slack[s] * 100 for s in GATE_STATION_IDS) + sum(VAR_demand_min_cover_slack[d] * 50 for d in DEMAND_IDS)",
        "coefficient": -1,
        "desc": "松弛变量惩罚成本：硬边界松弛惩罚系数100，需求兜底松弛惩罚系数50"
      }
    ],
    "desc": "最大化总利润（销售收入 - 采购成本 - 运输成本 - 惩罚成本 - 松弛惩罚）"
  },
  "constraints": [
    {
      "constraint_id": "CONST_RESOURCE_CAPACITY",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[0] == r)",
      "right_expression": "PARAM_RESOURCE_CAPACITY[r] + VAR_resource_surplus_slack[r]",
      "index_sets": [
        "RESOURCE_IDS"
      ],
      "priority": 1,
      "desc": "【场景1-上限松弛】资源供应上限约束：从资源r出发的流量总和不超过资源上限，允许通过过剩松弛变量突破"
    },
    {
      "constraint_id": "CONST_DEMAND_LIMIT",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[-1] == d) + VAR_demand_min_cover_slack[d]",
      "right_expression": "PARAM_DEMAND_QTY[d]",
      "index_sets": [
        "DEMAND_IDS"
      ],
      "priority": 1,
      "desc": "【场景2-最小量兜底】需求满足约束：到达需求d的流量总和尽量不低于需求计划量，允许通过缺口松弛变量记录未满足部分"
    },
    {
      "constraint_id": "CONST_TRANSPORT_CAPACITY",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if t in p)",
      "right_expression": "PARAM_TRANSPORT_CAPACITY[t] + VAR_transport_surplus_slack[t]",
      "index_sets": [
        "TRANSPORT_IDS"
      ],
      "priority": 1,
      "desc": "【场景1-上限松弛】管输运力上限约束：经过运输边t的流量总和不超过设计能力，允许通过过剩松弛变量突破"
    },
    {
      "constraint_id": "CONST_STATION_UPPER",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if s in p)",
      "right_expression": "PARAM_STATION_UPPER[s] + VAR_station_surplus_slack[s]",
      "index_sets": [
        "GATE_STATION_IDS"
      ],
      "priority": 1,
      "desc": "【场景1-上限松弛】门站业务上限约束：经过门站s的流量总和不超过业务上限，允许通过过剩松弛变量突破"
    },
    {
      "constraint_id": "CONST_STATION_LOWER",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if s in p) + VAR_station_slack[s]",
      "right_expression": "PARAM_STATION_LOWER[s]",
      "index_sets": [
        "GATE_STATION_IDS"
      ],
      "priority": 1,
      "desc": "【场景1-下限松弛】门站业务下限约束：经过门站s的流量总和不低于业务下限，允许通过不足松弛变量弥补缺口"
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
      "desc": "不可软化核心约束，禁止修改：照付不议缺口定义：缺口 >= 最小提取量 - 实际提取量（结合最小化目标自动实现max(0, ...)）"
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
      "desc": "不可软化核心约束，禁止修改：照付不议缺口上界：缺口不超过最小提取量（辅助约束，缩小可行域，提升求解效率）"
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