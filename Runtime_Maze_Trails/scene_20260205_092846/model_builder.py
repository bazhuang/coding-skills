"""
优化模型构建器 - 天然气供需匹配优化

自动生成时间: 2023-10-27 10:00:00
"""

import pandas as pd
import os
from pyomo.environ import (
    ConcreteModel, Var, Objective, Constraint,
    NonNegativeReals, maximize
)
from pyomo.opt import SolverFactory, TerminationCondition


def build_model(data):
    """构建天然气供需匹配优化模型

    Args:
        data: 包含所有数据的字典
            - 表数据: data["tables"]["table_name"] (pd.DataFrame)
            - 路径数据: data["paths"] (List[List[str]])

    Returns:
        Pyomo ConcreteModel 实例
    """
    # 1. 提取表数据
    tables = data["tables"]
    
    # 需求表
    demand_df = tables["monthly_demand_pool"]
    # 资源表
    resource_df = tables["monthly_resource_pool"]
    # 运输表
    transport_df = tables["monthly_transport_pool"]
    # 门站表
    station_df = tables["ontology_city_gas_station_info"]

    # 2. 构建集合和参数
    # 集合
    DEMAND_NODES = set(demand_df['demand_plan_code'].tolist())
    RESOURCE_NODES = set(resource_df['purchase_agreement_no'].tolist())
    TRANSPORT_EDGES = set(transport_df['id'].tolist())
    GATE_STATIONS = set(station_df['gate_station_code'].tolist())

    # 参数：需求
    PARAM_DEMAND_QTY = dict(zip(demand_df['demand_plan_code'], demand_df['quantity']))
    PARAM_SELLING_PRICE = dict(zip(demand_df['demand_plan_code'], demand_df['unit_selling_price']))
    PARAM_MIN_DEMAND_QTY = dict(zip(demand_df['demand_plan_code'], demand_df['minimum_satisfy_quantity']))

    # 参数：资源
    PARAM_RESOURCE_CAPACITY = dict(zip(resource_df['purchase_agreement_no'], resource_df['quantity']))
    PARAM_RESOURCE_MIN_QTY = dict(zip(resource_df['purchase_agreement_no'], resource_df['min_quantity']))
    PARAM_RESOURCE_PRICE = dict(zip(resource_df['purchase_agreement_no'], resource_df['unit_price']))
    PARAM_NOP_PERCENT = dict(zip(resource_df['purchase_agreement_no'], resource_df['no_discuss_percent']))

    # 参数：运输
    PARAM_TRANSPORT_CAPACITY = dict(zip(transport_df['id'], transport_df['design_gas_capacity']))
    PARAM_TRANSPORT_PRICE = dict(zip(transport_df['id'], transport_df['unit_price']))
    PARAM_TRANSPORT_MIN_AMOUNT = dict(zip(transport_df['id'], transport_df['min_amount']))

    # 参数：门站
    PARAM_STATION_UPPER = dict(zip(station_df['gate_station_code'], station_df['upper_bound']))
    PARAM_STATION_LOWER = dict(zip(station_df['gate_station_code'], station_df['lower_bound']))

    # 3. 提取路径数据
    paths = data["paths"]
    # 将路径列表转换为元组，用作 Pyomo 变量索引
    FEASIBLE_PATHS = [tuple(path) for path in paths]

    # 4. 创建 Pyomo 模型
    model = ConcreteModel(name="gas_matching_optimization")

    # 5. 定义决策变量
    model.VAR_PATH_FLOW = Var(
        FEASIBLE_PATHS,
        domain=NonNegativeReals,
        doc="路径上的天然气流量"
    )

    model.VAR_SHORTFALL = Var(
        RESOURCE_NODES,
        domain=NonNegativeReals,
        doc="照付不议未满足量"
    )

    model.VAR_resource_surplus_slack = Var(
        RESOURCE_NODES,
        domain=NonNegativeReals,
        doc="资源硬边界上限过剩松弛变量"
    )

    model.VAR_demand_surplus_slack = Var(
        DEMAND_NODES,
        domain=NonNegativeReals,
        doc="需求硬边界上限过剩松弛变量"
    )

    model.VAR_transport_surplus_slack = Var(
        TRANSPORT_EDGES,
        domain=NonNegativeReals,
        doc="运力硬边界上限过剩松弛变量"
    )

    model.VAR_station_surplus_slack = Var(
        GATE_STATIONS,
        domain=NonNegativeReals,
        doc="门站硬边界上限过剩松弛变量"
    )

    model.VAR_station_slack = Var(
        GATE_STATIONS,
        domain=NonNegativeReals,
        doc="门站硬边界下限不足松弛变量"
    )

    model.VAR_transport_min_cover_slack = Var(
        TRANSPORT_EDGES,
        domain=NonNegativeReals,
        doc="运输最小量达标缺口松弛变量"
    )

    model.VAR_demand_min_cover_slack = Var(
        DEMAND_NODES,
        domain=NonNegativeReals,
        doc="需求最小量达标缺口松弛变量"
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

        # 运输成本
        term_transport_cost = sum(
            m.VAR_PATH_FLOW[p] * sum(
                PARAM_TRANSPORT_PRICE[e]
                for e in p
                if e in TRANSPORT_EDGES
            )
            for p in FEASIBLE_PATHS
        )

        # 照付不议惩罚成本
        term_take_or_pay_penalty = sum(
            m.VAR_SHORTFALL[r] * PARAM_RESOURCE_PRICE[r] * PARAM_NOP_PERCENT[r]
            for r in RESOURCE_NODES
        )

        # 松弛变量惩罚成本
        term_slack_penalty = (
            sum(m.VAR_resource_surplus_slack[r] * 100 for r in RESOURCE_NODES) +
            sum(m.VAR_demand_surplus_slack[d] * 100 for d in DEMAND_NODES) +
            sum(m.VAR_transport_surplus_slack[e] * 100 for e in TRANSPORT_EDGES) +
            sum(m.VAR_station_surplus_slack[s] * 100 for s in GATE_STATIONS) +
            sum(m.VAR_station_slack[s] * 100 for s in GATE_STATIONS) +
            sum(m.VAR_transport_min_cover_slack[e] * 50 for e in TRANSPORT_EDGES) +
            sum(m.VAR_demand_min_cover_slack[d] * 50 for d in DEMAND_NODES)
        )

        return term_sales_revenue - term_resource_cost - term_transport_cost - term_take_or_pay_penalty - term_slack_penalty

    model.objective = Objective(
        rule=calculate_objective,
        sense=maximize
    )

    # 7. 定义约束条件

    # 资源供应量上限约束
    def resource_capacity_rule(m, r):
        return sum(
            m.VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[0] == r
        ) <= PARAM_RESOURCE_CAPACITY[r] + m.VAR_resource_surplus_slack[r]

    model.CONST_RESOURCE_CAPACITY = Constraint(RESOURCE_NODES, rule=resource_capacity_rule)

    # 需求满足量上限约束
    def demand_limit_rule(m, d):
        return sum(
            m.VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[-1] == d
        ) <= PARAM_DEMAND_QTY[d] + m.VAR_demand_surplus_slack[d]

    model.CONST_DEMAND_LIMIT = Constraint(DEMAND_NODES, rule=demand_limit_rule)

    # 管输运力能力上限约束
    def transport_capacity_rule(m, e):
        return sum(
            m.VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if e in p
        ) <= PARAM_TRANSPORT_CAPACITY[e] + m.VAR_transport_surplus_slack[e]

    model.CONST_TRANSPORT_CAPACITY = Constraint(TRANSPORT_EDGES, rule=transport_capacity_rule)

    # 门站业务上限约束
    def station_capacity_rule(m, s):
        return sum(
            m.VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if s in p
        ) <= PARAM_STATION_UPPER[s] + m.VAR_station_surplus_slack[s]

    model.CONST_STATION_CAPACITY = Constraint(GATE_STATIONS, rule=station_capacity_rule)

    # 门站业务下限约束
    def station_min_flow_rule(m, s):
        return sum(
            m.VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if s in p
        ) + m.VAR_station_slack[s] >= PARAM_STATION_LOWER[s]

    model.CONST_STATION_MIN_FLOW = Constraint(GATE_STATIONS, rule=station_min_flow_rule)

    # 运输最小量约束
    def transport_min_amount_rule(m, e):
        return sum(
            m.VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if e in p
        ) + m.VAR_transport_min_cover_slack[e] >= PARAM_TRANSPORT_MIN_AMOUNT[e]

    model.CONST_TRANSPORT_MIN_AMOUNT = Constraint(TRANSPORT_EDGES, rule=transport_min_amount_rule)

    # 需求最小满足量约束
    def demand_min_satisfy_rule(m, d):
        return sum(
            m.VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[-1] == d
        ) + m.VAR_demand_min_cover_slack[d] >= PARAM_MIN_DEMAND_QTY[d]

    model.CONST_DEMAND_MIN_SATISFY = Constraint(DEMAND_NODES, rule=demand_min_satisfy_rule)

    # 照付不议未满足量定义约束
    def shortfall_def_rule(m, r):
        return m.VAR_SHORTFALL[r] >= PARAM_RESOURCE_MIN_QTY[r] - sum(
            m.VAR_PATH_FLOW[p] for p in FEASIBLE_PATHS if p[0] == r
        )

    model.CONST_SHORTFALL_DEF = Constraint(RESOURCE_NODES, rule=shortfall_def_rule)

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

    # 计算总利润
    total_profit = model.objective()

    # 构建结果
    result = {
        "status": "success",
        "objective_value": round(total_profit, 2),
        "path_flows": path_flows,
        "num_active_paths": len(path_flows),
        "solver_time": results.solver.time,
        "termination_condition": str(results.solver.termination_condition),
        "excel_output": excel_path
    }

    return result