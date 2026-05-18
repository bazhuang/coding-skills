"""
优化模型构建器 - 城燃门站匹配利润优化

自动生成时间: 2026-01-30 19:00:00
"""

import pandas as pd
from pyomo.environ import (
    ConcreteModel, Var, Objective, Constraint,
    NonNegativeReals, Binary, maximize, minimize
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
    gate_df = tables["ontology_city_gas_station_info"]

    # 2. 构建集合和参数
    # 直接从表数据提取ID集合
    DEMAND_IDS = set(demand_df['demand_plan_code'])
    RESOURCE_IDS = set(resource_df['purchase_agreement_no'])
    TRANSPORT_IDS = set(transport_df['transport_code'])
    GATE_STATION_IDS = set(gate_df['gate_station_code'])

    # 构建参数字典
    PARAM_DEMAND_QUANTITY = dict(zip(demand_df['demand_plan_code'], demand_df['quantity']))
    PARAM_SELLING_PRICE = dict(zip(demand_df['demand_plan_code'], demand_df['unit_selling_price']))
    PARAM_MIN_SATISFY_QTY = dict(zip(demand_df['demand_plan_code'], demand_df['minimum_satisfy_quantity']))

    PARAM_RESOURCE_QUANTITY = dict(zip(resource_df['purchase_agreement_no'], resource_df['quantity']))
    PARAM_RESOURCE_MIN_QUANTITY = dict(zip(resource_df['purchase_agreement_no'], resource_df['min_quantity']))
    PARAM_RESOURCE_PRICE = dict(zip(resource_df['purchase_agreement_no'], resource_df['unit_price']))
    PARAM_TAKE_OR_PAY_PERCENT = dict(zip(resource_df['purchase_agreement_no'], resource_df['no_discuss_percent']))

    PARAM_TRANSPORT_CAPACITY = dict(zip(transport_df['transport_code'], transport_df['design_gas_capacity']))
    PARAM_TRANSPORT_PRICE = dict(zip(transport_df['transport_code'], transport_df['unit_price']))
    PARAM_TRANSPORT_MIN_AMOUNT = dict(zip(transport_df['transport_code'], transport_df['min_amount']))

    PARAM_GATE_UPPER_BOUND = dict(zip(gate_df['gate_station_code'], gate_df['upper_bound']))

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
        doc="资源未满足照付不议量的部分（辅助变量）"
    )

    model.VAR_USE_TRANSPORT = Var(
        TRANSPORT_IDS,
        domain=Binary,
        doc="运输边是否被使用（1=使用，0=不使用）"
    )

    model.VAR_resource_surplus_slack = Var(
        RESOURCE_IDS,
        domain=NonNegativeReals,
        doc="资源硬边界上限过剩松弛变量"
    )

    model.VAR_demand_surplus_slack = Var(
        DEMAND_IDS,
        domain=NonNegativeReals,
        doc="需求硬边界上限过剩松弛变量"
    )

    model.VAR_demand_min_cover_slack = Var(
        DEMAND_IDS,
        domain=NonNegativeReals,
        doc="需求最小量达标缺口松弛变量"
    )

    model.VAR_transport_surplus_slack = Var(
        TRANSPORT_IDS,
        domain=NonNegativeReals,
        doc="运力硬边界上限过剩松弛变量"
    )

    model.VAR_transport_min_cover_slack = Var(
        TRANSPORT_IDS,
        domain=NonNegativeReals,
        doc="运力最小量达标缺口松弛变量"
    )

    model.VAR_gate_surplus_slack = Var(
        GATE_STATION_IDS,
        domain=NonNegativeReals,
        doc="门站硬边界上限过剩松弛变量"
    )

    # 6. 定义目标函数
    def calculate_objective(m):
        # 销售收入
        term_sales_revenue = sum(
            m.VAR_PATH_FLOW[p] * PARAM_SELLING_PRICE[p[-1]]
            for p in FEASIBLE_PATHS
        )

        # 资源采购成本
        term_resource_cost = sum(
            m.VAR_PATH_FLOW[p] * PARAM_RESOURCE_PRICE[p[0]]
            for p in FEASIBLE_PATHS
        )

        # 管输运力成本
        term_transport_cost = sum(
            m.VAR_PATH_FLOW[p] * sum(
                PARAM_TRANSPORT_PRICE[e] for e in p if e in TRANSPORT_IDS
            )
            for p in FEASIBLE_PATHS
        )

        # 照付不议惩罚
        term_take_or_pay_penalty = sum(
            m.VAR_RESOURCE_SHORTAGE[r] * PARAM_RESOURCE_PRICE[r] * PARAM_TAKE_OR_PAY_PERCENT[r]
            for r in RESOURCE_IDS
        )

        # 各类松弛变量惩罚
        term_resource_surplus_penalty = -100 * sum(m.VAR_resource_surplus_slack[r] for r in RESOURCE_IDS)
        term_demand_surplus_penalty = -100 * sum(m.VAR_demand_surplus_slack[d] for d in DEMAND_IDS)
        term_demand_min_cover_penalty = -50 * sum(m.VAR_demand_min_cover_slack[d] for d in DEMAND_IDS)
        term_transport_surplus_penalty = -100 * sum(m.VAR_transport_surplus_slack[t] for t in TRANSPORT_IDS)
        term_transport_min_cover_penalty = -50 * sum(m.VAR_transport_min_cover_slack[t] for t in TRANSPORT_IDS)
        term_gate_surplus_penalty = -100 * sum(m.VAR_gate_surplus_slack[g] for g in GATE_STATION_IDS)

        return (
            term_sales_revenue
            - term_resource_cost
            - term_transport_cost
            - term_take_or_pay_penalty
            + term_resource_surplus_penalty
            + term_demand_surplus_penalty
            + term_demand_min_cover_penalty
            + term_transport_surplus_penalty
            + term_transport_min_cover_penalty
            + term_gate_surplus_penalty
        )

    model.objective = Objective(
        rule=calculate_objective,
        sense=maximize
    )

    # 7. 定义约束条件

    # 资源供应量上限约束
    def resource_supply_limit_rule(m, r):
        return sum(
            m.VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[0] == r
        ) <= PARAM_RESOURCE_QUANTITY[r] + m.VAR_resource_surplus_slack[r]

    model.CONST_RESOURCE_SUPPLY_LIMIT = Constraint(RESOURCE_IDS, rule=resource_supply_limit_rule)

    # 需求满足量上限约束
    def demand_limit_rule(m, d):
        return sum(
            m.VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[-1] == d
        ) <= PARAM_DEMAND_QUANTITY[d] + m.VAR_demand_surplus_slack[d]

    model.CONST_DEMAND_LIMIT = Constraint(DEMAND_IDS, rule=demand_limit_rule)

    # 需求最小满足量约束
    def demand_min_satisfy_rule(m, d):
        return sum(
            m.VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[-1] == d
        ) + m.VAR_demand_min_cover_slack[d] >= PARAM_MIN_SATISFY_QTY[d]

    model.CONST_DEMAND_MIN_SATISFY = Constraint(DEMAND_IDS, rule=demand_min_satisfy_rule)

    # 管输运力容量约束
    def transport_capacity_rule(m, t):
        return sum(
            m.VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if t in p
        ) <= PARAM_TRANSPORT_CAPACITY[t] + m.VAR_transport_surplus_slack[t]

    model.CONST_TRANSPORT_CAPACITY = Constraint(TRANSPORT_IDS, rule=transport_capacity_rule)

    # 运输使用逻辑约束
    def transport_usage_link_rule(m, t):
        return sum(
            m.VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if t in p
        ) <= PARAM_TRANSPORT_CAPACITY[t] * m.VAR_USE_TRANSPORT[t]

    model.CONST_TRANSPORT_USAGE_LINK = Constraint(TRANSPORT_IDS, rule=transport_usage_link_rule)

    # 管输最小量逻辑约束
    def transport_min_amount_logic_rule(m, t):
        return sum(
            m.VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if t in p
        ) + m.VAR_transport_min_cover_slack[t] >= PARAM_TRANSPORT_MIN_AMOUNT[t] * m.VAR_USE_TRANSPORT[t]

    model.CONST_TRANSPORT_MIN_AMOUNT_LOGIC = Constraint(TRANSPORT_IDS, rule=transport_min_amount_logic_rule)

    # 门站业务上限约束
    def gate_station_capacity_rule(m, g):
        return sum(
            m.VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if g in p
        ) <= PARAM_GATE_UPPER_BOUND[g] + m.VAR_gate_surplus_slack[g]

    model.CONST_GATE_STATION_CAPACITY = Constraint(GATE_STATION_IDS, rule=gate_station_capacity_rule)

    # 照付不议缺口定义约束
    def resource_shortage_def_rule(m, r):
        return m.VAR_RESOURCE_SHORTAGE[r] >= PARAM_RESOURCE_MIN_QUANTITY[r] - sum(
            m.VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[0] == r
        )

    model.CONST_RESOURCE_SHORTAGE_DEF = Constraint(RESOURCE_IDS, rule=resource_shortage_def_rule)

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
    solver.options['limits/time'] = 300  # 5分钟超时
    solver.options['limits/gap'] = 0.01  # 1% gap
    solver.options['threads'] = 4

    # 求解
    results = solver.solve(model, tee=True)

    # 将 model 附加到 results 对象，供 parse_result 使用
    results.model = model

    # 检查求解状态
    if results.solver.termination_condition == TerminationCondition.optimal:
        print("✓ 找到最优解")
    elif results.solver.termination_condition == TerminationCondition.feasible:
        print("✓ 找到可行解")
    else:
        print(f"✗ 求解失败: {results.solver.termination_condition}")

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

    # 获取运输ID集合
    tables = data["tables"]
    transport_df = tables["monthly_transport_pool"]
    TRANSPORT_IDS_SET = set(transport_df['transport_code'])

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
                # 判断索引维度
                first_key = list(var_component.keys())[0]
                if isinstance(first_key, tuple):
                    # 多维索引
                    index_cols = [f"index_{i}" for i in range(len(var_data[0]) - 1)]
                    columns = index_cols + ["value"]
                else:
                    # 单维索引
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

    # 提取运输使用状态
    transport_usage = {}
    if hasattr(model, 'VAR_USE_TRANSPORT'):
        for t in model.VAR_USE_TRANSPORT:
            val = model.VAR_USE_TRANSPORT[t].value
            if val is not None:
                transport_usage[t] = int(round(val))

    # 提取资源缺口
    resource_shortage = {}
    if hasattr(model, 'VAR_RESOURCE_SHORTAGE'):
        for r in model.VAR_RESOURCE_SHORTAGE:
            val = model.VAR_RESOURCE_SHORTAGE[r].value
            if val is not None and val > 0.001:
                resource_shortage[r] = round(val, 2)

    # 计算总利润
    total_profit = model.objective()

    # 构建结果
    result = {
        "status": "success",
        "objective_value": round(total_profit, 2),
        "path_flows": path_flows,
        "transport_usage": transport_usage,
        "resource_shortage": resource_shortage,
        "num_active_paths": len(path_flows),
        "solver_time": results.solver.time,
        "termination_condition": str(results.solver.termination_condition),
        "excel_output": excel_path
    }

    return result