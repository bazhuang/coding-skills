---
name: detailed-design
description: 软件详细设计 skill - 基于概要设计文档，通过协作对话完成详细的数据库设计、接口定义、类设计和核心算法设计。生成可直接指导编码的详细设计文档。适用于软件开发的详细设计阶段。当用户需要进行数据库表设计、API 详细定义、类结构设计时使用。
---

# 详细设计 Skill

> **阶段定位**：软件开发第三阶段。**前置条件**：概要设计阶段已完成，存在 `docs/design/high-level-design.md`。本阶段完成后，进入编码阶段。

基于概要设计文档生成可直接指导编码的详细设计。

## 核心原则

1. **基于概要设计**：详细设计必须基于已确认的概要设计文档
2. **可编码性**：设计要足够详细，开发人员可以直接编码
3. **数据库规范**：严格遵守数据库设计规范
4. **HARD-GATE 机制**：完成详细设计后，必须得到用户明确确认才能进入编码阶段

## 前置条件

**必须先完成概要设计阶段**，并且存在 `docs/design/high-level-design.md` 文件。

如果用户直接要求做详细设计但没有概要设计文档：
1. 询问是否已有概要设计文档
2. 如果没有，建议先完成概要设计
3. 如果用户坚持，可以基于用户提供的信息直接进行

## 工作流程

### 第一步：读取概要设计和本体图谱

读取：
- `docs/design/high-level-design.md` — 系统架构、模块划分、技术选型、数据架构、接口列表

**搜索项目中是否有本体图谱文件**：
- 查找 `**/*本体*`、`**/*ontology*`、`**/*模型*` 等模式（不限文件类型）
- 如果找到，读取并分析完整结构

**如果项目没有本体图谱**：
- 基于概要设计文档进行分析
- 从概要设计的数据架构中提取表结构信息

### 第二步：从本体图谱推导详细设计

**从 Objects 推导表结构（架构师视角）**：
- 每个 object 的属性 → 表字段定义（字段名、类型、约束）
- object 的业务含义 → 字段注释
- object 的标识属性 → 唯一索引设计
- **避免过度设计**：不是所有属性都需要立即建表，关注核心属性；冗余字段要谨慎添加

**从 Edges 推导关系表结构（架构师视角）**：
- **one-to-one 关系** → 在任一表中添加 `{object}_id BIGINT` 外键字段
- **one-to-many 关系** → 在"多"的一方添加 `{object}_id BIGINT` 外键字段
- **many-to-many 关系** → 创建关联表，包含两个外键字段和审计字段
- **避免过度设计**：评估关系的必要性，不是所有关系都需要立即实现；考虑是否可以通过应用层关联

**从 Rules 推导约束和验证（架构师视角）**：
- 字段级约束（NOT NULL、UNIQUE、CHECK）
- 应用层验证逻辑
- 业务规则的实现方式
- **避免过度设计**：复杂规则优先在应用层实现，保持数据库设计简洁；不要过早优化

**从 Behaviors 推导接口详细定义（架构师视角）**：
- 每个 behavior → 一个或多个 API 接口
- behavior 的输入参数 → 请求体字段
- behavior 的输出结果 → 响应体字段
- behavior 的前置条件 → 接口校验逻辑
- **避免过度设计**：接口设计要简洁实用，避免过度抽象；参数不要过多，响应不要过于复杂

**从 SOP 推导业务流程接口（架构师视角）**：
- 每个 SOP 步骤 → 接口调用顺序
- SOP 的参与者 → 接口权限设计
- SOP 的异常处理 → 错误码定义
- **避免过度设计**：流程可以简化，不必完全照搬 SOP 的所有步骤；优先实现主流程

**架构师设计原则**：
- **YAGNI（You Aren't Gonna Need It）**：不要设计当前不需要的功能
- **数据库设计从简**：字段、索引、表都从最小集合开始，按需扩展
- **接口设计实用主义**：满足当前业务需求即可，不要过度抽象
- **可扩展但不过度**：预留扩展空间，但不要为未来可能的需求过度设计

**仅针对以下情况提问**：
- 本体图谱中未定义的字段类型或长度
- 性能优化相关的索引策略
- 本体图谱中模糊或冲突的定义

### 第三步：数据库设计规范（必须遵守）

**主键规范**：
- 使用 `BIGINT AUTO_INCREMENT`
- 不使用业务 ID 作为主键

**审计字段（所有表必须包含）**：
```sql
created_by BIGINT NOT NULL COMMENT '创建人ID',
created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
updated_by BIGINT NOT NULL COMMENT '修改人ID',
updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间'
```

**外键约束**：
- 不使用数据库外键约束（FOREIGN KEY）
- 数据完整性由应用层保证

**关系映射（基于 Edges）**：
- **one-to-one**：在任一表中添加外键字段
- **one-to-many**：在"多"的一方添加外键字段
- **many-to-many**：创建独立的关联表，包含两个外键字段和审计字段

**关联表命名规范**：
- 命名格式：`{object1}_{object2}`（按字母顺序）
- 必须包含：两个外键字段 + 审计字段
- 主键：复合主键或独立自增主键

### 第四步：生成详细设计文档

分段写入 `docs/design/detailed-design.md`：

**文档重点**：描述**怎么做的具体实现**（How - Implementation），可直接指导编码

**文档结构**：

**1. 设计概述**
- 设计目标、设计原则、技术栈

**2. 数据库详细设计**
- **完整 DDL**：所有表的 CREATE TABLE 语句（包括字段类型、长度、约束、默认值、注释）
- **索引设计**：基于查询场景设计的索引（普通索引、唯一索引）
- **数据迁移脚本**：初始化数据、数据转换脚本

**3. 接口详细设计**
- **接口契约**：每个 API 的完整定义
  - 请求参数（字段名、类型、必填、校验规则、示例）
  - 响应格式（成功响应、错误响应、字段说明）
  - 错误码定义
- **接口调用示例**

**4. 模块详细设计**
- **类设计**：类名、属性、方法签名
- **核心算法**：关键业务逻辑的实现方式
- **异常处理**：异常场景和处理策略

**注意**：基于概要设计的表结构和接口列表，补充完整的实现细节

**写入步骤**：
1. 确保 `docs/design/` 目录存在
2. 分段写入 `detailed-design.md`：
   - 第一段：数据库设计（所有表的 DDL）
   - 第二段：接口详细设计
   - 第三段：类设计和核心算法
3. 提交到 git

### 第五步：设计自查

在要求用户审查之前，检查：
- 所有 objects 是否都有对应的表设计？
- 所有 edges 是否都正确映射到表结构（含关联表）？
- 数据库设计是否符合规范（主键、审计字段、无外键约束）？
- 所有 behaviors 是否都有对应的接口定义？
- 接口定义是否完整（请求、响应、错误处理）？
- 类设计是否清晰？
- 设计是否与概要设计一致？

### 第六步：用户审查（HARD-GATE）

完成文档后，要求用户审查：

```
详细设计文档已完成，请审查：
- docs/design/detailed-design.md

请确认：
1. 数据库表设计是否完整？
2. 接口定义是否清晰？
3. 类设计是否合理？
4. 是否可以直接指导编码？

确认后我们将进入编码阶段。
```

**在用户明确确认之前，不得进入编码阶段。**

## 本体图谱到详细设计的映射规则

本体图谱结构：

```javascript
{
  "objects": [...],      // 业务对象定义
  "edges": [...],        // 对象间关系定义
  "rules": [...],        // 业务规则和约束
  "behaviors": [...],    // 业务行为和操作
  "sop": [...]          // 标准操作流程
}
```

**映射到详细设计**：

- **Objects（业务对象）** → 
  - 数据库表名（通常使用 object 的英文名或拼音）
  - 表字段（从 object 的属性推导字段名、类型、长度、约束）
  - 字段注释（从 object 的业务含义推导）
  - 唯一索引（从 object 的标识属性推导）

- **Edges（关系）** → 
  - **one-to-one**：在任一表中添加 `{object}_id BIGINT NOT NULL COMMENT '{对象名}ID'`
  - **one-to-many**：在"多"的一方添加 `{object}_id BIGINT NOT NULL COMMENT '{对象名}ID'`
  - **many-to-many**：创建关联表
    ```sql
    CREATE TABLE {object1}_{object2} (
      id BIGINT AUTO_INCREMENT PRIMARY KEY,
      {object1}_id BIGINT NOT NULL COMMENT '{对象1}ID',
      {object2}_id BIGINT NOT NULL COMMENT '{对象2}ID',
      created_by BIGINT NOT NULL COMMENT '创建人ID',
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
      updated_by BIGINT NOT NULL COMMENT '修改人ID',
      updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
      UNIQUE KEY uk_{object1}_{object2} ({object1}_id, {object2}_id)
    );
    ```

- **Rules（业务规则）** → 
  - 字段级约束（NOT NULL、UNIQUE、CHECK、DEFAULT）
  - 应用层验证逻辑（在接口设计中体现）
  - 业务不变量的实现方式

- **Behaviors（行为）** → 
  - API 接口定义（路径、方法、功能描述）
  - 请求体结构（从 behavior 的输入参数推导）
  - 响应体结构（从 behavior 的输出结果推导）
  - 接口校验逻辑（从 behavior 的前置条件推导）
  - 错误码定义（从 behavior 的异常情况推导）

- **SOP（标准操作流程）** → 
  - 业务流程接口的调用顺序
  - 接口权限设计（从 SOP 的参与者推导）
  - 流程状态管理（如需要状态机）
  - 异常处理和回滚策略
