# 项目技术规范参考

本文件提供应用设计阶段的项目技术约束，设计时必须在此范围内制定方案，不得违背。

## 项目概述

基于 Spring Boot 3.4.5 的企业级多模块 Maven 项目。

**技术栈**: JDK 17 | Spring Boot 3.4.5 | MyBatis 3.0.4 | MySQL 5.7 | Maven 3.9

**关键集成**: Apollo 配置中心 | RocketMQ | RDFA 定时任务 | LangChain4j（AI）

## Maven 模块结构

```
{project}-parent/
├── {project}-starter    # 应用启动模块
├── {project}-web        # Web 控制层 (Controller)
├── {project}-service    # 业务服务层 (Biz + Service)
├── {project}-dal        # 数据访问层 (Mapper + PO)
├── {project}-client     # 客户端 VO 定义
├── {project}-test       # 测试模块
└── rdfa-auth-spring-mvc  # 认证 SDK 适配
```

**约束**：仅在上述 Maven 管理的模块和测试模块中编写代码。

## 分层架构

**调用链**: `starter → controller → biz → service → dal`

| 层次 | 模块 | 包路径模板 | 类命名 | 返回类型 | 说明 |
|------|------|-----------|--------|---------|------|
| **Controller** | {project}-web | `com.enn.*.controller.*` | `XxxController` | `ServiceResult<VO>` | REST 接口，默认 POST |
| **Biz** | {project}-service | `com.enn.*.biz.*` | `XxxBizService` | `ServiceResult<VO>` | 业务编排、事务管理 |
| **Service** | {project}-service | `com.enn.*.service.*` | `XxxService` | `DTO` | 具体业务逻辑 |
| **DAL** | {project}-dal | `com.enn.*.repository.mapper` | `XxxMapper` | `PO` | 数据访问 |
| **Client** | {project}-client | `com.enn.*.client.*` | `XxxVO` | — | 视图对象定义 |

**架构关键原则**：
- Biz 和 Service 层**不需要 interface 接口**，直接使用实现类
- 数据转换方向：`PO → DTO → VO`；Controller/Biz 层禁止直接返回 PO/DTO
- 所有 VO/DTO/PO 使用 `@Data` 注解（Lombok）

## 启动类配置

启动类必须包含以下注解：
```java
@SpringBootApplication(scanBasePackages = {"top.rdfa", "com.enn"})
@EnableAspectJAutoProxy(proxyTargetClass = true)
@MapperScan("com.enn.**.repository.mapper")
@EnableApolloConfig
```

## Spring Boot 3.x 兼容性

设计时接口方法、过滤器等应使用 Jakarta 命名空间：

```java
// ✅ 正确 (Spring Boot 3.x)
import jakarta.annotation.Resource;
import jakarta.servlet.*;

// ❌ 错误 (Spring Boot 2.x，不可用)
import javax.annotation.Resource;
import javax.servlet.*;
```

## 认证与鉴权

- **每个 Controller 方法必须添加 `@Authorize` 注解**（来自 `top.rdfa.framework.auth.client.annotation`）
- 通过 `UnifyAuthContextHolder.getUserInfo()` 获取当前用户信息
- 所有保存/更新操作必须记录操作人：创建时设 `creator`，更新时设 `modifier`

## DAL 层规范

- Mapper 类必须添加 `@Mapper` 注解
- Mapper XML 放在 `resources/mapper/` 目录
- 时间字段统一使用 `java.util.Date`，不使用 `LocalDateTime`
- 禁止随意修改已有 SQL；如有指定 SQL 严格遵循

## 数据库设计约束

设计数据库表时必须遵守以下规范（与 SKILL.md 数据库规则配合使用）：

**字段类型**：
- 小数使用 `decimal`，禁止 `float`/`double`
- 时间字段使用 `datetime`
- 布尔/状态字段使用 `tinyint`，命名为 `is_xxx`

**审计字段（每张表必须包含）**：
- `create_by` varchar(64)：创建人（对应 Controller 中获取的 userId）
- `gmt_create` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP
- `update_by` varchar(64)：修改人
- `gmt_modified` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP

**禁止事项**：
- 禁止使用外键约束，关联完整性由应用层保证
- 禁止使用 MySQL 保留字作为字段名（如 `desc`、`range`、`match`）

## 单元测试规范

- 测试类放在测试模块 `src/test/java` 下，继承 `BaseTest`
- 类名 = 被测类名 + `Test`；方法名 = `test` + 方法名（驼峰）
- 数据库写操作必须加 `@Transactional`（测试后自动回滚）
- 不对引入的 Java Service 做 Mock，直接用 `@Resource` 注入

## 配置和环境

### 数据库配置
配置位置: `{project}-starter/src/main/resources/application.properties`

```properties
spring.datasource.url=jdbc:mysql://{host}:{port}/{database}
spring.datasource.username={username}
spring.datasource.password={password}
mybatis.mapper-locations=classpath:mapper/*.xml
```

### Apollo 配置中心
- **命名空间**: `application`, `RDFA.auth`, `RDFA.mq.producer`, `RDFA.mq.consumer`, `RDFA.timer`, `RDFA.redisson`

### 外部依赖 SDK

**认证 SDK**：
```xml
<dependency>
    <groupId>top.rdfa.auth</groupId>
    <artifactId>rdfa-auth-spring-mvc-starter</artifactId>
    <version>3.0.0-20221019-RELEASE</version>
</dependency>
```

### AI 集成
项目集成 LangChain4j，支持智能规划和分析功能。模板位于 `{project}-service/src/main/resources/ai/template/`

## 对应用设计的影响

在制定应用设计时，以下决策已被技术栈固定，**不需要**再作为可选方案提出：

| 设计维度 | 已确定方案 |
|---------|-----------|
| 框架 | Spring Boot 3.4.5，不可替换 |
| ORM | MyBatis，不可替换 |
| 数据库 | MySQL 5.7，不可替换 |
| 分层架构 | Controller → Biz → Service → DAL，不可替换 |
| 接口风格 | REST POST 为主，使用 `ServiceResult<VO>` 包装 |
| 消息队列 | RocketMQ（如需异步，优先考虑） |
| 配置管理 | Apollo 配置中心 |
| 认证 | RDFA 认证 SDK，`@Authorize` 注解 |

因此，应用设计的 2-3 种方案应聚焦于**业务逻辑的分解方式、模块划分、数据流设计**等层面，而非技术选型层面。
