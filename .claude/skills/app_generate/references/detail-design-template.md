# 详细设计文档模板

## 项目概述

- **项目名称**: 供需运筹仿真系统 - {模块名称}
- **文档版本**: V1.0
- **编写日期**: {date}
- **作者**: AI架构师助手
- **状态**: 草稿/评审中/已确认

---

## 1. 数据库设计

### 1.1 数据库表清单

| 序号 | 表名 | 表中文名 | 说明 |
|------|------|---------|------|
| 1 | mop_monthly_plan | 月度经营计划 | 核心对象 |
| 2 | rp_resource_pool | 资源池 | 核心对象 |
| ... | | | |

### 1.2 表结构设计

#### 1.2.1 {表名}

**表说明**: {表中文名}

| 序号 | 字段名 | 字段中文名 | 数据类型 | 是否主键 | 是否为空 | 默认值 | 说明 |
|------|--------|-----------|---------|---------|---------|-------|------|
| 1 | id | 主键ID | BIGINT(20) | PK | N | | 自增主键 |
| 2 | cvcu_id | 客创唯一标识 | VARCHAR(64) | | N | | 唯一约束 |
| ... | | | | | | | |

**索引设计**:

| 索引名称 | 索引类型 | 索引字段 | 说明 |
|---------|---------|---------|------|
| idx_xxx | NORMAL | field1,field2 | 复合索引 |
| uk_cvcu_id | UNIQUE | cvcu_id | 唯一索引 |

**建表SQL**:
```sql
CREATE TABLE `{table_name}` (
    ...
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{table_comment}';
```

---

## 2. Java类设计

### 2.1 类清单

| 序号 | 类名 | 类型 | 包路径 | 说明 |
|------|------|------|--------|------|
| 1 | XxxController | Controller | com.enn.supply.opt.controller | 接口层 |
| 2 | XxxBizService | Biz | com.enn.supply.opt.biz | 业务编排层 |
| 3 | XxxService | Service | com.enn.supply.opt.service | 业务逻辑层 |
| 4 | XxxMapper | Mapper | com.enn.supply.opt.repository.mapper | 数据访问层 |
| 5 | XxxPO | PO | com.enn.supply.opt.repository.po | 数据实体 |
| 6 | XxxDTO | DTO | com.enn.supply.opt.service.dto | 数据传输对象 |
| 7 | XxxVO | VO | com.enn.supply.opt.client.vo | 视图对象 |

### 2.2 详细类设计

#### 2.2.1 PO类

**文件位置**: `supply-opt-dal/src/main/java/com/enn/supply/opt/repository/po/XxxPO.java`

```java
package com.enn.supply.opt.repository.po;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.util.Date;

@Data
@TableName("xxx_table")
public class XxxPO {
    
    @TableId(type = IdType.AUTO)
    private Long id;
    
    private String cvcuId;
    
    // 业务字段...
    
    private String createBy;
    
    private Date createTime;
    
    private String updateBy;
    
    private Date updateTime;
}
```

#### 2.2.2 DTO类

**文件位置**: `supply-opt-service/src/main/java/com/enn/supply/opt/service/dto/XxxDTO.java`

```java
package com.enn.supply.opt.service.dto;

import lombok.Data;

@Data
public class XxxDTO {
    
    private Long id;
    
    private String cvcuId;
    
    // 业务字段...
}
```

#### 2.2.3 VO类

**文件位置**: `supply-opt-client/src/main/java/com/enn/supply/opt/client/vo/XxxVO.java`

```java
package com.enn.supply.opt.client.vo;

import lombok.Data;
import java.io.Serializable;

@Data
public class XxxVO implements Serializable {
    
    private static final long serialVersionUID = 1L;
    
    private String cvcuId;
    
    // 业务字段...
}
```

#### 2.2.4 Mapper接口

**文件位置**: `supply-opt-dal/src/main/java/com/enn/supply/opt/repository/mapper/XxxMapper.java`

```java
package com.enn.supply.opt.repository.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.enn.supply.opt.repository.po.XxxPO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import java.util.List;

@Mapper
public interface XxxMapper extends BaseMapper<XxxPO> {
    
    // 自定义方法...
}
```

#### 2.2.5 Mapper XML

**文件位置**: `supply-opt-dal/src/main/resources/mapper/XxxMapper.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" 
    "http://mybatis.org/dtd/mybatis-3-mapper.dtd">

<mapper namespace="com.enn.supply.opt.repository.mapper.XxxMapper">

    <resultMap id="BaseResultMap" type="com.enn.supply.opt.repository.po.XxxPO">
        <!-- 映射配置 -->
    </resultMap>

    <sql id="Base_Column_List">
        <!-- 基础字段 -->
    </sql>

    <!-- 自定义SQL -->
    
</mapper>
```

#### 2.2.6 Service类

**文件位置**: `supply-opt-service/src/main/java/com/enn/supply/opt/service/XxxService.java`

```java
package com.enn.supply.opt.service;

import com.enn.supply.opt.client.vo.XxxVO;
import com.enn.supply.opt.repository.mapper.XxxMapper;
import com.enn.supply.opt.repository.po.XxxPO;
import com.enn.supply.opt.service.dto.XxxDTO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import jakarta.annotation.Resource;
import java.util.List;

@Slf4j
@Service
public class XxxService {
    
    @Resource
    private XxxMapper xxxMapper;
    
    @Transactional(rollbackFor = Exception.class)
    public Boolean save(XxxVO vo, String userId) {
        // 1. 参数校验
        // 2. PO转换
        // 3. 数据持久化
        // 4. 返回结果
        return true;
    }
    
    public XxxDTO getById(Long id) {
        XxxPO po = xxxMapper.selectById(id);
        return convertToDTO(po);
    }
    
    public List<XxxDTO> list(XxxDTO dto) {
        // 查询逻辑
        return null;
    }
    
    private XxxDTO convertToDTO(XxxPO po) {
        if (po == null) {
            return null;
        }
        XxxDTO dto = new XxxDTO();
        // 属性复制
        return dto;
    }
}
```

#### 2.2.7 BizService类

**文件位置**: `supply-opt-service/src/main/java/com/enn/supply/opt/biz/XxxBizService.java`

```java
package com.enn.supply.opt.biz;

import com.enn.supply.opt.client.vo.XxxVO;
import com.enn.supply.opt.service.XxxService;
import com.enn.supply.opt.service.result.ServiceResult;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import jakarta.annotation.Resource;

@Slf4j
@Service
public class XxxBizService {
    
    @Resource
    private XxxService xxxService;
    
    public ServiceResult<Boolean> save(XxxVO vo, String userId) {
        try {
            Boolean result = xxxService.save(vo, userId);
            return ServiceResult.success(result);
        } catch (Exception e) {
            log.error("保存失败", e);
            return ServiceResult.fail(e.getMessage());
        }
    }
}
```

#### 2.2.8 Controller类

**文件位置**: `supply-opt-web/src/main/java/com/enn/supply/opt/controller/XxxController.java`

```java
package com.enn.supply.opt.controller;

import com.enn.supply.opt.biz.XxxBizService;
import com.enn.supply.opt.client.vo.XxxVO;
import com.enn.supply.opt.service.result.ServiceResult;
import top.rdfa.framework.auth.client.UnifyAuthContextHolder;
import top.rdfa.framework.auth.client.annotation.Authorize;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;
import jakarta.annotation.Resource;

@Slf4j
@RestController
@RequestMapping("/xxx")
public class XxxController {
    
    @Resource
    private XxxBizService xxxBizService;
    
    @PostMapping("/save")
    @Authorize
    public ServiceResult<Boolean> save(@RequestBody XxxVO vo) {
        String userId = UnifyAuthContextHolder.getUserInfo().getUsername();
        return xxxBizService.save(vo, userId);
    }
    
    @PostMapping("/getById")
    @Authorize
    public ServiceResult<XxxVO> getById(@RequestParam Long id) {
        return xxxBizService.getById(id);
    }
    
    @PostMapping("/list")
    @Authorize
    public ServiceResult<List<XxxVO>> list(@RequestBody XxxVO vo) {
        return xxxBizService.list(vo);
    }
}
```

---

## 3. 接口设计

### 3.1 保存接口

**请求路径**: `POST /api/xxx/save`

**请求参数**:
```json
{
    "cvcuId": "xxx",
    "field1": "value1"
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

### 3.2 查询接口

**请求路径**: `POST /api/xxx/getById`

**请求参数**:
```
id: Long
```

**响应参数**:
```json
{
    "success": true,
    "code": "0",
    "message": "success",
    "data": {
        "id": 1,
        "cvcuId": "xxx"
    }
}
```

---

## 4. 异常处理

### 4.1 业务异常

| 异常码 | 异常描述 | 处理方式 |
|--------|---------|---------|
| XXX001 | 参数校验失败 | 返回错误信息 |
| XXX002 | 数据不存在 | 返回错误信息 |

### 4.2 系统异常

| 异常类型 | 处理方式 |
|---------|---------|
| 数据库异常 | 记录日志，返回通用错误 |
| 业务异常 | Biz层捕获，返回业务错误 |

---

## 5. 测试用例

### 5.1 单元测试

| 用例编号 | 用例名称 | 测试步骤 | 预期结果 |
|---------|---------|---------|---------|
| TC001 | 保存成功 | 传入有效参数 | 返回true |
| TC002 | 参数校验失败 | 传入无效参数 | 返回错误信息 |

### 5.2 集成测试

| 用例编号 | 用例名称 | 测试步骤 | 预期结果 |
|---------|---------|---------|---------|
| IT001 | 完整流程 | 增删改查全流程 | 功能正常 |

---

## 6. 附录

### 6.1 术语表

| 术语 | 说明 |
|------|------|
| cvcu_id | 客创唯一标识 |
| PO | Persistent Object 持久化对象 |
| DTO | Data Transfer Object 数据传输对象 |
| VO | View Object 视图对象 |

### 6.2 参考文档

- 《技术规范文档》
- 《架构设计文档》
