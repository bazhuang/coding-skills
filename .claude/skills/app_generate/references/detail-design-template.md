# 详细设计文档模板（通用版）

## 项目概述

- **项目名称**: {project_name} - {module_name}
- **文档版本**: V1.0
- **编写日期**: {date}
- **作者**: {author}
- **状态**: 草稿/评审中/已确认

---

## 1. 数据库设计

### 1.1 数据库表清单

基于ontology.objects自动生成：

| 序号 | 表名 | 表中文名 | 说明 |
|------|------|---------|------|
| {n} | {table_name} | {object_name} | {object_type} |

### 1.2 表结构设计

{基于ontology.objects动态生成每个表的详细结构}

#### 1.2.1 {table_name}

**表说明**: {table_comment}

| 序号 | 字段名 | 字段中文名 | 数据类型 | 是否主键 | 是否为空 | 默认值 | 说明 |
|------|--------|-----------|---------|---------|---------|-------|------|
| 1 | id | 主键ID | BIGINT(20) | PK | N | | 自增主键 |
| 2 | biz_id | 业务唯一标识 | VARCHAR(64) | | N | | 唯一约束 |

**索引设计**:

| 索引名称 | 索引类型 | 索引字段 | 说明 |
|---------|---------|---------|------|
| uk_biz_id | UNIQUE | biz_id | 唯一索引 |

**建表SQL**:
```sql
CREATE TABLE `{table_name}` (
    `id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `biz_id` VARCHAR(64) NOT NULL COMMENT '业务唯一标识',
    {business_fields}
    `create_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '创建人',
    `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_by` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '修改人',
    `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_biz_id` (`biz_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{table_comment}';
```

---

## 2. Java类设计

### 2.1 类清单

基于ontology.objects和layers动态生成：

| 序号 | 类名 | 类型 | 包路径 | 说明 |
|------|------|------|--------|------|
| {n} | XxxController | Controller | {base_package}.controller | 接口层 |
| {n} | XxxBizService | Biz | {base_package}.biz | 业务编排层 |
| {n} | XxxService | Service | {base_package}.service | 业务逻辑层 |
| {n} | XxxMapper | Mapper | {base_package}.dal.mapper | 数据访问层 |
| {n} | XxxPO | PO | {base_package}.dal.po | 数据实体 |
| {n} | XxxDTO | DTO | {base_package}.service.dto | 数据传输对象 |
| {n} | XxxVO | VO | {base_package}.client.vo | 视图对象 |

### 2.2 详细类设计

#### 2.2.1 PO类

**文件位置**: `{module}-dal/src/main/java/{base_package}/dal/po/XxxPO.java`

```java
package {base_package}.dal.po;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.util.Date;

@Data
@TableName("{table_name}")
public class XxxPO {
    
    @TableId(type = IdType.AUTO)
    private Long id;
    
    private String bizId;
    
    // 业务字段...
    
    private String createBy;
    
    private Date createTime;
    
    private String updateBy;
    
    private Date updateTime;
}
```

#### 2.2.2 DTO类

**文件位置**: `{module}-service/src/main/java/{base_package}/service/dto/XxxDTO.java`

```java
package {base_package}.service.dto;

import lombok.Data;

@Data
public class XxxDTO {
    
    private Long id;
    
    private String bizId;
    
    // 业务字段...
}
```

#### 2.2.3 VO类

**文件位置**: `{module}-client/src/main/java/{base_package}/client/vo/XxxVO.java`

```java
package {base_package}.client.vo;

import lombok.Data;
import java.io.Serializable;

@Data
public class XxxVO implements Serializable {
    
    private static final long serialVersionUID = 1L;
    
    private String bizId;
    
    // 业务字段...
}
```

#### 2.2.4 Mapper接口

**文件位置**: `{module}-dal/src/main/java/{base_package}/dal/mapper/XxxMapper.java`

```java
package {base_package}.dal.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import {base_package}.dal.po.XxxPO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import java.util.List;

@Mapper
public interface XxxMapper extends BaseMapper<XxxPO> {
    
    // 自定义方法...
}
```

#### 2.2.5 Mapper XML

**文件位置**: `{module}-dal/src/main/resources/mapper/XxxMapper.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" 
    "http://mybatis.org/dtd/mybatis-3-mapper.dtd">

<mapper namespace="{base_package}.dal.mapper.XxxMapper">

    <resultMap id="BaseResultMap" type="{base_package}.dal.po.XxxPO">
        <!-- 映射配置 -->
    </resultMap>

    <sql id="Base_Column_List">
        <!-- 基础字段 -->
    </sql>

    <!-- 自定义SQL -->
    
</mapper>
```

#### 2.2.6 Service类

**文件位置**: `{module}-service/src/main/java/{base_package}/service/XxxService.java`

```java
package {base_package}.service;

import {base_package}.client.vo.XxxVO;
import {base_package}.dal.mapper.XxxMapper;
import {base_package}.dal.po.XxxPO;
import {base_package}.service.dto.XxxDTO;
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

**文件位置**: `{module}-service/src/main/java/{base_package}/biz/XxxBizService.java`

```java
package {base_package}.biz;

import {base_package}.client.vo.XxxVO;
import {base_package}.service.XxxService;
import {base_package}.service.result.ServiceResult;
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

**文件位置**: `{module}-web/src/main/java/{base_package}/controller/XxxController.java`

```java
package {base_package}.controller;

import {base_package}.biz.XxxBizService;
import {base_package}.client.vo.XxxVO;
import {base_package}.service.result.ServiceResult;
import top.rdfa.framework.auth.client.UnifyAuthContextHolder;
import top.rdfa.framework.auth.client.annotation.Authorize;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;
import jakarta.annotation.Resource;

@Slf4j
@RestController
@RequestMapping("/{module}")
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

基于ontology.behaviors自动生成接口文档。

### 3.1 保存接口

**请求路径**: `POST /api/{module}/save`

**请求参数**:
```json
{
    "bizId": "xxx",
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

**请求路径**: `POST /api/{module}/getById`

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
        "bizId": "xxx"
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
| biz_id | 业务唯一标识 |
| PO | Persistent Object 持久化对象 |
| DTO | Data Transfer Object 数据传输对象 |
| VO | View Object 视图对象 |

### 6.2 参考文档

- 《技术规范文档》
- 《架构设计文档》
- Ontology定义文件
