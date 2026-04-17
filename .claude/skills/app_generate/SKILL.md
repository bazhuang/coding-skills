---
name: app_generate
description: |
  基于本体图谱进行数据建模、架构设计、详细设计的通用开发流程工具。
  当用户需要根据ontology图谱schema进行DDL生成、数据库建模、架构设计、详细设计等开发工作时触发。
  适用于任意业务领域的模型设计和代码生成场景。
  支持动态识别业务场景并加载领域增强知识。
---

# App-Generate Skill (通用版)

基于本体图谱(ontology)的schema信息解析，完成数据建模、架构设计、详细设计的完整开发流程。

## 核心特性

- **通用性**：适用于任意业务领域的本体图谱
- **动态化**：表名、包路径、关联表均从ontology动态生成
- **可配置**：支持用户自定义项目参数
- **场景感知**：自动识别业务领域并加载领域增强知识

---

## 阶段一：本体图谱Schema解析

### 1.1 必需输入

用户必须提供以下信息之一：

| 类型 | 说明 | 优先级 |
|------|------|--------|
| **Ontology JSON文件** | 包含objects、edges的完整图谱定义 | P0（必需） |
| **项目包路径前缀** | 如 `com.example.project` | P1（推荐） |
| **数据库名称** | 如 `myapp_db` | P2（可选） |
| **模块前缀映射** | 对象code到表名前缀的映射 | P3（可选） |

### 1.2 Ontology格式要求

Ontology文件应为JSON格式，包含以下核心结构：

```json
{
  "objects": [
    {
      "code": "object_code",
      "name": "对象名称",
      "comment": "对象描述",
      "type": "对象类型",
      "properties": [
        {
          "code": "field_code",
          "name": "字段名称",
          "comment": "字段描述",
          "type": "String|Integer|Double|Boolean|Date|DateTime|JSON"
        }
      ]
    }
  ],
  "edges": [
    {
      "code": "edge_code",
      "name": "关系名称",
      "source_code": "源对象code",
      "target_code": "目标对象code",
      "constraint": "约束描述"
    }
  ],
  "rules": [...],
  "behaviors": [...],
  "sop": [...]
}
```

### 1.3 解析内容

1. **解析Objects**：提取对象编码、名称、类型、属性
2. **解析Edges**：提取关系编码、源对象、目标对象、约束
3. **解析Rules**：提取业务规则定义
4. **解析Behaviors**：提取行为定义（CRUD）
5. **解析SOP**：提取业务流程定义

---

## 场景识别与动态知识加载

基于解析的Objects、Edges信息，自动识别业务领域并加载对应知识增强包。

### 场景识别规则

| 场景关键词 | 识别依据 | 加载知识包 |
|-----------|---------|-----------|
| **天然气供需匹配** | objects含`resource_pool`,`demand_pool`,`transport_capacity_pool`,`optimization_model` 或 edges含`matching_result` | `domain/natural_gas/*` |
| **订单/交易系统** | objects含`order`,`product`,`customer` 且无专项领域对象 | 通用流程 |
| **通用业务系统** | 其他标准对象组合 | 通用流程 |

### 动态加载机制

当识别到特定领域时，加载以下增强知识：

```markdown
## 领域增强包加载

场景: {识别结果}
知识包: {知识包路径}

包含内容:
1. 业务特定规范 (CLAUDE.md)
2. 专项头脑风暴议题
3. 领域特定DDL规则
4. 业务接口约定
```

### 天然气供需匹配场景知识包

当识别为此场景时，自动加载以下内容：

#### 专项头脑风暴议题（A-G）

- **议题A**：月度计划编制规则（运筹模型输入）
- **议题B**：资源池与需求池匹配算法
- **议题C**：传输运力约束建模
- **议题D**：多目标优化策略（成本/效率/稳定性）
- **议题E**：结果可视化与报表设计
- **议题F**：历史数据积累与分析
- **议题G**：异常处理与人工干预机制

#### 业务特定规范

- 包路径前缀：`com.enn.supply.opt`
- 业务唯一标识：`cvcu_id`（而非通用`biz_id`）
- 时间粒度：月度（plan_date格式：yyyy-MM）
- 核心关系：计划→模型→结果 调用链

---

## 阶段二：数据建模 - MySQL DDL生成

<HARD-GATE>
完成DDL生成后，必须等待用户确认DDL文档，才能进入下一阶段（头脑风暴）。
</HARD-GATE>

### 2.1 动态表名生成规则

**规则**：将对象code转为下划线命名，并添加模块前缀

| 对象code | 表名（无前缀） | 表名（有前缀：mod_） |
|----------|---------------|---------------------|
| monthlyOperationPlan | monthly_operation_plan | mod_monthly_operation_plan |
| resourcePool | resource_pool | mod_resource_pool |
| userInfo | user_info | mod_user_info |

**表名前缀映射**（可选配置）：

```yaml
# 用户可通过配置覆盖默认前缀
prefix_mapping:
  core_object: core_
  transaction: txn_
  reference: ref_
```

### 2.2 字段类型映射规则

| Ontology类型 | MySQL类型 | 说明 |
|-------------|----------|------|
| String | VARCHAR(255) | 默认255，特殊长度可调整 |
| Integer | INT(11) | 整数 |
| Long | BIGINT(20) | 长整数 |
| Double | DECIMAL(20,6) | 金额、量值（高精度） |
| Boolean | TINYINT(1) | 0/1 |
| Date | VARCHAR(10) | yyyy-MM-dd格式 |
| DateTime | DATETIME | 时间戳 |
| JSON | TEXT / JSON | JSON数据 |

### 2.3 必需字段规范

每个表必须包含以下审计字段：

```sql
-- 主键（必需）
`id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',

-- 业务唯一标识（必需）
`biz_id` VARCHAR(64) NOT NULL COMMENT '业务唯一标识',

-- 审计字段（必需）
`create_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '创建人',
`create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
`update_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '修改人',
`update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',

-- 时间范围字段（按需添加）
`start_date` VARCHAR(10) DEFAULT NULL COMMENT '开始日期',
`end_date` VARCHAR(10) DEFAULT NULL COMMENT '结束日期',

-- 状态字段（按需添加）
`status` VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' COMMENT '状态'
```

### 2.4 动态关联表生成

根据edges关系动态生成关联表：

**生成规则**：
1. 遍历所有edges
2. 对于N:1关系，生成 `{target_table}_{source_table}_rel` 关联表
3. 对于1:1关系，生成 `{source_table}_{target_table}_rel` 关联表
4. 对于N:N关系，生成带复合唯一索引的关联表
5. 排除自关联和特殊关系

**关联表模板**：

```sql
-- 关联表: {relation_table_name}
-- 说明: {source_object} 与 {target_object} 的关联表
-- 关系类型: {relationship_type} ({cardinality})

CREATE TABLE `{relation_table_name}` (
    `id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `biz_id` VARCHAR(64) NOT NULL COMMENT '业务唯一标识',
    
    -- 关联字段
    `{source_fk}` BIGINT(20) NOT NULL COMMENT '{source_object}外键',
    `{target_fk}` BIGINT(20) NOT NULL COMMENT '{target_object}外键',
    
    -- 关联属性（如edges中有额外属性）
    {edge_properties}
    
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

### 2.5 索引设计规范

**索引优先级**：

| 优先级 | 索引类型 | 说明 |
|--------|---------|------|
| P0 | 主键索引 | id自增主键 |
| P1 | 唯一索引 | biz_id业务唯一标识 |
| P2 | 外键索引 | 关联表外键字段 |
| P3 | 业务索引 | 频繁查询字段 |
| P4 | 复合索引 | 组合查询字段 |

### 2.6 输出初步DDL

生成DDL脚本文件，命名格式：`{module}_ddl_{date}.sql`

**完成后必须**：
1. 向用户展示DDL文件路径和表数量概览
2. 明确告知用户："DDL已生成完成，请确认后我将进入头脑风暴阶段"
3. 等待用户明确回复"确认"或"继续"后，才能进入阶段三

---

## 阶段三：头脑风暴 - 技术逻辑补充 ★

<HARD-GATE>
在完成头脑风暴讨论并获得用户批准之前，不得进入下一阶段。
</HARD-GATE>

### 3.1 核心原则

1. **One question at a time** - 一次只问一个问题，不堆积
2. **Multiple choice preferred** - 优先提供选择题
3. **Incremental validation** - 分段展示设计，获取批准后再继续
4. **Be flexible** - 随时准备回退澄清
5. **YAGNI ruthlessly** - 去除不必要的功能

### 3.2 通用讨论议题

基于初步DDL，与架构师逐一讨论以下通用主题：

#### 议题1：数据模型优化

**讨论内容**：
- JSON字段存储是否合理？
- 是否需要增加明细表？
- 是否需要冗余字段优化查询？

**讨论选项**：
```
A. 保持JSON字段，适合动态结构
B. 增加结构化明细表，便于前端展示和查询
C. 混合方案：JSON存储+明细表索引
```

#### 议题2：索引设计

**讨论内容**：
- 现有索引是否满足查询需求？
- 是否需要复合索引？
- 分表策略？

**讨论选项**：
```
A. 现有索引足够
B. 增加复合索引
C. 考虑按时间/业务维度分表
```

#### 议题3：关联表设计

**讨论内容**：
- 关联表设计是否合理？
- 是否需要额外的关联属性？
- 关联约束的实现方式？

**讨论选项**：
```
A. 现有设计合理
B. 关联表增加额外字段
C. 增加约束校验逻辑
```

#### 议题4：约束实现策略

**讨论内容**：
- 业务约束在数据层还是业务层实现？
- 是否需要专门的约束校验表？

**讨论选项**：
```
A. 业务层校验（Service层）
B. 数据库层校验（Trigger/Check约束）
C. 专门的约束配置表
```

#### 议题5：性能与扩展性

**讨论内容**：
- 大数据量场景预估？
- 批量操作需求？
- 缓存策略？

**讨论选项**：
```
A. V1版本先不分表，按需扩展
B. 预留分表字段（partition_key）
C. 增加读写分离设计
```

#### 议题6：审计字段配置

**讨论内容**：
- 审计字段是否完整？
- 是否需要记录版本/状态变更历史？

**讨论选项**：
```
A. 基础审计字段足够
B. 增加状态变更历史表
C. 增加操作日志表
```

### 3.3 交互式讨论流程

```
1. 展示初步DDL概述
   - 表数量、核心表结构
   - 关系表设计

2. 逐一发起讨论（一次一个议题）
   - 提供讨论内容和选项
   - 等待架构师回复
   - 记录决策

3. 汇总讨论结论
   - 补充的字段
   - 补充的表
   - 索引优化
   - 约束设计

4. 输出补充后的DDL
   - 更新DDL文件
   - 获得架构师最终确认
```

### 3.4 头脑风暴输出模板

```markdown
## 头脑风暴结论

### 讨论议题及决策

| 议题 | 讨论内容 | 最终决策 | 补充内容 |
|------|---------|---------|---------|
| 数据模型 | JSON vs 结构化 | [决策] | [补充] |
| 索引设计 | ... | [决策] | [补充] |
| ... | ... | ... | ... |

### 补充表结构

[补充的DDL]

### 最终DDL

已更新至：{filename}
```

**完成后必须**：
1. 输出头脑风暴结论文档：`{module}_brainstorm_summary_{date}.md`
2. 更新DDL文件，包含补充的表结构
3. 明确告知用户："头脑风暴阶段完成，已生成结论文档和更新DDL。请确认后我将进入架构设计阶段"
4. 等待用户明确回复"确认"或"继续"后，才能进入阶段四

---

## 阶段四：架构设计（概要设计）

<HARD-GATE>
完成架构设计文档后，必须等待用户确认，才能进入下一阶段（详细设计）。
</HARD-GATE>

基于技术规范和头脑风暴结论，输出架构设计文档。

**输出文档模板**: `references/arch-design-template.md`

### 4.1 设计内容

1. **业务背景**
   - 业务场景描述
   - 核心目标
   - 业务流程

2. **功能需求**
   - 功能列表
   - 详细功能说明

3. **非功能性需求**
   - 性能需求
   - 安全需求
   - 数据需求

4. **系统设计**
   - 系统架构图
   - 模块划分
   - 核心类设计
   - 数据库设计（含头脑风暴补充）

5. **接口设计**
   - REST API定义
   - 请求/响应格式

6. **风险评估**

### 4.2 通用架构规范

- 调用链: `starter → controller → biz → service → dal`
- Controller返回: `ServiceResult<VO>`
- Biz层职责: 业务编排、事务管理
- Service层职责: 业务逻辑实现
- DAL层职责: 数据访问
- 所有VO/DTO/PO使用`@Data`注解
- Controller方法必须添加`@Authorize`注解
- 使用Spring Boot 3.x兼容的jakarta包

### 4.3 包路径生成规则

**默认包路径**：`{user_package_prefix}.{module}.{layer}`

| 层级 | 包路径 |
|------|--------|
| Controller | `{base}.controller.*` |
| Biz | `{base}.biz.*` |
| Service | `{base}.service.*` |
| DAL | `{base}.dal.mapper` |
| PO | `{base}.dal.po` |
| DTO | `{base}.service.dto` |
| VO | `{base}.client.vo` |

### 4.4 输出文档

命名格式：`{module}_architecture_design_{date}.md`

**完成后必须**：
1. 向用户展示架构设计文档路径
2. 简要说明文档包含的核心内容（业务背景、功能需求、系统设计、接口设计等）
3. 明确告知用户："架构设计文档已完成。请确认后我将进入详细设计阶段"
4. 等待用户明确回复"确认"或"继续"后，才能进入阶段五

---

## 阶段五：详细设计

<HARD-GATE>
完成详细设计文档后，必须等待用户确认，才能进入下一阶段（代码生成）。
</HARD-GATE>

基于架构设计，输出详细设计文档。

**输出文档模板**: `references/detail-design-template.md`

### 5.1 设计内容

1. **数据库设计**
   - 表清单
   - 完整表结构（含索引）
   - 建表SQL

2. **Java类设计**
   - 类清单
   - PO/DTO/VO类完整代码
   - Mapper接口
   - Mapper XML
   - Service/BizService/Controller类完整代码

3. **接口设计**
   - 完整请求/响应格式

4. **异常处理**
   - 业务异常定义
   - 系统异常处理

5. **测试用例**

### 5.2 输出文档

命名格式：`{module}_detail_design_{date}.md`

**完成后必须**：
1. 向用户展示详细设计文档路径
2. 简要说明文档包含的核心内容（数据库设计、Java类设计、接口设计等）
3. 明确告知用户："详细设计文档已完成。请确认后我将进入代码生成阶段"
4. 等待用户明确回复"确认"或"继续"后，才能进入阶段六

---

## 阶段六：代码生成

基于详细设计文档，生成完整的Java代码。

### 6.1 生成文件

1. **PO类** - 数据持久化对象
2. **DTO类** - 数据传输对象
3. **VO类** - 视图对象
4. **Mapper接口** - MyBatis数据访问
5. **Mapper XML** - MyBatis SQL映射
6. **Service类** - 业务逻辑
7. **BizService类** - 业务编排
8. **Controller类** - REST接口

### 6.2 代码规范

- 包路径遵循 `{user_package}.{module}.{layer}` 约定
- 使用`@Data`、`@Service`、`@Mapper`等注解（Lombok）
- Spring Boot 3.x使用jakarta包
- Mapper XML使用MyBatis规范
- 添加必要的注释

---

## 输出文件命名约定

- DDL文件: `{module}_ddl_{date}.sql`
- 头脑风暴结论: `{module}_brainstorm_summary_{date}.md`
- 架构设计: `{module}_architecture_design_{date}.md`
- 详细设计: `{module}_detail_design_{date}.md`
- 日期格式: yyyy-MM-dd

---

## 关键约束

1. 每个阶段完成后必须等待用户确认才能进入下一阶段
2. 表名从对象code动态生成（下划线命名）
3. 包路径从用户配置动态生成
4. 关联表从edges关系动态生成
5. 必须包含审计字段
6. Controller层必须添加@Authorize注解
7. 返回类型统一使用ServiceResult包装

---

## 用户配置项

用户在开始使用前可以提供以下配置（可选）：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `base_package` | 基础包路径前缀 | `com.example` |
| `db_name` | 数据库名称 | `app_db` |
| `table_prefix` | 表名前缀 | 无 |
| `author` | 文档作者 | `AI` |

### 场景自动识别

系统会根据Ontology内容自动识别业务场景，并加载对应知识增强包：

| 场景 | 识别关键词 | 自动配置 |
|------|-----------|---------|
| 天然气供需匹配 | `resource_pool`, `demand_pool`, `transport_capacity_pool`, `optimization_model` | 加载领域知识包 |
| 其他场景 | - | 使用通用规范 |
