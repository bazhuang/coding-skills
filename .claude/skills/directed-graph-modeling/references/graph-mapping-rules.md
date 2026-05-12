# 图映射规则

本文件定义了从运筹算法本体到 NebulaGraph 图数据库结构的确定性映射规则。

## 1. 对象类别处理

- `object_category: "node"` → 生成 TAG
- `object_category: "edge"` → 生成 EDGE

## 2. TAG 构造规则

### 2.1 命名

- `tag_name` = `object.table_schema.table_name`（完全一致，不做任何修改）
- `tag_type` = `object.object_type`（由本体定义的节点类型枚举）

### 2.2 VID 字段确定

**必须通过唯一索引获取**：

1. 如果 `object.table_schema.indexes` 包含唯一索引：
   - 单字段：直接使用该字段
   - 两个字段：选择其中不是版本过滤字段的字段
   - 两个以上字段：去掉版本过滤字段后，剩余字段按下划线连接
2. 如果没有唯一索引，则无法确定 VID，报错提示

### 2.3 字段列表

`fields` = `object.table_schema.fields[].name` 的完整列表

**版本过滤字段处理**：

- 如果 `fields` 中已包含版本过滤字段，保持原样
- 如果 `fields` 中不包含版本过滤字段，在字段列表开头添加版本过滤字段

### 2.4 字段类型转换

对 `table_schema.fields` 中的每个字段，应用以下 MySQL → NebulaGraph 类型转换：

| MySQL 类型模式 | NebulaGraph 类型 |
|---|---|
| `bigint(n)` / `bigint` | `int64` |
| `int(n)` / `int` | `int` |
| `tinyint(n)` / `tinyint` | `int` |
| `varchar(n)` / `varchar` / `text` | `string` |
| `decimal(m,n)` / `decimal` / `float` / `double` | `double` |
| `datetime` / `timestamp` | `datetime` |
| `date` | `date` |
| `boolean`| `bool` |

### 2.5 字段类型转换完成后即可，无需检测时间维度

## 3. EDGE 构造规则

### 3.1 命名

- `edge_name` = `object.table_schema.table_name`（完全一致）
- `edge_type` = `object.object_type`（由本体定义的边类型枚举）

### 3.2 端点解析

**src_tag / dst_tag 确定**：

1. 从 `object.edge_endpoints.from_objects` 获取源对象名称列表
2. 从 `object.edge_endpoints.to_objects` 获取目标对象名称列表
3. 在 `or_ontology` 的 `algorithm_objects.objects` 中查找匹配的对象
4. 使用匹配对象的 `table_schema.table_name` 作为 `src_tag` / `dst_tag`

**src_vid_field / dst_vid_field 确定**：

1. 优先从 `object.table_schema.foreign_keys` 中查找：
   - `ref_table` = `src_tag` 的外键字段 → `src_vid_field`
   - `ref_table` = `dst_tag` 的外键字段 → `dst_vid_field`
2. 如果没有 foreign_keys，从 `edge_endpoints.supporting_fields` 中推断
3. 如果仍然无法确定，根据字段命名模式推断：
   - 包含源 TAG 名称的字段 → src_vid_field
   - 包含目标 TAG 名称的字段 → dst_vid_field

### 3.3 rank_field

- 使用 `object.table_schema.primary_key[0]` 作为 rank_field

### 3.4 字段列表和类型转换

与 TAG 的规则相同（见 2.3 和 2.4）。

### 3.5 无额外配置，按 3.3 和 3.4 节规则处理即可

## 4. 结构化中间态格式（nebula_schema_meta.json）

### 4.1 整体结构

```json
{
  "space_name": "图空间名",
  "tags": [
    {
      "name": "表名",
      "tag_type": "节点类型",
      "vid_field": "VID字段名",
      "source_table": "源表名",
      "fields": ["所有属性字段列表"],
      "field_types": {
        "field_name": "nebula_type"
      },
      "indexes": ["版本过滤字段"]
    }
  ],
  "edges": [
    {
      "name": "边名称",
      "edge_type": "边类型",
      "src_tag": "源节点TAG名称",
      "dst_tag": "目标节点TAG名称",
      "src_vid_field": "源节点VID字段",
      "dst_vid_field": "目标节点VID字段",
      "rank_field": "排序字段",
      "source_table": "源表名",
      "fields": ["所有属性字段列表"],
      "field_types": {
        "field_name": "nebula_type"
      },
      "indexes": ["版本过滤字段"]
    }
  ]
}
```

### 4.2 字段取值来源

| 字段 | 取值来源 |
|------|---------|
| `name`（TAG/EDGE） | `table_schema.table_name` |
| `tag_type` / `edge_type` | `object_type` |
| `vid_field` | `table_schema.indexes` 唯一索引字段 |
| `src_vid_field` / `dst_vid_field` | 通过 `edge_endpoints` + `foreign_keys` 解析 |
| `source_table` | 与 `name` 一致 |
| `src_tag` / `dst_tag` | `edge_endpoints.from_objects` / `to_objects` 对应对象的 `table_name` |
| `fields` | `table_schema.fields[].name` 列表（确保包含版本过滤字段） |
| `field_types` | MySQL → NebulaGraph 类型转换结果 |
| `rank_field` | `primary_key[0]`|
| `indexes` | 必须包含版本过滤字段 |

## 5. DDL 渲染规则

### 5.1 TAG DDL 格式

```sql
CREATE TAG IF NOT EXISTS `tag_name` (
    `版本字段` int64 COMMENT '版本号',
    `field1` nebula_type COMMENT '字段描述（来源于 table_schema.fields[].desc）',
    `field2` nebula_type COMMENT '字段描述（来源于 table_schema.fields[].desc）'
) comment='table_type:tag_type';
```

注意：

- **不要生成 CREATE SPACE 语句**
- 如果原表已有版本过滤字段，不要在 DDL 中重复添加
- 字段顺序保持 `table_schema.fields` 的原始顺序
- 版本过滤字段始终放在第一个位置（如果原表没有）
- 每个字段的 `COMMENT` 使用 `table_schema.fields[].desc` 的值，不要使用空字符串或通用占位文本

### 5.2 TAG 索引

为每个 TAG 创建版本过滤字段索引：

```sql
CREATE TAG INDEX IF NOT EXISTS `tag_name_version_index` ON `tag_name` (`版本字段`);
```

### 5.3 EDGE DDL 格式

```sql
CREATE EDGE IF NOT EXISTS `edge_name` (
    `版本字段` int64 COMMENT '版本号',
    `field1` nebula_type COMMENT '字段描述'
) comment='table_type:edge_type';
```

注意：

- NebulaGraph EDGE 自动包含 src_vid 和 dst_vid，不需要在属性中显式定义

### 5.4 EDGE 索引

为每个 EDGE 创建版本过滤字段索引：

```sql
CREATE EDGE INDEX IF NOT EXISTS `edge_name_version_index` ON `edge_name` (`版本字段`);
```

## 6. 交叉引用校验

在输出最终结果前，必须完成以下校验：

### 6.1 TAG 列表完整性

- 每个 TAG 的 `name` 唯一
- 每个 TAG 的 `vid_field` 存在于 `fields` 列表中
- 每个 TAG 的 `fields` 包含版本过滤字段
- 每个 TAG 的 `field_types` 包含 `fields` 中的所有字段

### 6.2 EDGE 列表完整性

- 每个 EDGE 的 `name` 唯一
- 每个 EDGE 的 `src_vid_field` 和 `dst_vid_field` 存在于 `fields` 列表中
- 每个 EDGE 的 `fields` 包含版本过滤字段
- 每个 EDGE 的 `field_types` 包含 `fields` 中的所有字段

### 6.3 TAG-EDGE 关联

- 每个 EDGE 的 `src_tag` 存在于 TAG 列表中
- 每个 EDGE 的 `dst_tag` 存在于 TAG 列表中
- 如果某个 EDGE 的 `src_tag` 或 `dst_tag` 不存在，抛出错误并说明缺失的 TAG 名称

### 6.4 DDL 一致性

- DDL 中的 TAG 数量与 nebula_schema_meta.json 中的 TAG 数量一致
- DDL 中的 EDGE 数量与 nebula_schema_meta.json 中的 EDGE 数量一致
- DDL 中每个 TAG/EDGE 都有对应的版本过滤字段索引

## 7. DDL 执行代码生成规则

生成的 `ddl_executor.py` 必须满足以下要求：

### 7.1 参数设计

- 接受 `--ddl-path` 参数，默认值为 `nebula_schema.sql`
- 接受 `--config-path` 参数，默认值为 `nebula_config.json`

### 7.2 连接逻辑

- 从 `nebula_config` JSON 读取配置：
  - `cluster_servers` → 转换为 `[(host, port), ...]` 元组列表（原始数据是 `[{host, port}, ...]` 字典列表）
  - `space` → USE SPACE 语句的图空间
  - `username` / `password` → 认证信息
  - `pool_config` → 连接池参数

### 7.3 执行逻辑

- 读取 DDL 文件内容，逐行解析：
  1. 跳过注释行（`--` 开头）和空行
  2. 将有效行累积拼接，遇到分号表示一条完整语句
  3. 采用逐行累积法，避免直接按分号分割导致语法截断
- 逐条执行，输出每条语句的执行结果（成功或失败及错误信息）
- 遇到失败立即中断，返回非零退出码

### 7.4 禁止事项

- 不在代码中硬编码配置值
- 不执行 `nebula_schema.sql` 之外的任何 DDL
- 不访问或处理业务实例数据
