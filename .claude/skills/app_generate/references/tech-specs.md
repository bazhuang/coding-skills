# 天然气供需匹配运筹项目 - 技术规范

## 项目概述

**项目名称**: 供需运筹仿真系统（gas）
**技术栈**: JDK 17 | Spring Boot 3.4.5 | MyBatis 3.0.4 | MySQL 5.7 | Maven 3.9
**关键集成**: Apollo配置中心 | RocketMQ | RDFA定时任务 | LangChain4j(AI)

## Maven模块结构

```
supply-opt-parent/
├── supply-opt-starter    # 应用启动模块
├── supply-opt-web        # Web控制层 (Controller)
├── supply-opt-service    # 业务服务层 (Biz + Service)
├── supply-opt-dal        # 数据访问层 (Mapper + PO)
├── supply-opt-client     # 客户端VO定义
└── supply-opt-test       # 测试模块
```

## 分层架构

**调用链**: `starter → controller → biz → service → dal`

| 层次 | 模块 | 包路径模板 | 类命名 | 返回类型 |
|------|------|-----------|--------|----------|
| Controller | supply-opt-web | `com.enn.supply.opt.controller.*` | `XxxController` | `ServiceResult<VO>` |
| Biz | supply-opt-service | `com.enn.supply.opt.biz.*` | `XxxBizService` | `ServiceResult<VO>` |
| Service | supply-opt-service | `com.enn.supply.opt.service.match.*` | `XxxService` | `DTO` |
| DAL | supply-opt-dal | `com.enn.supply.opt.match.repository.mapper` | `XxxMapper` | `PO` |
| Client | supply-opt-client | `com.enn.supply.opt.client.*` | `XxxVO` | - |

## 关键原则

- Biz和Service层**不需要interface接口**，直接使用实现类
- 数据转换：`PO → DTO → VO`，Controller/Biz层禁止直接返回PO/DTO
- 所有VO/DTO/PO使用`@Data`注解（Lombok）

## DAL层规范

- **Mapper类**: 必须添加`@Mapper`注解
- **Mapper XML**: 放在`resources/mapper/`目录
- **时间字段**: 统一使用`java.util.Date`
- **SQL**: 如有指定SQL，严格遵循，不要随意修改

## Spring Boot 3.x 兼容性

```java
// ❌ 错误 (Spring Boot 2.x)
import javax.annotation.Resource;

// ✅ 正确 (Spring Boot 3.x)
import jakarta.annotation.Resource;
```

## 认证和鉴权

**Controller方法必须添加`@Authorize`注解**

```java
import top.rdfa.framework.auth.client.annotation.Authorize;
import top.rdfa.framework.auth.client.UnifyAuthContextHolder;

@PostMapping("/xxx/save")
@Authorize
public ServiceResult<Boolean> save(XxxVO vo) {
    UserInfo userInfo = UnifyAuthContextHolder.getUserInfo();
    String userId = userInfo.getUsername();
    return xxxBizService.save(vo, userId);
}
```

## 数据库配置

```properties
spring.datasource.url=jdbc:mysql://{host}:3306/supply_opt
spring.datasource.username={username}
spring.datasource.password={password}
mybatis.mapper-locations=classpath:mapper/*.xml
```

## 表设计通用字段

| 字段 | 类型 | 说明 |
|------|------|------|
| cvcu_id | VARCHAR(64) | 客创唯一标识 |
| create_by | VARCHAR(64) | 创建人 |
| create_time | DATETIME | 创建时间 |
| update_by | VARCHAR(64) | 修改人 |
| update_time | DATETIME | 修改时间 |
| start_date | VARCHAR(10) | 开始日期 |
| end_date | VARCHAR(10) | 结束日期 |

## 业务逻辑概述

### 核心业务流程

1. 制定月度经营计划（目标、策略）
2. 录入资源池数据（合同量、价格、照付不议条款）
3. 录入需求池数据（客户需求、优先级、灵活性）
4. 录入传输运力池数据（管道能力、保底量、运输成本）
5. 构建运筹优化模型（目标函数+约束条件）
6. 求解优化模型（算法计算）
7. 生成需供匹配结果（资源分配+运输路径+客户供气量）
8. 输出调度方案供执行

### 价值计算公式

```
利润 = 销售收入 
     - 资源成本 
     - 运力成本 
     - 资源照付不议成本 
     - 需求缺口成本 
     - 运力低于最小量成本
```

### 关键约束

- **需求侧**：实际供气量 ≤ 计划需求量，必须供气客户优先满足
- **资源侧**：使用量 ≤ 合同可用量，未达最低提气量产生照付不议成本
- **运力侧**：传输量 ≤ 管道设计能力，未达保底量产生保底成本
