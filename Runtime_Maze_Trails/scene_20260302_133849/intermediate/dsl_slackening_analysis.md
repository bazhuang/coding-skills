# DSL硬约束松弛优化分析报告

## LLM完整响应

# DSL约束软化方案

## 1. 可软化约束识别
根据模型定义，识别出以下可软化的硬约束：
- **资源总量上限约束 (CONST_RESOURCE_CAPACITY)**：属于场景1（硬边界上限），允许突破资源总量上限。
- **管输运力上限约束 (CONST_TRANSPORT_CAP)**：属于场景1（硬边界上限），允许突破设计输气能力。
- **门站业务上限约束 (CONST_STATION_UPPER)**：属于场景1（硬边界上限），允许突破门站业务上限。
- **管输运力下限约束 (CONST_TRANSPORT_MIN)**：属于场景2（最小量达标），尽量满足最小输气量，允许缺口。
- **门站业务下限约束 (CONST_STATION_LOWER)**：属于场景2（最小量达标），尽量满足门站下限流量，允许缺口。
- **需求最小满足量约束 (CONST_MIN_DEMAND)**：属于场景2（最小量达标），尽量满足最小需求量，允许缺口。

**不可软化约束**：
- 需求量上限约束 (CONST_DEMAND_QTY)：通常作为市场天花板，不建议突破。
- 照付不议线性化约束 (CONST_TAKE_OR_PAY_LINEARIZATION)：属于定义性约束，用于计算惩罚基数，不可软化。

## 2. 松弛变量设计
根据场景分类，设计以下松弛变量：

**场景1：硬边界上限松弛（过剩松弛）**
1. `VAR_resource_surplus_slack`：索引集 `RESOURCE_IDS`，用于资源总量上限。
2. `VAR_transport_surplus_slack`：索引集 `TRANSPORT_IDS`，用于管输运力上限。
3. `VAR_station_surplus_slack`：索引集 `GATE_STATION_IDS`，用于门站业务上限。

**场景2：最小量达标兜底松弛（缺口松弛）**
1. `VAR_transport_min_cover_slack`：索引集 `TRANSPORT_IDS`，用于管输最小输气量。
2. `VAR_station_min_cover_slack`：索引集 `GATE_STATION_IDS`，用于门站业务下限。
3. `VAR_demand_min_cover_slack`：索引集 `DEMAND_IDS`，用于需求最小满足量。

## 3. 约束软化实施
- **上限约束软化**：将 `实际量 ≤ 上限` 修改为 `实际量 ≤ 上限 + surplus_slack`。
- **最小量约束软化**：将 `实际量 ≥ 最小量` 修改为 `实际量 + min_cover_slack ≥ 最小量`。

## 4. 惩罚成本设置
- **场景1惩罚系数**：100（高惩罚，仅在无解时突破）。
- **场景2惩罚系数**：50（中等惩罚，鼓励达标但允许缺口）。
- **目标函数调整**：在最大化利润目标中，减去所有松弛变量的惩罚成本。

## 终版完整DSL

```json
{
  "meta_info": {
    "scene_id": "gas_city_gate_dispatch_profit",
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
            "desc": "资源总量",
            "is_required": true
          },
          {
            "name": "min_quantity",
            "type": "float",
            "desc": "最小提取量（照付不议基准）",
            "is_required": true
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
            "desc": "管输单价",
            "is_required": true
          },
          {
            "name": "min_amount",
            "type": "float",
            "desc": "最小输气量",
            "is_required": true
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
        "desc": "资源合同ID集合"
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
        "source": "path_query",
        "desc": "可行路径集合，每个元素为[资源节点ID, 边ID, ..., 门站ID, ..., 边ID, 需求节点ID]的列表，由图数据库查询生成"
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
        "desc": "资源合同总量上限"
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
        "param_name": "PARAM_TAKE_OR_PAY_RATE",
        "source": "monthly_resource_pool.no_discuss_percent",
        "index_sets": [
          "RESOURCE_IDS"
        ],
        "data_type": "float",
        "desc": "照付不议系数"
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
        "param_name": "PARAM_TRANSPORT_MIN",
        "source": "monthly_transport_pool.min_amount",
        "index_sets": [
          "TRANSPORT_IDS"
        ],
        "data_type": "float",
        "desc": "管输最小输气量"
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
      "desc": "路径上的天然气流量，索引为完整路径序列"
    },
    {
      "var_name": "VAR_TAKE_OR_PAY_SHORTFALL",
      "var_type": "continuous",
      "index_sets": [
        "RESOURCE_IDS"
      ],
      "lower_bound": 0,
      "desc": "照付不议惩罚基数：资源实际提取量低于最小提取量的差额"
    },
    {
      "var_name": "VAR_resource_surplus_slack",
      "var_type": "continuous",
      "index_sets": [
        "RESOURCE_IDS"
      ],
      "lower_bound": 0,
      "desc": "【场景1-上限松弛】资源硬边界上限过剩松弛变量，代表突破资源总量的规模，非负"
    },
    {
      "var_name": "VAR_transport_surplus_slack",
      "var_type": "continuous",
      "index_sets": [
        "TRANSPORT_IDS"
      ],
      "lower_bound": 0,
      "desc": "【场景1-上限松弛】管输运力硬边界上限过剩松弛变量，代表突破设计输气能力的规模，非负"
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
      "var_name": "VAR_transport_min_cover_slack",
      "var_type": "continuous",
      "index_sets": [
        "TRANSPORT_IDS"
      ],
      "lower_bound": 0,
      "desc": "【场景2-最小量兜底】管输运力最小量达标缺口松弛变量，代表未达最小输气量的缺口，非负"
    },
    {
      "var_name": "VAR_station_min_cover_slack",
      "var_type": "continuous",
      "index_sets": [
        "GATE_STATION_IDS"
      ],
      "lower_bound": 0,
      "desc": "【场景2-最小量兜底】门站业务下限达标缺口松弛变量，代表未达门站下限的缺口，非负"
    },
    {
      "var_name": "VAR_demand_min_cover_slack",
      "var_type": "continuous",
      "index_sets": [
        "DEMAND_IDS"
      ],
      "lower_bound": 0,
      "desc": "【场景2-最小量兜底】需求最小满足量达标缺口松弛变量，代表未达最小需求量的缺口，非负"
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
        "desc": "管输运力成本：路径经过的所有边的管输单价之和乘以流量"
      },
      {
        "term_name": "TERM_TAKE_OR_PAY_PENALTY",
        "expression": "sum(VAR_TAKE_OR_PAY_SHORTFALL[r] * PARAM_RESOURCE_PRICE[r] * PARAM_TAKE_OR_PAY_RATE[r] for r in RESOURCE_IDS)",
        "coefficient": -1,
        "desc": "照付不议惩罚成本：辅助变量乘以单价和系数"
      },
      {
        "term_name": "TERM_SLACK_PENALTY_RESOURCE",
        "expression": "sum(VAR_resource_surplus_slack[r] for r in RESOURCE_IDS)",
        "coefficient": -100,
        "desc": "【场景1-上限松弛】资源总量突破惩罚项"
      },
      {
        "term_name": "TERM_SLACK_PENALTY_TRANSPORT",
        "expression": "sum(VAR_transport_surplus_slack[t] for t in TRANSPORT_IDS)",
        "coefficient": -100,
        "desc": "【场景1-上限松弛】管输运力突破惩罚项"
      },
      {
        "term_name": "TERM_SLACK_PENALTY_STATION",
        "expression": "sum(VAR_station_surplus_slack[s] for s in GATE_STATION_IDS)",
        "coefficient": -100,
        "desc": "【场景1-上限松弛】门站上限突破惩罚项"
      },
      {
        "term_name": "TERM_SLACK_PENALTY_TRANSPORT_MIN",
        "expression": "sum(VAR_transport_min_cover_slack[t] for t in TRANSPORT_IDS)",
        "coefficient": -50,
        "desc": "【场景2-最小量兜底】管输最小输气量未达标惩罚项"
      },
      {
        "term_name": "TERM_SLACK_PENALTY_STATION_MIN",
        "expression": "sum(VAR_station_min_cover_slack[s] for s in GATE_STATION_IDS)",
        "coefficient": -50,
        "desc": "【场景2-最小量兜底】门站下限未达标惩罚项"
      },
      {
        "term_name": "TERM_SLACK_PENALTY_DEMAND_MIN",
        "expression": "sum(VAR_demand_min_cover_slack[d] for d in DEMAND_IDS)",
        "coefficient": -50,
        "desc": "【场景2-最小量兜底】需求最小满足量未达标惩罚项"
      }
    ],
    "desc": "最大化利润（销售收入 - 资源成本 - 运输成本 - 照付不议惩罚 - 松弛变量惩罚）"
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
      "desc": "【场景1-上限松弛】资源总量约束：从资源点r出发的流量不超过资源总量（允许突破，施加惩罚）"
    },
    {
      "constraint_id": "CONST_DEMAND_QTY",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[-1] == d)",
      "right_expression": "PARAM_DEMAND_QTY[d]",
      "index_sets": [
        "DEMAND_IDS"
      ],
      "priority": 1,
      "desc": "不可软化核心约束，禁止修改：需求量约束：到达需求点d的流量不超过计划需求量"
    },
    {
      "constraint_id": "CONST_TRANSPORT_CAP",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if t in p)",
      "right_expression": "PARAM_TRANSPORT_CAPACITY[t] + VAR_transport_surplus_slack[t]",
      "index_sets": [
        "TRANSPORT_IDS"
      ],
      "priority": 1,
      "desc": "【场景1-上限松弛】管输运力上限约束：经过运输边t的流量不超过设计能力（允许突破，施加惩罚）"
    },
    {
      "constraint_id": "CONST_TRANSPORT_MIN",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if t in p) + VAR_transport_min_cover_slack[t]",
      "right_expression": "PARAM_TRANSPORT_MIN[t]",
      "index_sets": [
        "TRANSPORT_IDS"
      ],
      "priority": 1,
      "desc": "【场景2-最小量兜底】管输运力下限约束：经过运输边t的流量不低于最小输气量（允许缺口，施加惩罚）"
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
      "desc": "【场景1-上限松弛】门站业务上限约束：经过门站s的流量不超过上限（允许突破，施加惩罚）"
    },
    {
      "constraint_id": "CONST_STATION_LOWER",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if s in p) + VAR_station_min_cover_slack[s]",
      "right_expression": "PARAM_STATION_LOWER[s]",
      "index_sets": [
        "GATE_STATION_IDS"
      ],
      "priority": 1,
      "desc": "【场景2-最小量兜底】门站业务下限约束：经过门站s的流量不低于下限（允许缺口，施加惩罚）"
    },
    {
      "constraint_id": "CONST_MIN_DEMAND",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[-1] == d) + VAR_demand_min_cover_slack[d]",
      "right_expression": "PARAM_MIN_DEMAND_QTY[d]",
      "index_sets": [
        "DEMAND_IDS"
      ],
      "priority": 2,
      "relaxable": true,
      "desc": "【场景2-最小量兜底】需求最小满足量约束：到达需求点d的流量不低于最小满足量（允许缺口，施加惩罚）"
    },
    {
      "constraint_id": "CONST_TAKE_OR_PAY_LINEARIZATION",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "VAR_TAKE_OR_PAY_SHORTFALL[r]",
      "right_expression": "PARAM_RESOURCE_MIN_QTY[r] - sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[0] == r)",
      "index_sets": [
        "RESOURCE_IDS"
      ],
      "priority": 1,
      "desc": "不可软化核心约束，禁止修改：照付不议线性化约束：辅助变量 >= 最小提取量 - 实际提取量"
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
        "name": "take_or_pay_penalty",
        "expression": "VAR_TAKE_OR_PAY_SHORTFALL[r] * PARAM_RESOURCE_PRICE[r] * PARAM_TAKE_OR_PAY_RATE[r]",
        "desc": "照付不议惩罚金额"
      }
    ],
    "output_format": "csv",
    "output_path": "./optimization_result"
  }
}
```