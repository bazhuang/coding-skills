# 架构设计文档模板

## 项目概述

- **项目名称**: 供需运筹仿真系统 - {模块名称}
- **文档版本**: V1.0
- **编写日期**: {date}
- **作者**: AI架构师助手
- **状态**: 草稿/评审中/已确认

---

## 1. 业务背景

### 1.1 业务场景

{业务场景描述}

### 1.2 核心目标

- 目标1
- 目标2
- 目标3

### 1.3 业务流程

1. 步骤1
2. 步骤2
3. ...

---

## 2. 功能需求

### 2.1 功能列表

| 序号 | 功能名称 | 功能描述 | 优先级 |
|------|---------|---------|--------|
| 1 | | | P0/P1/P2 |

### 2.2 详细功能说明

#### 2.2.1 功能1

**功能描述**: 
**业务规则**: 
**输入**: 
**输出**: 
**异常处理**: 

---

## 3. 非功能性需求

### 3.1 性能需求

- 响应时间: < X ms
- 并发用户: N
- 数据量: 支持X万条数据

### 3.2 安全需求

- 认证方式: RDFA统一认证
- 权限控制: 接口级权限

### 3.3 数据需求

- 数据存储: MySQL
- 数据保留周期: X年

---

## 4. 系统设计

### 4.1 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      Controller层                          │
│              com.enn.supply.opt.controller                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        Biz层                                │
│              com.enn.supply.opt.biz                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Service层                              │
│              com.enn.supply.opt.service                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        DAL层                                │
│         com.enn.supply.opt.repository.mapper               │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 模块划分

| 模块 | 职责 | 包路径 |
|------|------|--------|
| Controller | 接口定义、参数校验、认证鉴权 | `com.enn.supply.opt.controller.*` |
| Biz | 业务编排、事务管理 | `com.enn.supply.opt.biz.*` |
| Service | 业务逻辑实现 | `com.enn.supply.opt.service.*` |
| DAL | 数据访问 | `com.enn.supply.opt.repository.mapper` |

### 4.3 核心类设计

#### 4.3.1 Controller

```java
@RestController
@RequestMapping("/xxx")
public class XxxController {
    
    @Resource
    private XxxBizService xxxBizService;
    
    @PostMapping("/save")
    @Authorize
    public ServiceResult<Boolean> save(XxxVO vo) {
        UserInfo userInfo = UnifyAuthContextHolder.getUserInfo();
        return xxxBizService.save(vo, userInfo.getUsername());
    }
}
```

#### 4.3.2 BizService

```java
@Service
@Slf4j
public class XxxBizService {
    
    @Resource
    private XxxService xxxService;
    
    public ServiceResult<Boolean> save(XxxVO vo, String userId) {
        // 业务编排
        // 事务管理
        return xxxService.save(vo, userId);
    }
}
```

#### 4.3.3 Service

```java
@Service
@Slf4j
public class XxxService {
    
    @Resource
    private XxxMapper xxxMapper;
    
    @Transactional
    public Boolean save(XxxVO vo, String userId) {
        // 业务逻辑
        // PO转换
        // 数据持久化
        return true;
    }
}
```

### 4.4 数据库设计

#### 4.4.1 ER图

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Table_A    │────▶│   Table_B    │◀────│   Table_C    │
│              │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
```

#### 4.4.2 表结构

详见《详细设计文档》

---

## 5. 接口设计

### 5.1 接口列表

| 接口路径 | 请求方式 | 功能描述 |
|---------|---------|---------|
| /xxx/save | POST | 保存 |
| /xxx/update | POST | 更新 |
| /xxx/delete | POST | 删除 |
| /xxx/getById | POST | 按ID查询 |
| /xxx/list | POST | 列表查询 |

### 5.2 接口详情

#### 5.2.1 保存接口

**请求路径**: `/api/xxx/save`
**请求方式**: POST
**请求参数**:
```json
{
    "field1": "value1",
    "field2": "value2"
}
```
**响应参数**:
```json
{
    "success": true,
    "code": "0",
    "message": "success",
    "data": true
}
```

---

## 6. 风险评估

| 风险项 | 风险等级 | 应对措施 |
|--------|---------|---------|
| | 高/中/低 | |

---

## 7. 评审意见

| 评审人 | 评审日期 | 评审意见 |
|--------|---------|---------|
| | | |
