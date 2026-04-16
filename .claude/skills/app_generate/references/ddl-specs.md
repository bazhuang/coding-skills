# MySQL DDL 生成规范与模板

## 命名规范

- 数据库名: `supply_opt`
- 表名: 采用**小写+下划线**命名，模块前缀缩写
- 字段名: 采用**小写+下划线**命名
- 索引名: `idx_{表名}_{字段名}`
- 外键名: `fk_{表名}_{字段名}`

## 表名前缀约定

| 模块 | 前缀 | 示例 |
|------|------|------|
| 月度经营计划 | mop_ | mop_monthly_plan |
| 资源池 | rp_ | rp_resource_pool |
| 需求池 | dp_ | dp_demand_pool |
| 运力池 | tcp_ | tcp_transport_capacity |
| 优化模型 | om_ | om_optimization_model |
| 匹配结果 | mr_ | mr_matching_result |

## 通用字段模板

```sql
-- 通用审计字段（必须）
cvcu_id       VARCHAR(64)  NOT NULL COMMENT '客创唯一标识',
create_by     VARCHAR(64)  NOT NULL DEFAULT '' COMMENT '创建人',
create_time   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
update_by     VARCHAR(64)  NOT NULL DEFAULT '' COMMENT '修改人',
update_time   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',

-- 通用时间范围字段（按需）
start_date    VARCHAR(10)   DEFAULT NULL COMMENT '开始日期',
end_date      VARCHAR(10)   DEFAULT NULL COMMENT '结束日期',

-- 通用状态字段（按需）
status        VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE' COMMENT '状态',
```

## DDL 模板

### 核心表DDL模板

```sql
-- 表名: {table_name}
-- 说明: {table_comment}

CREATE TABLE `{table_name}` (
    -- 主键
    `id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    
    -- 客创唯一标识
    `cvcu_id` VARCHAR(64) NOT NULL COMMENT '客创唯一标识',
    
    -- 业务字段开始
    {business_fields}
    -- 业务字段结束
    
    -- 审计字段
    `create_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '创建人',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '修改人',
    `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    
    -- 主键和索引
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_cvcu_id` (`cvcu_id`),
    {indexes}
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{table_comment}';
```

### 业务字段类型映射

| Ontology类型 | MySQL类型 | 说明 |
|-------------|----------|------|
| String | VARCHAR(255) / TEXT | 根据长度选择 |
| Integer | INT(11) | 整数 |
| Double | DECIMAL(20,6) | 金额、量值 |
| Boolean | TINYINT(1) | 0/1 |
| Date | VARCHAR(10) | yyyy-MM-dd格式 |
| DateTime | DATETIME | 时间戳 |
| JSON | TEXT / JSON | JSON数据 |

### 索引设计原则

1. **唯一索引**: cvcu_id（客创ID）必须有唯一索引
2. **业务索引**: 频繁查询字段需建立索引
3. **外键索引**: 外键字段需建立索引
4. **复合索引**: 频繁组合查询的字段建立复合索引

### 关联表设计模式

当对象之间存在多对多关系时，创建关联表：

```sql
CREATE TABLE `{relation_table}` (
    `id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `cvcu_id` VARCHAR(64) NOT NULL COMMENT '客创唯一标识',
    
    -- 关联字段
    `{source_fk}` BIGINT(20) NOT NULL COMMENT '{source_field}外键',
    `{target_fk}` BIGINT(20) NOT NULL COMMENT '{target_field}外键',
    
    -- 关联属性（如有）
    {relation_fields}
    
    -- 审计字段
    `create_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '创建人',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '修改人',
    `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_cvcu_id` (`cvcu_id`),
    INDEX `idx_{source_fk}` (`{source_fk}`),
    INDEX `idx_{target_fk}` (`{target_fk}`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{relation_comment}';
```

### Edges关系表设计规范

根据ontology图谱的edges关系，设计对应的关联表：

#### 1. 计划-模型关系 (plan_to_model)
- **约束**: 一个月度计划对应一个优化模型 (1:1)
- **表名**: `om_plan_model_rel`

```sql
CREATE TABLE `om_plan_model_rel` (
    `id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `cvcu_id` VARCHAR(64) NOT NULL COMMENT '客创唯一标识',
    `plan_id` VARCHAR(64) NOT NULL COMMENT '月度经营计划ID',
    `model_id` VARCHAR(64) NOT NULL COMMENT '优化模型ID',
    `create_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '创建人',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '修改人',
    `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_cvcu_id` (`cvcu_id`),
    UNIQUE KEY `uk_plan_id` (`plan_id`),
    UNIQUE KEY `uk_model_id` (`model_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='计划-模型关联表';
```

#### 2. 资源/需求/运力-模型关系
- **约束**: 多个资源/需求/运力可输入同一个模型 (N:1)
- **表名**: `om_model_resource_rel`, `om_model_demand_rel`, `om_model_transport_rel`

```sql
-- 资源-模型关系
CREATE TABLE `om_model_resource_rel` (
    `id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `cvcu_id` VARCHAR(64) NOT NULL COMMENT '客创唯一标识',
    `model_id` VARCHAR(64) NOT NULL COMMENT '优化模型ID',
    `resource_id` VARCHAR(64) NOT NULL COMMENT '资源池ID',
    `create_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '创建人',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '修改人',
    `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_cvcu_id` (`cvcu_id`),
    INDEX `idx_model_id` (`model_id`),
    INDEX `idx_resource_id` (`resource_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型-资源池关联表';

-- 需求-模型关系
CREATE TABLE `om_model_demand_rel` (
    `id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `cvcu_id` VARCHAR(64) NOT NULL COMMENT '客创唯一标识',
    `model_id` VARCHAR(64) NOT NULL COMMENT '优化模型ID',
    `demand_id` VARCHAR(64) NOT NULL COMMENT '需求池ID',
    `create_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '创建人',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '修改人',
    `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_cvcu_id` (`cvcu_id`),
    INDEX `idx_model_id` (`model_id`),
    INDEX `idx_demand_id` (`demand_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型-需求池关联表';

-- 运力-模型关系
CREATE TABLE `om_model_transport_rel` (
    `id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `cvcu_id` VARCHAR(64) NOT NULL COMMENT '客创唯一标识',
    `model_id` VARCHAR(64) NOT NULL COMMENT '优化模型ID',
    `transport_id` VARCHAR(64) NOT NULL COMMENT '运力池ID',
    `create_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '创建人',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '修改人',
    `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_cvcu_id` (`cvcu_id`),
    INDEX `idx_model_id` (`model_id`),
    INDEX `idx_transport_id` (`transport_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模型-运力池关联表';
```

#### 3. 资源-运力站点匹配关系 (resource_to_transport)
- **约束**: 资源的下载站点必须匹配运力的起点站点 (N:N)
- **表名**: `rp_transport_station_rel`

```sql
CREATE TABLE `rp_transport_station_rel` (
    `id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `cvcu_id` VARCHAR(64) NOT NULL COMMENT '客创唯一标识',
    `resource_id` VARCHAR(64) NOT NULL COMMENT '资源池ID',
    `transport_id` VARCHAR(64) NOT NULL COMMENT '运力池ID',
    `download_station` VARCHAR(100) NOT NULL COMMENT '资源下载站点(必须=运力起点站点)',
    `start_station` VARCHAR(100) NOT NULL COMMENT '运力起点站点',
    `is_matched` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '站点是否匹配:0-否,1-是',
    `remark` TEXT COMMENT '备注',
    `create_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '创建人',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '修改人',
    `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_cvcu_id` (`cvcu_id`),
    INDEX `idx_resource_id` (`resource_id`),
    INDEX `idx_transport_id` (`transport_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资源-运力站点匹配表';
```

#### 4. 运力-需求站点匹配关系 (transport_to_demand)
- **约束**: 运力的终点站点必须匹配需求的门站站点 (N:N)
- **表名**: `tcp_demand_station_rel`

```sql
CREATE TABLE `tcp_demand_station_rel` (
    `id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `cvcu_id` VARCHAR(64) NOT NULL COMMENT '客创唯一标识',
    `transport_id` VARCHAR(64) NOT NULL COMMENT '运力池ID',
    `demand_id` VARCHAR(64) NOT NULL COMMENT '需求池ID',
    `end_station` VARCHAR(100) NOT NULL COMMENT '运力终点站点(必须=需求门站站点)',
    `gate_station` VARCHAR(100) NOT NULL COMMENT '需求门站站点',
    `is_matched` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '站点是否匹配:0-否,1-是',
    `remark` TEXT COMMENT '备注',
    `create_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '创建人',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '修改人',
    `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_cvcu_id` (`cvcu_id`),
    INDEX `idx_transport_id` (`transport_id`),
    INDEX `idx_demand_id` (`demand_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='运力-需求站点匹配表';
```

#### Edges关系表汇总

| Edge Code | 源对象 | 目标对象 | 约束 | 关系表 | 基数 |
|-----------|--------|---------|------|--------|------|
| plan_to_model | monthly_operation_plan | optimization_model | 1:1 | om_plan_model_rel | 1:1 |
| resource_to_model | resource_pool | optimization_model | N:1 | om_model_resource_rel | N:1 |
| demand_to_model | demand_pool | optimization_model | N:1 | om_model_demand_rel | N:1 |
| transport_to_model | transport_capacity_pool | optimization_model | N:1 | om_model_transport_rel | N:1 |
| resource_to_transport | resource_pool | transport_capacity_pool | N:N(站点匹配) | rp_transport_station_rel | N:N |
| transport_to_demand | transport_capacity_pool | demand_pool | N:N(站点匹配) | tcp_demand_station_rel | N:N |

> **注意**: `model_to_result` (需供和模型的关系表) 不设计关联表，通过model_id和result_id直接关联。

## 字段映射示例

根据ontology.json对象生成的DDL示例：

### 月度经营计划表 (mop_monthly_plan)

| Ontology字段 | MySQL字段 | 类型 | 说明 |
|-------------|----------|------|------|
| cvcu_id | cvcu_id | VARCHAR(64) | 客创ID |
| plan_name | plan_name | VARCHAR(255) | 计划名称 |
| year | year_num | INT(11) | 年份 |
| month | month_num | INT(11) | 月份 |
| start_date | start_date | VARCHAR(10) | 开始日期 |
| end_date | end_date | VARCHAR(10) | 结束日期 |
| target_profit | target_profit | DECIMAL(20,6) | 目标利润 |
| matching_principle | matching_principle | TEXT | 匹配原则 |

### 资源池表 (rp_resource_pool)

| Ontology字段 | MySQL字段 | 类型 | 说明 |
|-------------|----------|------|------|
| cvcu_id | cvcu_id | VARCHAR(64) | 客创ID |
| resource_name | resource_name | VARCHAR(255) | 资源名称 |
| supplier_name | supplier_name | VARCHAR(255) | 供应商名称 |
| contract_volume | contract_volume | DECIMAL(20,6) | 合同量（万方） |
| min_offtake_volume | min_offtake_volume | DECIMAL(20,6) | 最低提气量 |
| resource_unit_price | resource_unit_price | DECIMAL(20,6) | 资源单价（元/方） |
| top_coefficient | top_coefficient | DECIMAL(10,4) | 照付不议系数 |
| download_station | download_station | VARCHAR(100) | 下载站点 |
| resource_status | resource_status | VARCHAR(20) | 资源状态 |

### 需求池表 (dp_demand_pool)

| Ontology字段 | MySQL字段 | 类型 | 说明 |
|-------------|----------|------|------|
| cvcu_id | cvcu_id | VARCHAR(64) | 客创ID |
| customer_name | customer_name | VARCHAR(255) | 客户名称 |
| customer_type | customer_type | VARCHAR(50) | 客户类型 |
| demand_volume | demand_volume | DECIMAL(20,6) | 需求量（万方） |
| min_demand_volume | min_demand_volume | DECIMAL(20,6) | 最低需求量 |
| priority | priority | VARCHAR(20) | 优先级 |
| must_supply | must_supply | TINYINT(1) | 是否必须供气 |
| allow_flexible | allow_flexible | TINYINT(1) | 是否允许灵活供应 |
| gate_station | gate_station | VARCHAR(100) | 门站站点 |
| sales_unit_price | sales_unit_price | DECIMAL(20,6) | 销售单价 |

### 运力池表 (tcp_transport_capacity)

| Ontology字段 | MySQL字段 | 类型 | 说明 |
|-------------|----------|------|------|
| cvcu_id | cvcu_id | VARCHAR(64) | 客创ID |
| pipeline_name | pipeline_name | VARCHAR(255) | 管道名称 |
| design_capacity | design_capacity | DECIMAL(20,6) | 设计输气能力（万方） |
| min_transport_volume | min_transport_volume | DECIMAL(20,6) | 运输保底量 |
| transport_unit_price | transport_unit_price | DECIMAL(20,6) | 管输单价（元/方） |
| capacity_status | capacity_status | VARCHAR(20) | 运力状态 |
| start_station | start_station | VARCHAR(100) | 起点站点 |
| end_station | end_station | VARCHAR(100) | 终点站点 |

### 优化模型表 (om_optimization_model)

| Ontology字段 | MySQL字段 | 类型 | 说明 |
|-------------|----------|------|------|
| cvcu_id | cvcu_id | VARCHAR(64) | 客创ID |
| model_name | model_name | VARCHAR(255) | 模型名称 |
| objective_function | objective_function | TEXT | 目标函数 |
| constraint_set | constraint_set | TEXT | 约束条件集 |
| solver_type | solver_type | VARCHAR(50) | 求解器类型 |
| model_status | model_status | VARCHAR(20) | 模型状态 |

### 匹配结果表 (mr_matching_result)

| Ontology字段 | MySQL字段 | 类型 | 说明 |
|-------------|----------|------|------|
| cvcu_id | cvcu_id | VARCHAR(64) | 客创ID |
| result_name | result_name | VARCHAR(255) | 结果名称 |
| total_profit | total_profit | DECIMAL(20,6) | 总利润 |
| total_sales_revenue | total_sales_revenue | DECIMAL(20,6) | 总销售收入 |
| total_resource_cost | total_resource_cost | DECIMAL(20,6) | 总资源成本 |
| total_transport_cost | total_transport_cost | DECIMAL(20,6) | 总运力成本 |
| total_top_cost | total_top_cost | DECIMAL(20,6) | 总照付不议成本 |
| total_shortage_cost | total_shortage_cost | DECIMAL(20,6) | 总缺口成本 |
| allocated_resource | allocated_resource | TEXT | 资源分配详情JSON |
| allocated_volume | allocated_volume | TEXT | 分配气量JSON |
| satisfied_demand | satisfied_demand | TEXT | 客户供气详情JSON |
| transport_path | transport_path | TEXT | 运输路径JSON |
| result_status | result_status | VARCHAR(20) | 结果状态 |
