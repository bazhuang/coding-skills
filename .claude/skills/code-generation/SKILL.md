---
name: code-generation
description: "基于应用设计文档和数据库设计文档生成可运行的 Spring Boot 项目代码。当用户要求代码生成、实现功能、生成项目代码时使用。"
triggers:
  - 用户要求生成代码、实现功能、创建项目
  - app-design 完成后用户要求进入实现阶段
  - 用户要求将设计文档转化为可运行代码
parameters:
  project_path:
    description: 项目代码生成的目标路径
    required: false
---

# 代码生成

基于 `app-design` 产出的技术文档，生成可运行的 Spring Boot 项目代码。

## 技术规范约束

生成代码时**必须严格遵循** `../app-design/references/backend-tech-guidelines.md` 中的全部技术规范，不可妥协。无论本地环境配置如何，都不允许因"编译不通过"或"运行报错"而省略规范中的任何要求。

如果因环境问题导致编译/运行失败，应该生成环境配置说明文档指导用户配置，**而不是删除或降级代码中的规范要求**。

## 输入

| 输入文件 | 作用 |
|---------|------|
| `docs/app-design.md` | 架构决策、模块划分、接口设计、数据流、错误处理——代码生成的直接依据 |
| `docs/db-schema.md` | DDL、表结构、索引——PO/Mapper 生成的直接依据 |

**不读取** `docs/ontology_schema.json`（已被 app-design 消化）和 `docs/brd.md`（验收由下游验证 skill 负责）。

## 生成流程

### 步骤 0：探测已有代码

检查目标项目路径，确定生成模式：

**检测项**：
- 项目目录是否存在 Maven 模块结构（pom.xml）
- 是否存在已有的 src/main/java 目录
- 已有的 Mapper、Service、Controller 文件
- 已有的 pom.xml 中的依赖版本
- 已有的 base package 路径

**两种模式**：

| 模式 | 判断条件 | 行为 |
|------|---------|------|
| **全新项目** | 目标路径为空或无 Maven 结构 | 生成完整项目骨架：模块结构、启动类、配置文件、pom.xml |
| **增量开发** | 目标路径存在 Maven 项目 | 在已有结构上追加，不覆盖已有文件 |

**增量开发注意事项**：
- 新增的文件不与已有文件冲突
- 新增的 Mapper XML 追加而非覆盖已有 XML
- 新增的接口路径不与已有路径重复
- import 路径基于已有的 base package 推断

### 步骤 1：生成全局骨架（单代理，顺序执行）

这是"合同"阶段——所有类的全限定名、方法签名、import 路径在这里确定。后续子代理必须遵循此骨架，不允许修改。

**生成内容**：

```
1. 项目骨架（仅全新项目）
   ├── {project}-parent/pom.xml
   ├── {project}-starter/
   │   └── src/main/java/.../Application.java（启动类，含必要注解）
   │   └── src/main/resources/application.properties
   ├── {project}-web/
   ├── {project}-service/
   ├── {project}-dal/
   ├── {project}-client/
   └── {project}-test/

2. 所有 PO 类（字段定义、类型、@Data 注解、审计字段）
3. 所有 VO/DTO 类（字段定义、@Data 注解）
4. 所有 Controller 方法签名（空实现，只有 @Authorize 注解和方法头，返回 ServiceResult<VO>）
5. 所有 BizService 方法签名（空实现）
6. 所有 Service 方法签名（空实现）
7. 所有 Mapper 接口（空方法声明，@Mapper 注解）
8. 所有 Mapper XML 骨架（namespace + resultMap，无 SQL）
```

**骨架文件写入磁盘**，用户可随时查看。阶段 1 完成后直接进入阶段 2，不单独暂停等待用户确认。

### 步骤 2：并行填充实现（多子代理）

每个子代理负责 1 个本体对象的实现填充。子代理只填充方法体，不修改签名。因为骨架是确定的，子代理之间不会产生冲突，import 路径也不会出错。

**子代理任务模板**：

```
你负责实现 [对象名] 的完整代码。骨架已在步骤1生成，你只需填充方法体。

必须遵循的骨架文件：
- PO: [文件路径]
- Mapper: [文件路径]
- Mapper XML: [文件路径]
- Service: [文件路径]
- BizService: [文件路径]
- Controller: [文件路径]
- VO: [文件路径]

填充内容：
1. Mapper XML：补充所有 CRUD SQL（insert、selectById、selectList、updateById、deleteById）
2. Service：补充业务逻辑方法实现
3. BizService：补充编排逻辑、事务管理、约束校验
4. Controller：补充接口实现（调用 BizService，转换 VO）

铁律：不可修改方法签名、不可修改 import、不可修改类名。
```

**分组策略**：
- 按对象依赖关系分批：被依赖的对象先生成（如引用对象、核心对象），依赖别人的后生成（如实体对象、关系对象）
- 并行子代理的具体数量由 agent 根据实际情况自行决定
- 后批可以引用前批已确定的类和方法签名

### 步骤 3：可选测试代码生成

默认不生成单元测试代码。如果用户要求，可同步生成测试类骨架：

- 测试类放在 `{project}-test/src/test/java` 下，继承 `BaseTest`
- 类名 = 被测类名 + `Test`
- 方法签名和 `@Transactional` 注解就位，方法体留空或只写基本断言
- 用户可自行补充业务场景测试

测试代码为可选项，不影响后续 code-verification 的验证结论。

## 输出

| 产出物 | 说明 |
|--------|------|
| Spring Boot 项目代码 | 完整项目（全新）或增量代码（增量开发），所有文件已写入磁盘 |
| 测试代码（可选） | 仅在用户要求时生成，测试类骨架 |

## 关键原则

- **骨架优先**：先生成全局契约（类签名、方法签名），再并行填充实现——解决子代理协作的集成问题
- **技术规范不可妥协**：环境问题靠配置文档解决，不降级代码
- **不读业务原文**：只消费 app-design 的技术产出，不回头读 ontology_schema 或 brd
- **增量兼容**：自动探测已有代码，全新和增量两种模式无缝切换
- **可见性**：骨架写入磁盘，用户可随时查看，不单独打断流程
