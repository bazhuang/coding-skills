# 架构设计文档模板（通用版）

## 项目概述

- **项目名称**: {project_name} - {module_name}
- **文档版本**: V1.0
- **编写日期**: {date}
- **作者**: {author}
- **状态**: 草稿/评审中/已确认

---

## 1. 业务背景

### 1.1 业务场景

{从ontology.biz或用户输入提取}

### 1.2 核心目标

- 目标1
- 目标2
- 目标3

### 1.3 业务流程

基于ontology.sop自动生成：

{自动生成的流程步骤}

---

## 2. 功能需求

### 2.1 功能列表

基于ontology.behaviors自动生成：

| 序号 | 功能名称 | 功能描述 | 优先级 |
|------|---------|---------|--------|
| {n} | {behavior_description} | {behavior_type} | P0/P1/P2 |

### 2.2 详细功能说明

{基于ontology.behaviors详细展开}

---

## 3. 非功能性需求

### 3.1 性能需求

- 响应时间: < X ms
- 并发用户: N
- 数据量: 支持X万条数据

### 3.2 安全需求

- 认证方式: 统一认证
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
│              {base_package}.controller                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        Biz层                                │
│              {base_package}.biz                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Service层                              │
│              {base_package}.service                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        DAL层                                │
│              {base_package}.dal.mapper                      │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 模块划分

| 模块 | 职责 | 包路径 |
|------|------|--------|
| Controller | 接口定义、参数校验、认证鉴权 | `{base_package}.controller.*` |
| Biz | 业务编排、事务管理 | `{base_package}.biz.*` |
| Service | 业务逻辑实现 | `{base_package}.service.*` |
| DAL | 数据访问 | `{base_package}.dal.mapper` |

### 4.3 核心类设计

#### 4.3.1 Controller

```java
@RestController
@RequestMapping("/{module}")
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
{自动生成的ER图}

表清单：
{表名} - {表描述}
```

#### 4.4.2 表结构

详见《详细设计文档》

---

## 5. 接口设计

### 5.1 接口列表

基于ontology.behaviors自动生成CRUD接口：

| 接口路径 | 请求方式 | 功能描述 |
|---------|---------|---------|
| /{module}/save | POST | 创建 |
| /{module}/update | POST | 更新 |
| /{module}/delete | POST | 删除 |
| /{module}/getById | POST | 按ID查询 |
| /{module}/list | POST | 列表查询 |

### 5.2 接口详情

#### 5.2.1 保存接口

**请求路径**: `POST /api/{module}/save`
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
| 数据量增长 | 中 | 预留分表字段 |
| 并发压力 | 中 | 读写分离设计 |

---

## 7. 评审意见

| 评审人 | 评审日期 | 评审意见 |
|--------|---------|---------|
| | | |
