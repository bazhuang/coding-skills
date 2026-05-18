"""
优化模型构建器 - 城燃门站匹配利润优化

自动生成时间: 2026-01-30 19:00:00
"""

import pandas as pd
from pyomo.environ import (
    ConcreteModel, Var, Objective, Constraint,
    NonNegativeReals, maximize
)
from pyomo.opt import SolverFactory, TerminationCondition


def build_model(data):
    """构建优化模型

    Args:
        data: 包含所有数据的字典
            - 表数据: data["tables"]["table_name"] (pd.DataFrame)
            - 路径数据: data["paths"] (List[List[str]])

    Returns:
        Pyomo ConcreteModel 实例
    """
    # 1. 提取表数据
    tables = data["tables"]
    
    # 根据DSL中的table_name提取数据
    demand_df = tables["monthly_demand_pool"]
    resource_df = tables["monthly_resource_pool"]
    transport_df = tables["monthly_transport_pool"]
    station_df = tables["ontology_city_gas_station_info"]

    # 2. 构建集合和参数
    # 直接从表数据提取ID集合
    DEMAND_IDS = set(demand_df['demand_plan_code'])
    RESOURCE_IDS = set(resource_df['purchase_agreement_no'])
    TRANSPORT_IDS = set(transport_df['id'])
    GATE_STATION_IDS = set(station_df['gate_station_code'])

    # 构建参数字典
    PARAM_DEMAND_QTY = dict(zip(demand_df['demand_plan_code'], demand_df['quantity']))
    PARAM_SELLING_PRICE = dict(zip(demand_df['demand_plan_code'], demand_df['unit_selling_price']))
    PARAM_MIN_DEMAND_QTY = dict(zip(demand_df['demand_plan_code'], demand_df['minimum_satisfy_quantity']))

    PARAM_RESOURCE_CAPACITY = dict(zip(resource_df['purchase_agreement_no'], resource_df['quantity']))
    PARAM_RESOURCE_MIN_QTY = dict(zip(resource_df['purchase_agreement_no'], resource_df['min_quantity']))
    PARAM_RESOURCE_PRICE = dict(zip(resource_df['purchase_agreement_no'], resource_df['unit_price']))
    PARAM_TOP_COEFF = dict(zip(resource_df['purchase_agreement_no'], resource_df['no_discuss_percent']))

    PARAM_TRANSPORT_CAPACITY = dict(zip(transport_df['id'], transport_df['design_gas_capacity']))
    PARAM_TRANSPORT_PRICE = dict(zip(transport_df['id'], transport_df['unit_price']))
    PARAM_TRANSPORT_MIN = dict(zip(transport_df['id'], transport_df['min_amount']))

    PARAM_STATION_UPPER = dict(zip(station_df['gate_station_code'], station_df['upper_bound']))
    PARAM_STATION_LOWER = dict(zip(station_df['gate_station_code'], station_df['lower_bound']))

    # 3. 提取路径数据
    paths = data["paths"]
    # 将路径列表转换为元组，用作 Pyomo 变量索引
    FEASIBLE_PATHS = [tuple(path) for path in paths]

    # 4. 创建 Pyomo 模型
    model = ConcreteModel(name="gas_city_gate_matching_profit")

    # 5. 定义决策变量
    model.VAR_PATH_FLOW = Var(
        FEASIBLE_PATHS,
        domain=NonNegativeReals,
        doc="路径上的天然气流量"
    )

    model.VAR_RESOURCE_SHORTAGE = Var(
        RESOURCE_IDS,
        domain=NonNegativeReals,
        doc="资源未满足最小提取量的部分"
    )

    model.VAR_resource_surplus_slack = Var(
        RESOURCE_IDS,
        domain=NonNegativeReals,
        doc="资源硬边界上限过剩松弛变量"
    )

    model.VAR_transport_surplus_slack = Var(
        TRANSPORT_IDS,
        domain=NonNegativeReals,
        doc="运力硬边界上限过剩松弛变量"
    )

    model.VAR_station_surplus_slack = Var(
        GATE_STATION_IDS,
        domain=NonNegativeReals,
        doc="门站硬边界上限过剩松弛变量"
    )

    model.VAR_station_slack = Var(
        GATE_STATION_IDS,
        domain=NonNegativeReals,
        doc="门站硬边界下限不足松弛变量"
    )

    model.VAR_demand_min_cover_slack = Var(
        DEMAND_IDS,
        domain=NonNegativeReals,
        doc="需求最小量达标缺口松弛变量"
    )

    # 6. 定义目标函数
    def calculate_objective(m):
        # TERM_SALES_REVENUE: sum(VAR_PATH_FLOW[p] * PARAM_SELLING_PRICE[p[-1]])
        term_sales_revenue = sum(
            m.VAR_PATH_FLOW[p] * PARAM_SELLING_PRICE[p[-1]]
            for p in FEASIBLE_PATHS
        )

        # TERM_RESOURCE_COST: sum(VAR_PATH_FLOW[p] * PARAM_RESOURCE_PRICE[p[0]])
        term_resource_cost = sum(
            m.VAR_PATH_FLOW[p] * PARAM_RESOURCE_PRICE[p[0]]
            for p in FEASIBLE_PATHS
        )

        # TERM_TRANSPORT_COST: sum(VAR_PATH_FLOW[p] * sum(PARAM_TRANSPORT_PRICE[e] for e in p if e in TRANSPORT_IDS))
        term_transport_cost = sum(
            m.VAR_PATH_FLOW[p] * sum(
                PARAM_TRANSPORT_PRICE[e] for e in p if e in TRANSPORT_IDS
            )
            for p in FEASIBLE_PATHS
        )

        # TERM_TAKE_OR_PAY_PENALTY: sum(VAR_RESOURCE_SHORTAGE[r] * PARAM_RESOURCE_PRICE[r] * PARAM_TOP_COEFF[r])
        term_top_penalty = sum(
            m.VAR_RESOURCE_SHORTAGE[r] * PARAM_RESOURCE_PRICE[r] * PARAM_TOP_COEFF[r]
            for r in RESOURCE_IDS
        )

        # TERM_SLACK_PENALTY
        term_slack_penalty = (
            sum(m.VAR_resource_surplus_slack[r] * 100 for r in RESOURCE_IDS) +
            sum(m.VAR_transport_surplus_slack[t] * 100 for t in TRANSPORT_IDS) +
            sum(m.VAR_station_surplus_slack[s] * 100 for s in GATE_STATION_IDS) +
            sum(m.VAR_station_slack[s] * 100 for s in GATE_STATION_IDS) +
            sum(m.VAR_demand_min_cover_slack[d] * 50 for d in DEMAND_IDS)
        )

        # 最大化总利润
        return term_sales_revenue - term_resource_cost - term_transport_cost - term_top_penalty - term_slack_penalty

    model.objective = Objective(
        rule=calculate_objective,
        sense=maximize
    )

    # 7. 定义约束条件

    # CONST_RESOURCE_CAPACITY
    def resource_capacity_rule(m, r):
        return sum(
            m.VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[0] == r
        ) <= PARAM_RESOURCE_CAPACITY[r] + m.VAR_resource_surplus_slack[r]

    model.CONST_RESOURCE_CAPACITY = Constraint(RESOURCE_IDS, rule=resource_capacity_rule)

    # CONST_DEMAND_LIMIT
    def demand_limit_rule(m, d):
        return sum(
            m.VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[-1] == d
        ) + m.VAR_demand_min_cover_slack[d] >= PARAM_DEMAND_QTY[d]

    model.CONST_DEMAND_LIMIT = Constraint(DEMAND_IDS, rule=demand_limit_rule)

    # CONST_TRANSPORT_CAPACITY
    def transport_capacity_rule(m, t):
        return sum(
            m.VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if t in p
        ) <= PARAM_TRANSPORT_CAPACITY[t] + m.VAR_transport_surplus_slack[t]

    model.CONST_TRANSPORT_CAPACITY = Constraint(TRANSPORT_IDS, rule=transport_capacity_rule)

    # CONST_STATION_UPPER
    def station_upper_rule(m, s):
        return sum(
            m.VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if s in p
        ) <= PARAM_STATION_UPPER[s] + m.VAR_station_surplus_slack[s]

    model.CONST_STATION_UPPER = Constraint(GATE_STATION_IDS, rule=station_upper_rule)

    # CONST_STATION_LOWER
    def station_lower_rule(m, s):
        return sum(
            m.VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if s in p
        ) + m.VAR_station_slack[s] >= PARAM_STATION_LOWER[s]

    model.CONST_STATION_LOWER = Constraint(GATE_STATION_IDS, rule=station_lower_rule)

    # CONST_TOP_SHORTAGE_DEF
    def top_shortage_def_rule(m, r):
        return m.VAR_RESOURCE_SHORTAGE[r] >= PARAM_RESOURCE_MIN_QTY[r] - sum(
            m.VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[0] == r
        )

    model.CONST_TOP_SHORTAGE_DEF = Constraint(RESOURCE_IDS, rule=top_shortage_def_rule)

    # CONST_TOP_SHORTAGE_UPPER
    def top_shortage_upper_rule(m, r):
        return m.VAR_RESOURCE_SHORTAGE[r] <= PARAM_RESOURCE_MIN_QTY[r]

    model.CONST_TOP_SHORTAGE_UPPER = Constraint(RESOURCE_IDS, rule=top_shortage_upper_rule)

    return model


def solve_model(model):
    """求解优化模型

    Args:
        model: Pyomo ConcreteModel 实例

    Returns:
        求解结果对象
    """
    # 创建求解器
    solver = SolverFactory('scip')

    # 配置求解器参数
    solver.options['limits/time'] = 300
    solver.options['limits/gap'] = 0.01
    solver.options['lp/emphasis'] = 'optimal'
    solver.options['threads'] = 4

    # 求解
    results = solver.solve(model, tee=True)

    # 将 model 附加到 results 对象，供 parse_result 使用
    results.model = model

    # 检查求解状态
    if results.solver.termination_condition == TerminationCondition.optimal:
        print("找到最优解")
    elif results.solver.termination_condition == TerminationCondition.feasible:
        print("找到可行解")
    else:
        print(f"求解失败: {results.solver.termination_condition}")

    return results


def parse_result(results, data, output_dir):
    """解析求解结果并输出到Excel

    Args:
        results: 求解结果对象
        data: 原始数据字典
        output_dir: 输出目录路径

    Returns:
        结果字典
    """
    import os

    # 检查求解状态
    if results.solver.termination_condition not in [
        TerminationCondition.optimal,
        TerminationCondition.feasible
    ]:
        return {
            "status": "failed",
            "message": str(results.solver.termination_condition)
        }

    # 从 results 中获取 model 引用
    model = results.model

    # 提取路径数据
    paths = data["paths"]
    feasible_paths = [tuple(path) for path in paths]

    # 获取运输ID集合（用于筛选边）
    tables = data["tables"]
    transport_df = tables["monthly_transport_pool"]
    TRANSPORT_IDS_SET = set(transport_df['id'].tolist())

    # 创建Excel writer
    excel_path = os.path.join(output_dir, "decision_variables.xlsx")
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:

        # 1. 输出所有决策变量到不同的sheet
        for var_name in model.component_map(Var):
            var_component = model.component(var_name)

            # 提取变量值（输出所有变量，不做任何过滤）
            var_data = []
            for index in var_component:
                var_value = var_component[index].value
                # 根据索引类型构建行数据
                if isinstance(index, tuple):
                    # 多维索引：展开为多列
                    row = list(index) + [var_value]
                else:
                    # 单维索引
                    row = [index, var_value]
                var_data.append(row)

            # 转换为DataFrame
            if var_data:
                # 判断索引列数
                first_index = list(var_component.keys())[0]
                if isinstance(first_index, tuple):
                    index_cols = [f"index_{i}" for i in range(len(first_index))]
                    columns = index_cols + ["value"]
                else:
                    columns = ["index", "value"]

                df = pd.DataFrame(var_data, columns=columns)
                # 写入Excel sheet
                df.to_excel(writer, sheet_name=var_name, index=False)

        # 2. 输出目标函数值
        objective_value = model.objective()
        objective_df = pd.DataFrame({
            "objective_name": ["objective"],
            "value": [objective_value]
        })
        objective_df.to_excel(writer, sheet_name="Objective", index=False)

    # 提取决策变量的值（用于返回结果字典）
    path_flows = []
    for path_seq in feasible_paths:
        flow_value = model.VAR_PATH_FLOW[path_seq].value
        if flow_value and flow_value > 0.001:  # 过滤掉接近0的值
            # 提取节点和边
            path_nodes = [path_seq[0], path_seq[-1]]  # 资源和需求节点
            path_edges = [e for e in path_seq if e in TRANSPORT_IDS_SET]  # 边
            path_flows.append({
                "resource_id": path_seq[0],
                "demand_id": path_seq[-1],
                "flow": round(flow_value, 2),
                "path_nodes": path_nodes,
                "path_edges": path_edges
            })

    # 提取资源缺口
    resource_shortages = []
    for r in model.VAR_RESOURCE_SHORTAGE:
        val = model.VAR_RESOURCE_SHORTAGE[r].value
        if val and val > 0.001:
            resource_shortages.append({
                "resource_id": r,
                "shortage": round(val, 2)
            })

    # 计算总利润
    total_profit = model.objective()

    # 构建结果
    result = {
        "status": "success",
        "objective_value": round(total_profit, 2),
        "path_flows": path_flows,
        "resource_shortages": resource_shortages,
        "num_active_paths": len(path_flows),
        "solver_time": results.solver.time,
        "termination_condition": str(results.solver.termination_condition),
        "excel_output": excel_path
    }

    return result