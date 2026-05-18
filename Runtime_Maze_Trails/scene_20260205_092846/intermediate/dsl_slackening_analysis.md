# DSL硬约束松弛优化分析报告

## LLM完整响应

# DSL约束软化方案

## 1. 可软化约束识别
根据任务要求，需对模型中的硬边界约束和最小量达标约束进行软化，同时保留定义类和守恒类核心约束。识别结果如下：

**可软化约束（需修改）：**
1.  **资源供应量上限约束 (CONST_RESOURCE_CAPACITY)**：属于场景1（硬边界上限），允许突破资源总量。
2.  **需求满足量上限约束 (CONST_DEMAND_LIMIT)**：属于场景1（硬边界上限），允许突破需求总量（即允许超供）。
3.  **管输运力能力上限约束 (CONST_TRANSPORT_CAPACITY)**：属于场景1（硬边界上限），允许突破设计运力。
4.  **门站业务上限约束 (CONST_STATION_CAPACITY)**：属于场景1（硬边界上限），允许突破门站上限。
5.  **门站业务下限约束 (CONST_STATION_MIN_FLOW)**：属于场景1（硬边界下限），允许低于业务下限。
6.  **运输最小量约束 (CONST_TRANSPORT_MIN_AMOUNT)**：属于场景2（最小量达标），允许未达最小运输量。
7.  **需求最小满足量约束 (CONST_DEMAND_MIN_SATISFY)**：属于场景2（最小量达标），允许未达最小需求量。

**不可软化约束（严格保留）：**
1.  **照付不议未满足量定义约束 (CONST_SHORTFALL_DEF)**：属于数学定义类约束，用于计算惩罚成本，必须严格保留。

## 2. 松弛变量设计
根据识别结果，设计以下松弛变量：

**场景1：硬边界约束松弛（惩罚系数 100）**
1.  `VAR_resource_surplus_slack`：资源上限过剩松弛，索引集 `RESOURCE_NODES`。
2.  `VAR_demand_surplus_slack`：需求上限过剩松弛，索引集 `DEMAND_NODES`。
3.  `VAR_transport_surplus_slack`：运力上限过剩松弛，索引集 `TRANSPORT_EDGES`。
4.  `VAR_station_surplus_slack`：门站上限过剩松弛，索引集 `GATE_STATIONS`。
5.  `VAR_station_slack`：门站下限不足松弛，索引集 `GATE_STATIONS`。

**场景2：最小量达标兜底松弛（惩罚系数 50）**
1.  `VAR_transport_min_cover_slack`：运输最小量缺口松弛，索引集 `TRANSPORT_EDGES`。
2.  `VAR_demand_min_cover_slack`：需求最小量缺口松弛，索引集 `DEMAND_NODES`。

## 3. 约束软化实施
1.  **上限约束软化**：将 `实际量 ≤ 边界值` 修改为 `实际量 ≤ 边界值 + surplus_slack`。
2.  **下限约束软化**：将 `实际量 ≥ 边界值` 修改为 `实际量 + slack ≥ 边界值`。
3.  **最小量约束软化**：将 `实际量 ≥ 最小量` 修改为 `实际量 + min_cover_slack ≥ 最小量`。
4.  **目标函数修改**：在最大化利润目标中，减去所有松弛变量的惩罚成本（`sum(松弛变量 * 惩罚系数)`）。

## 4. 设计说明总结
本方案针对天然气资源流动优化模型，新增7类松弛变量以解决潜在无解问题并提升达标率。其中，5类硬边界松弛（系数100）用于资源、运力及门站上下限的紧急松绑；2类最小量兜底松弛（系数50）用于保障运输和需求的基本达标。修改了7个业务约束，严格保留了照付不议定义等核心逻辑。通过差异化惩罚设计，在保障模型可解性的同时，优先维护核心业务收益。

## 终版完整DSL

```json
{
  "meta_info": {
    "scene_id": "gas_matching_optimization",
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
            "desc": "单位销售价格",
            "is_required": true
          },
          {
            "name": "minimum_satisfy_quantity",
            "type": "float",
            "desc": "最小满足量",
            "is_required": false,
            "default_value": "0"
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
            "desc": "资源总量",
            "is_required": true
          },
          {
            "name": "min_quantity",
            "type": "float",
            "desc": "最小提取量（照付不议量）",
            "is_required": false,
            "default_value": "0"
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
            "default_value": "0"
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
            "desc": "设计输气能力",
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
            "is_required": false,
            "default_value": "0"
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
        "set_name": "DEMAND_NODES",
        "source": "monthly_demand_pool.demand_plan_code",
        "desc": "需求节点集合"
      },
      {
        "set_name": "RESOURCE_NODES",
        "source": "monthly_resource_pool.purchase_agreement_no",
        "desc": "资源节点集合"
      },
      {
        "set_name": "TRANSPORT_EDGES",
        "source": "monthly_transport_pool.id",
        "desc": "运输边集合"
      },
      {
        "set_name": "GATE_STATIONS",
        "source": "ontology_city_gas_station_info.gate_station_code",
        "desc": "门站节点集合"
      },
      {
        "set_name": "FEASIBLE_PATHS",
        "source": "path_query.paths",
        "desc": "可行路径集合，每个元素为[节点ID, 边ID, 节点ID, ...]的列表"
      }
    ],
    "parameters": [
      {
        "param_name": "PARAM_DEMAND_QTY",
        "source": "monthly_demand_pool.quantity",
        "index_sets": [
          "DEMAND_NODES"
        ],
        "data_type": "float",
        "desc": "需求总量"
      },
      {
        "param_name": "PARAM_SELLING_PRICE",
        "source": "monthly_demand_pool.unit_selling_price",
        "index_sets": [
          "DEMAND_NODES"
        ],
        "data_type": "float",
        "desc": "单位销售价格"
      },
      {
        "param_name": "PARAM_MIN_DEMAND_QTY",
        "source": "monthly_demand_pool.minimum_satisfy_quantity",
        "index_sets": [
          "DEMAND_NODES"
        ],
        "data_type": "float",
        "desc": "最小需求满足量"
      },
      {
        "param_name": "PARAM_RESOURCE_CAPACITY",
        "source": "monthly_resource_pool.quantity",
        "index_sets": [
          "RESOURCE_NODES"
        ],
        "data_type": "float",
        "desc": "资源最大可供应量"
      },
      {
        "param_name": "PARAM_RESOURCE_MIN_QTY",
        "source": "monthly_resource_pool.min_quantity",
        "index_sets": [
          "RESOURCE_NODES"
        ],
        "data_type": "float",
        "desc": "资源最小提取量（照付不议）"
      },
      {
        "param_name": "PARAM_RESOURCE_PRICE",
        "source": "monthly_resource_pool.unit_price",
        "index_sets": [
          "RESOURCE_NODES"
        ],
        "data_type": "float",
        "desc": "资源采购单价"
      },
      {
        "param_name": "PARAM_NOP_PERCENT",
        "source": "monthly_resource_pool.no_discuss_percent",
        "index_sets": [
          "RESOURCE_NODES"
        ],
        "data_type": "float",
        "desc": "照付不议惩罚系数"
      },
      {
        "param_name": "PARAM_TRANSPORT_CAPACITY",
        "source": "monthly_transport_pool.design_gas_capacity",
        "index_sets": [
          "TRANSPORT_EDGES"
        ],
        "data_type": "float",
        "desc": "运输路径设计能力"
      },
      {
        "param_name": "PARAM_TRANSPORT_PRICE",
        "source": "monthly_transport_pool.unit_price",
        "index_sets": [
          "TRANSPORT_EDGES"
        ],
        "data_type": "float",
        "desc": "运输单价"
      },
      {
        "param_name": "PARAM_TRANSPORT_MIN_AMOUNT",
        "source": "monthly_transport_pool.min_amount",
        "index_sets": [
          "TRANSPORT_EDGES"
        ],
        "data_type": "float",
        "desc": "运输最小量"
      },
      {
        "param_name": "PARAM_STATION_UPPER",
        "source": "ontology_city_gas_station_info.upper_bound",
        "index_sets": [
          "GATE_STATIONS"
        ],
        "data_type": "float",
        "desc": "门站业务上限"
      },
      {
        "param_name": "PARAM_STATION_LOWER",
        "source": "ontology_city_gas_station_info.lower_bound",
        "index_sets": [
          "GATE_STATIONS"
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
      "var_name": "VAR_SHORTFALL",
      "var_type": "continuous",
      "index_sets": [
        "RESOURCE_NODES"
      ],
      "lower_bound": 0,
      "desc": "照付不议未满足量：辅助变量，用于线性化max(0, min_qty - actual_qty)"
    },
    {
      "var_name": "VAR_resource_surplus_slack",
      "var_type": "continuous",
      "index_sets": [
        "RESOURCE_NODES"
      ],
      "lower_bound": 0,
      "desc": "【场景1-上限松弛】资源硬边界上限过剩松弛变量，代表突破资源总量的规模，非负"
    },
    {
      "var_name": "VAR_demand_surplus_slack",
      "var_type": "continuous",
      "index_sets": [
        "DEMAND_NODES"
      ],
      "lower_bound": 0,
      "desc": "【场景1-上限松弛】需求硬边界上限过剩松弛变量，代表突破需求总量的规模，非负"
    },
    {
      "var_name": "VAR_transport_surplus_slack",
      "var_type": "continuous",
      "index_sets": [
        "TRANSPORT_EDGES"
      ],
      "lower_bound": 0,
      "desc": "【场景1-上限松弛】运力硬边界上限过剩松弛变量，代表突破设计运力的规模，非负"
    },
    {
      "var_name": "VAR_station_surplus_slack",
      "var_type": "continuous",
      "index_sets": [
        "GATE_STATIONS"
      ],
      "lower_bound": 0,
      "desc": "【场景1-上限松弛】门站硬边界上限过剩松弛变量，代表突破门站上限的规模，非负"
    },
    {
      "var_name": "VAR_station_slack",
      "var_type": "continuous",
      "index_sets": [
        "GATE_STATIONS"
      ],
      "lower_bound": 0,
      "desc": "【场景1-下限松弛】门站硬边界下限不足松弛变量，代表未达门站下限的缺口，非负"
    },
    {
      "var_name": "VAR_transport_min_cover_slack",
      "var_type": "continuous",
      "index_sets": [
        "TRANSPORT_EDGES"
      ],
      "lower_bound": 0,
      "desc": "【场景2-最小量兜底】运输最小量达标缺口松弛变量，代表未达最小运输量的缺口，非负"
    },
    {
      "var_name": "VAR_demand_min_cover_slack",
      "var_type": "continuous",
      "index_sets": [
        "DEMAND_NODES"
      ],
      "lower_bound": 0,
      "desc": "【场景2-最小量兜底】需求最小量达标缺口松弛变量，代表未达最小需求量的缺口，非负"
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
        "expression": "sum(VAR_PATH_FLOW[p] * sum(PARAM_TRANSPORT_PRICE[e] for e in p if type(e)==int and e in TRANSPORT_EDGES) for p in FEASIBLE_PATHS)",
        "coefficient": -1,
        "desc": "运输成本：路径流量 * 路径上所有边的运输单价之和"
      },
      {
        "term_name": "TERM_TAKE_OR_PAY_PENALTY",
        "expression": "sum(VAR_SHORTFALL[r] * PARAM_RESOURCE_PRICE[r] * PARAM_NOP_PERCENT[r] for r in RESOURCE_NODES)",
        "coefficient": -1,
        "desc": "照付不议惩罚成本：未满足量 * 单价 * 系数"
      },
      {
        "term_name": "TERM_SLACK_PENALTY",
        "expression": "sum(VAR_resource_surplus_slack[r] * 100 for r in RESOURCE_NODES) + sum(VAR_demand_surplus_slack[d] * 100 for d in DEMAND_NODES) + sum(VAR_transport_surplus_slack[e] * 100 for e in TRANSPORT_EDGES) + sum(VAR_station_surplus_slack[s] * 100 for s in GATE_STATIONS) + sum(VAR_station_slack[s] * 100 for s in GATE_STATIONS) + sum(VAR_transport_min_cover_slack[e] * 50 for e in TRANSPORT_EDGES) + sum(VAR_demand_min_cover_slack[d] * 50 for d in DEMAND_NODES)",
        "coefficient": -1,
        "desc": "松弛变量惩罚成本：硬边界松弛(系数100) + 最小量兜底松弛(系数50)"
      }
    ],
    "desc": "最大化总利润（销售收入 - 资源成本 - 运输成本 - 照付不议惩罚 - 松弛惩罚）"
  },
  "constraints": [
    {
      "constraint_id": "CONST_RESOURCE_CAPACITY",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[0] == r)",
      "right_expression": "PARAM_RESOURCE_CAPACITY[r] + VAR_resource_surplus_slack[r]",
      "index_sets": [
        "RESOURCE_NODES"
      ],
      "priority": 1,
      "desc": "【场景1-上限松弛】资源供应量上限约束：从资源点流出的总量不超过资源总量+松弛"
    },
    {
      "constraint_id": "CONST_DEMAND_LIMIT",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[-1] == d)",
      "right_expression": "PARAM_DEMAND_QTY[d] + VAR_demand_surplus_slack[d]",
      "index_sets": [
        "DEMAND_NODES"
      ],
      "priority": 1,
      "desc": "【场景1-上限松弛】需求满足量上限约束：流入需求点的总量不超过需求量+松弛"
    },
    {
      "constraint_id": "CONST_TRANSPORT_CAPACITY",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if e in p)",
      "right_expression": "PARAM_TRANSPORT_CAPACITY[e] + VAR_transport_surplus_slack[e]",
      "index_sets": [
        "TRANSPORT_EDGES"
      ],
      "priority": 1,
      "desc": "【场景1-上限松弛】管输运力能力上限约束：经过运输边的流量不超过设计能力+松弛"
    },
    {
      "constraint_id": "CONST_STATION_CAPACITY",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if s in p)",
      "right_expression": "PARAM_STATION_UPPER[s] + VAR_station_surplus_slack[s]",
      "index_sets": [
        "GATE_STATIONS"
      ],
      "priority": 1,
      "desc": "【场景1-上限松弛】门站业务上限约束：经过门站的流量不超过上限+松弛"
    },
    {
      "constraint_id": "CONST_STATION_MIN_FLOW",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if s in p) + VAR_station_slack[s]",
      "right_expression": "PARAM_STATION_LOWER[s]",
      "index_sets": [
        "GATE_STATIONS"
      ],
      "priority": 1,
      "desc": "【场景1-下限松弛】门站业务下限约束：经过门站的流量+松弛不低于下限"
    },
    {
      "constraint_id": "CONST_TRANSPORT_MIN_AMOUNT",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if e in p) + VAR_transport_min_cover_slack[e]",
      "right_expression": "PARAM_TRANSPORT_MIN_AMOUNT[e]",
      "index_sets": [
        "TRANSPORT_EDGES"
      ],
      "priority": 2,
      "relaxable": true,
      "desc": "【场景2-最小量兜底】运输最小量约束：流量+缺口松弛需满足最小运输量"
    },
    {
      "constraint_id": "CONST_DEMAND_MIN_SATISFY",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[-1] == d) + VAR_demand_min_cover_slack[d]",
      "right_expression": "PARAM_MIN_DEMAND_QTY[d]",
      "index_sets": [
        "DEMAND_NODES"
      ],
      "priority": 2,
      "relaxable": true,
      "desc": "【场景2-最小量兜底】需求最小满足量约束：流入总量+缺口松弛需满足最小满足量"
    },
    {
      "constraint_id": "CONST_SHORTFALL_DEF",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "VAR_SHORTFALL[r]",
      "right_expression": "PARAM_RESOURCE_MIN_QTY[r] - sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[0] == r)",
      "index_sets": [
        "RESOURCE_NODES"
      ],
      "priority": 1,
      "desc": "不可软化核心约束，禁止修改：照付不议未满足量定义约束：辅助变量 >= 最小提取量 - 实际提取量"
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
        "name": "sales_revenue",
        "expression": "TERM_SALES_REVENUE",
        "desc": "销售收入"
      },
      {
        "name": "resource_cost",
        "expression": "TERM_RESOURCE_COST",
        "desc": "资源成本"
      },
      {
        "name": "transport_cost",
        "expression": "TERM_TRANSPORT_COST",
        "desc": "运输成本"
      },
      {
        "name": "penalty_cost",
        "expression": "TERM_TAKE_OR_PAY_PENALTY",
        "desc": "照付不议惩罚成本"
      }
    ],
    "output_format": "csv",
    "output_path": "./optimization_result"
  }
}
```