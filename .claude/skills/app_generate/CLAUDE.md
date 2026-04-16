# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# 项目概述

**供需运筹仿真系统**（gas）- 一个基于Spring Boot 3.4.5的企业级多模块Maven项目，用于能源供需运筹和仿真计算。

**技术栈**: JDK 17 | Spring Boot 3.4.5 | MyBatis 3.0.4 | MySQL 5.7 | Maven 3.9

**关键集成**: Apollo配置中心 | RocketMQ | RDFA定时任务 | LangChain4j(AI)

# 约束
* 每次对话内容记录到`log/`目录下，基于当前时间作为文件名的依据。文件格式参照：`log_2026-01-05_11-30-20.md`
* 仅在Maven管理的模块和测试模块中编写代码

# 构建和运行
## 编译项目
```bash
mvn clean install
```

## 运行应用
**启动类**: `com.enn.supply.opt.starter.ApplicationRunner`

**必需JVM参数**:
```
-Dspring.profiles.active=fat,local
-DlogPath=.
-Denv=FAT
-Dapollo.meta=http://hcs-rdfa-cfg-config.fat.ennew.com
-Dapp.id=supply-opt
-Dlog4j.configurationFile=classpath:log4j2.xml
--add-opens=java.base/java.util=ALL-UNNAMED
--add-opens=java.base/java.lang=ALL-UNNAMED
```

## 运行测试
```bash
# 所有测试
mvn test

# 单个测试类
mvn test -Dtest=ClassNameTest

# 单个测试方法
mvn test -Dtest=ClassNameTest#testMethodName
```

# 架构设计

## Maven模块结构
```
supply-opt-parent/
├── supply-opt-starter    # 应用启动模块
├── supply-opt-web        # Web控制层 (Controller)
├── supply-opt-service    # 业务服务层 (Biz + Service)
├── supply-opt-dal        # 数据访问层 (Mapper + PO)
├── supply-opt-client     # 客户端VO定义
├── supply-opt-test       # 测试模块
└── rdfa-auth-spring-mvc  # 认证SDK适配
```

## 分层架构

**调用链**: `starter → controller → biz → service → dal`

### 各层职责和规范

| 层次 | 模块 | 包路径模板 | 类命名 | 返回类型 | 说明 |
|------|------|-----------|--------|---------|------|
| **Controller** | supply-opt-web | `com.enn.supply.opt.controller.*` | `XxxController` | `ServiceResult<VO>` | REST接口，默认POST请求 |
| **Biz** | supply-opt-service | `com.enn.supply.opt.biz.*` | `XxxBizService` | `ServiceResult<VO>` | 业务编排、事务管理 |
| **Service** | supply-opt-service | `com.enn.supply.opt.service.match.*` | `XxxService` | `DTO` | 具体业务逻辑 |
| **DAL** | supply-opt-dal | `com.enn.supply.opt.match.repository.mapper` | `XxxMapper` | `PO` | 数据访问 |
| **Client** | supply-opt-client | `com.enn.supply.opt.client.*` | `XxxVO` | - | 视图对象定义 |

**关键原则**:
- Biz和Service层**不需要interface接口**，直接使用实现类
- 数据转换：`PO → DTO → VO`，Controller/Biz层禁止直接返回PO/DTO
- 所有VO/DTO/PO使用`@Data`注解（Lombok）

## 启动类配置

`ApplicationRunner`必须包含以下注解：
```java
@SpringBootApplication(scanBasePackages = {"top.rdfa", "com.enn"})
@EnableAspectJAutoProxy(proxyTargetClass = true)
@MapperScan("com.enn.supply.opt.**.repository.mapper")
@EnableApolloConfig
```

## DAL层规范

- **Mapper类**: 必须添加`@Mapper`注解
- **Mapper XML**: 放在`resources/mapper/`目录
- **时间字段**: 统一使用`java.util.Date`，不使用LocalDateTime等其他时间类
- **SQL**: 如有指定SQL，严格遵循，不要随意修改

# Spring Boot 3.x 兼容性

**关键变更**（与Spring Boot 2.x不同）：

```java
// ❌ 错误 (Spring Boot 2.x)
import javax.annotation.Resource;
import javax.servlet.*;

// ✅ 正确 (Spring Boot 3.x)
import jakarta.annotation.Resource;
import jakarta.servlet.*;
```

严格按照Spring Boot 3.4.5的API编写代码。

# 认证和鉴权

## Controller层认证

**每个Controller方法必须添加`@Authorize`注解**:

```java
import top.rdfa.framework.auth.client.annotation.Authorize;
import top.rdfa.framework.auth.client.UnifyAuthContextHolder;
import top.rdfa.framework.auth.facade.entity.UserInfo;

@RestController
public class XxxController {

    @Resource
    private XxxBizService xxxBizService;

    @PostMapping("/xxx/save")
    @Authorize  // 必需
    public ServiceResult<Boolean> save(XxxVO vo) {
        // 获取当前用户ID
        UserInfo userInfo = UnifyAuthContextHolder.getUserInfo();
        String userId = userInfo.getUsername();

        // 传递给Biz层，用于设置creator/modifier
        return xxxBizService.save(vo, userId);
    }
}
```

## 操作人记录

所有保存/更新操作必须记录操作人：
- **创建**: 设置`creator`字段为当前userId
- **更新**: 设置`modifier`字段为当前userId

# 单元测试规范

## 测试类结构

**位置**: `supply-opt-test`模块 → `src/test/java`

**基本规范**:
- 继承`BaseTest`
- 类名: 被测类名 + `Test`后缀
- 方法名: `test` + 方法名（驼峰）
- 数据库写操作: 必须添加`@Transactional`注解（测试后自动回滚）
- 不要对引入的Java Service做Mock处理，直接采用@Resource 注解引入即可

**示例**:
```java
package com.enn.supply.opt.match.repository.mapper;

import com.ennew.supply.opt.base.BaseTest;
import jakarta.annotation.Resource;
import org.junit.jupiter.api.Test;
import org.springframework.transaction.annotation.Transactional;

class MonthlyTransportPoolMapperTest extends BaseTest {

    @Resource
    private MonthlyTransportPoolMapper mapper;

    @Test
    @Transactional  // 数据库写操作必需
    void testInsert() {
        // 测试逻辑
    }
}
```

# 配置和环境

## 数据库配置
配置位置: `supply-opt-starter/src/main/resources/application.properties`

```properties
spring.datasource.url=jdbc:mysql://10.203.125.221:3306/supply_opt
spring.datasource.username=eone_rw
spring.datasource.password=AK#fgljStmJRYD4FU
mybatis.mapper-locations=classpath:mapper/*.xml
```

## Apollo配置中心
- **App ID**: `supply-opt`
- **命名空间**: `application`, `RDFA.auth`, `RDFA.mq.producer`, `RDFA.mq.consumer`, `RDFA.timer`, `RDFA.redisson`

## 外部依赖SDK

### 认证SDK
```xml
<dependency>
    <groupId>top.rdfa.auth</groupId>
    <artifactId>rdfa-auth-spring-mvc-starter</artifactId>
    <version>3.0.0-20221019-RELEASE</version>
</dependency>
```

### AI集成
项目集成LangChain4j，支持智能规划和分析功能。模板位于`supply-opt-service/src/main/resources/ai/template/`
