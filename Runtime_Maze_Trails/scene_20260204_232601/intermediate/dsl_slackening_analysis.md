# DSL硬约束松弛优化分析报告

## LLM完整响应

# DSL约束软化方案

## 1. 可软化约束识别
根据DSL中的约束定义及业务场景，识别出以下可软化约束：
- **资源供应上限约束 (CONST_RESOURCE_SUPPLY_LIMIT)**：硬边界上限，易因资源总量不足导致无解，需软化。
- **管输运力上限约束 (CONST_TRANSPORT_CAP_LIMIT)**：硬边界上限，易因管网拥堵导致无解，需软化。
- **门站业务上限约束 (CONST_STATION_CAP_LIMIT)**：硬边界上限，易因节点承载不足导致无解，需软化。
- **门站业务下限约束 (CONST_STATION_MIN_LIMIT)**：硬边界下限（非最小量类），易因流量不足导致无解，需软化。
- **管输最小量约束 (CONST_TRANSPORT_MIN_LIMIT)**：最小量达标约束，需兜底松弛以提升达标率。
- **需求最小满足量约束 (CONST_DEMAND_MIN_SATISFY)**：最小量达标约束，需兜底松弛以提升达标率。

**不可软化约束**：
- 需求满足量上限 (CONST_DEMAND_SATISFY_LIMIT)：物理接收能力限制，不可突破。
- 照付不议缺口定义 (CONST_TOP_GAP_DEF)：变量定义类约束，不可修改。

## 2. 松弛变量设计
根据场景分类，设计以下松弛变量：

**场景1：硬边界约束松弛（惩罚系数 100）**
1. **资源供应上限过剩松弛**：`VAR_resource_surplus_slack`，索引集 `RESOURCE_CODES`。
2. **管输运力上限过剩松弛**：`VAR_transport_surplus_slack`，索引集 `TRANSPORT_IDS`。
3. **门站业务上限过剩松弛**：`VAR_station_surplus_slack`，索引集 `GATE_STATION_CODES`。
4. **门站业务下限不足松弛**：`VAR_station_slack`，索引集 `GATE_STATION_CODES`。

**场景2：最小量达标兜底松弛（惩罚系数 50）**
1. **管输最小量缺口松弛**：`VAR_transport_min_cover_slack`，索引集 `TRANSPORT_IDS`。
2. **需求最小满足量缺口松弛**：`VAR_demand_min_cover_slack`，索引集 `DEMAND_CODES`。

## 3. 约束软化实施
- **上限约束软化**：将 `实际量 ≤ 边界` 修改为 `实际量 ≤ 边界 + surplus_slack`。
- **下限约束软化**：将 `实际量 ≥ 边界` 修改为 `实际量 + slack ≥ 边界`。
- **最小量约束软化**：将 `实际量 ≥ 最小量` 修改为 `实际量 + min_cover_slack ≥ 最小量`。
- **目标函数调整**：在最大化利润目标中，减去所有松弛变量的惩罚成本（`sum(松弛变量 * 惩罚系数)`）。

## 4. 设计说明总结
本方案针对天然气资源流动优化模型，新增6类松弛变量以解决潜在无解问题并提升达标率。其中4类硬边界松弛（系数100）用于应对资源、运力及门站承载的极端冲突，2类最小量兜底松弛（系数50）用于保障管输和需求的基本满足。修改了6个核心业务约束，严格保留了照付不议定义及物理上限等不可软化约束，确保模型在获得更高可解性的同时，核心业务逻辑与优化目标保持不变。

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
    },
    {
      "var_name": "VAR_resource_surplus_slack",
      "var_type": "continuous",
      "index_sets": [
        "RESOURCE_CODES"
      ],
      "lower_bound": 0,
      "desc": "【场景1-上限松弛】资源供应硬边界上限过剩松弛变量，代表突破供应边界的规模，非负"
    },
    {
      "var_name": "VAR_transport_surplus_slack",
      "var_type": "continuous",
      "index_sets": [
        "TRANSPORT_IDS"
      ],
      "lower_bound": 0,
      "desc": "【场景1-上限松弛】管输运力硬边界上限过剩松弛变量，代表突破运力边界的规模，非负"
    },
    {
      "var_name": "VAR_station_surplus_slack",
      "var_type": "continuous",
      "index_sets": [
        "GATE_STATION_CODES"
      ],
      "lower_bound": 0,
      "desc": "【场景1-上限松弛】门站业务硬边界上限过剩松弛变量，代表突破门站承载边界的规模，非负"
    },
    {
      "var_name": "VAR_station_slack",
      "var_type": "continuous",
      "index_sets": [
        "GATE_STATION_CODES"
      ],
      "lower_bound": 0,
      "desc": "【场景1-下限松弛】门站业务硬边界下限不足松弛变量，代表未达门站业务下限的缺口，非负"
    },
    {
      "var_name": "VAR_transport_min_cover_slack",
      "var_type": "continuous",
      "index_sets": [
        "TRANSPORT_IDS"
      ],
      "lower_bound": 0,
      "desc": "【场景2-最小量兜底】管输最小量达标缺口松弛变量，代表未达最小运输量的缺口，非负；达标时取值为0"
    },
    {
      "var_name": "VAR_demand_min_cover_slack",
      "var_type": "continuous",
      "index_sets": [
        "DEMAND_CODES"
      ],
      "lower_bound": 0,
      "desc": "【场景2-最小量兜底】需求最小量达标缺口松弛变量，代表未达最小满足量的缺口，非负；达标时取值为0"
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
      },
      {
        "term_name": "TERM_RESOURCE_SURPLUS_PENALTY",
        "expression": "sum(VAR_resource_surplus_slack[r] for r in RESOURCE_CODES)",
        "coefficient": -100,
        "desc": "【场景1-上限松弛】资源供应上限突破惩罚"
      },
      {
        "term_name": "TERM_TRANSPORT_SURPLUS_PENALTY",
        "expression": "sum(VAR_transport_surplus_slack[t] for t in TRANSPORT_IDS)",
        "coefficient": -100,
        "desc": "【场景1-上限松弛】管输运力上限突破惩罚"
      },
      {
        "term_name": "TERM_STATION_SURPLUS_PENALTY",
        "expression": "sum(VAR_station_surplus_slack[s] for s in GATE_STATION_CODES)",
        "coefficient": -100,
        "desc": "【场景1-上限松弛】门站业务上限突破惩罚"
      },
      {
        "term_name": "TERM_STATION_SHORTAGE_PENALTY",
        "expression": "sum(VAR_station_slack[s] for s in GATE_STATION_CODES)",
        "coefficient": -100,
        "desc": "【场景1-下限松弛】门站业务下限未达惩罚"
      },
      {
        "term_name": "TERM_TRANSPORT_MIN_COVER_PENALTY",
        "expression": "sum(VAR_transport_min_cover_slack[t] for t in TRANSPORT_IDS)",
        "coefficient": -50,
        "desc": "【场景2-最小量兜底】管输最小量未达标惩罚"
      },
      {
        "term_name": "TERM_DEMAND_MIN_COVER_PENALTY",
        "expression": "sum(VAR_demand_min_cover_slack[d] for d in DEMAND_CODES)",
        "coefficient": -50,
        "desc": "【场景2-最小量兜底】需求最小满足量未达标惩罚"
      }
    ],
    "desc": "最大化总利润（销售收入 - 各项成本 - 各类松弛惩罚）"
  },
  "constraints": [
    {
      "constraint_id": "CONST_RESOURCE_SUPPLY_LIMIT",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[0] == r)",
      "right_expression": "PARAM_RESOURCE_QTY[r] + VAR_resource_surplus_slack[r]",
      "index_sets": [
        "RESOURCE_CODES"
      ],
      "priority": 1,
      "desc": "【场景1-上限松弛】资源供应量上限约束：从每个资源提取的总量不能超过该资源的最大供应量（允许通过过剩松弛变量突破）"
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
      "desc": "不可软化核心约束，禁止修改：需求满足量上限约束：供应给每个需求的总量不能超过该需求的最大需求量"
    },
    {
      "constraint_id": "CONST_TRANSPORT_CAP_LIMIT",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if t in p)",
      "right_expression": "PARAM_TRANSPORT_CAP[t] + VAR_transport_surplus_slack[t]",
      "index_sets": [
        "TRANSPORT_IDS"
      ],
      "priority": 1,
      "desc": "【场景1-上限松弛】管输运力上限约束：每条运输路径上的流量不能超过该管段的设计输气能力（允许通过过剩松弛变量突破）"
    },
    {
      "constraint_id": "CONST_STATION_CAP_LIMIT",
      "constraint_type": "inequality",
      "direction": "<=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if s in p)",
      "right_expression": "PARAM_STATION_UPPER[s] + VAR_station_surplus_slack[s]",
      "index_sets": [
        "GATE_STATION_CODES"
      ],
      "priority": 1,
      "desc": "【场景1-上限松弛】门站业务上限约束：经过门站的流量不能超过门站业务上限（允许通过过剩松弛变量突破）"
    },
    {
      "constraint_id": "CONST_STATION_MIN_LIMIT",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if s in p) + VAR_station_slack[s]",
      "right_expression": "PARAM_STATION_LOWER[s]",
      "index_sets": [
        "GATE_STATION_CODES"
      ],
      "priority": 1,
      "desc": "【场景1-下限松弛】门站业务下限约束：经过门站的流量不能低于门站业务下限（允许通过不足松弛变量未达）"
    },
    {
      "constraint_id": "CONST_TRANSPORT_MIN_LIMIT",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if t in p) + VAR_transport_min_cover_slack[t]",
      "right_expression": "PARAM_TRANSPORT_MIN[t]",
      "index_sets": [
        "TRANSPORT_IDS"
      ],
      "priority": 2,
      "relaxable": true,
      "desc": "【场景2-最小量兜底】管输最小量约束：使用管输运力时，运输量需满足最小运输量要求（允许通过缺口松弛变量未达）"
    },
    {
      "constraint_id": "CONST_DEMAND_MIN_SATISFY",
      "constraint_type": "inequality",
      "direction": ">=",
      "left_expression": "sum(VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[-1] == d) + VAR_demand_min_cover_slack[d]",
      "right_expression": "PARAM_MIN_SATISFY_QTY[d]",
      "index_sets": [
        "DEMAND_CODES"
      ],
      "priority": 2,
      "relaxable": true,
      "desc": "【场景2-最小量兜底】需求最小满足量约束：供应给每个需求的总量应尽量满足最小满足量要求（允许通过缺口松弛变量未达）"
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
      "desc": "不可软化核心约束，禁止修改：照付不议缺口定义约束：实际提取量 + 缺口变量 >= 最小提取量。结合目标函数最小化惩罚，等价于 Gap = max(0, Min - Actual)"
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