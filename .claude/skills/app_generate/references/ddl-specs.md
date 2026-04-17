# MySQL DDL 生成规范与模板（通用版）

## 命名规范

- 数据库名: `{db_name}`（用户配置）
- 表名: 采用**小写+下划线**命名，可选模块前缀
- 字段名: 采用**小写+下划线**命名
- 索引名: `idx_{表名}_{字段名}`
- 外键名: `fk_{表名}_{字段名}`

## 动态表名生成

### 命名规则

```
表名 = [表前缀] + 下划线命名(对象code)

示例：
- 对象code: monthlyOperationPlan → 表名: monthly_operation_plan
- 对象code: userInfo → 表名: user_info
- 带前缀: user_info → sys_user_info
```

### 表前缀映射（可选配置）

| 对象类型 | 前缀 | 示例 |
|---------|------|------|
| 核心对象 | 无 / `core_` | core_resource_pool |
| 业务对象 | 无 / `biz_` | biz_order |
| 关联对象 | `rel_` | rel_order_item |
| 历史对象 | `his_` | his_order |

## 通用字段模板

```sql
-- 通用审计字段（必须）
`id`            BIGINT(20)  NOT NULL AUTO_INCREMENT COMMENT '主键ID',
`biz_id`        VARCHAR(64) NOT NULL COMMENT '业务唯一标识',
`create_by`     VARCHAR(64) NOT NULL DEFAULT '' COMMENT '创建人',
`create_time`   DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
`update_by`     VARCHAR(64) NOT NULL DEFAULT '' COMMENT '修改人',
`update_time`   DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',

-- 通用时间范围字段（按需）
`start_date`    VARCHAR(10)  DEFAULT NULL COMMENT '开始日期',
`end_date`      VARCHAR(10)  DEFAULT NULL COMMENT '结束日期',

-- 通用状态字段（按需）
`status`        VARCHAR(20)  NOT NULL DEFAULT 'ACTIVE' COMMENT '状态'
```

## DDL 模板

### 核心表DDL模板

```sql
-- 表名: {table_name}
-- 说明: {table_comment}

CREATE TABLE `{table_name}` (
    -- 主键
    `id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    
    -- 业务唯一标识
    `biz_id` VARCHAR(64) NOT NULL COMMENT '业务唯一标识',
    
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
    UNIQUE KEY `uk_biz_id` (`biz_id`),
    {indexes}
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{table_comment}';
```

## 业务字段类型映射

| Ontology类型 | MySQL类型 | 说明 |
|-------------|----------|------|
| String | VARCHAR(255) / TEXT | 根据长度选择 |
| Integer | INT(11) | 整数 |
| Long | BIGINT(20) | 长整数 |
| Double | DECIMAL(20,6) | 金额、量值（高精度） |
| Boolean | TINYINT(1) | 0/1 |
| Date | VARCHAR(10) | yyyy-MM-dd格式 |
| DateTime | DATETIME | 时间戳 |
| JSON | TEXT / JSON | JSON数据 |

## 索引设计原则

1. **唯一索引**: biz_id（业务唯一标识）必须有唯一索引
2. **业务索引**: 频繁查询字段需建立索引
3. **外键索引**: 外键字段需建立索引
4. **复合索引**: 频繁组合查询的字段建立复合索引

## 动态关联表生成

### 生成规则

根据edges关系动态生成关联表：

```sql
-- 表名: {source_table}_{target_table}_rel
-- 说明: {source_object} 与 {target_object} 的关联表
-- 关系类型: {relationship_type}

CREATE TABLE `{relation_table}` (
    `id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `biz_id` VARCHAR(64) NOT NULL COMMENT '业务唯一标识',
    
    -- 关联字段
    `{source_fk}` BIGINT(20) NOT NULL COMMENT '{source_object}外键',
    `{target_fk}` BIGINT(20) NOT NULL COMMENT '{target_object}外键',
    
    -- 关联属性（如有）
    {relation_fields}
    
    -- 审计字段
    `create_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '创建人',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '修改人',
    `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_biz_id` (`biz_id`),
    {unique_constraints}
    INDEX `idx_{source_fk}` (`{source_fk}`),
    INDEX `idx_{target_fk}` (`{target_fk}`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{relation_comment}';
```

### 基数约束对应索引策略

| 基数 | 关系类型 | 唯一约束 |
|------|---------|---------|
| 1:1 | 一对一 | source_fk 和 target_fk 各自唯一 |
| N:1 | 多对一 | source_fk 普通索引，target_fk 普通索引 |
| N:N | 多对多 | 无唯一约束，或复合唯一键 |

## 字段映射示例

根据ontology对象生成的DDL示例：

### 通用对象表 ({object_code})

| Ontology字段 | MySQL字段 | 类型 | 说明 |
|-------------|----------|------|------|
| biz_id | biz_id | VARCHAR(64) | 业务ID |
| name | name | VARCHAR(255) | 名称 |
| code | code | VARCHAR(100) | 编码 |
| status | status | VARCHAR(20) | 状态 |
| amount | amount | DECIMAL(20,6) | 金额 |
| quantity | quantity | DECIMAL(20,6) | 数量 |
| remark | remark | TEXT | 备注 |
| startDate | start_date | VARCHAR(10) | 开始日期 |
| endDate | end_date | VARCHAR(10) | 结束日期 |
| extData | ext_data | JSON | 扩展数据 |
