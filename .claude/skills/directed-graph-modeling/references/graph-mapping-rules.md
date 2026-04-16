# 图映射规则

本文件定义了从算法本体模型到 NebulaGraph 图数据库结构的确定性映射规则。

## 1. 对象类别处理

- `object_category: "node"` → 生成 TAG
- `object_category: "edge"` → 生成 EDGE

## 2. TAG 构造规则

### 2.1 命名

- `tag_name` = `object.table_schema.table_name`（完全一致，不做任何修改）
- `tag_type` = `object.object_type`（枚举值：supply_node, demand_node, passthrough_node, processor_node, storage_node）

### 2.2 VID 字段确定

**优先级规则**：

1. 如果 `object.table_schema.indexes` 包含唯一索引且为单字段，使用该字段
2. 如果唯一索引是复合键，选择其中不是 `version_id` 的字段

### 2.3 字段列表

`fields` = `object.table_schema.fields[].name` 的完整列表

**version_id 处理**：

- 如果 `fields` 中已包含 `version_id`，保持原样
- 如果 `fields` 中不包含 `version_id`，在字段列表开头添加 `version_id`

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
| `boolean` / `tinyint(1)` | `bool` |

### 2.5 DDL 格式

```sql
CREATE TAG IF NOT EXISTS `tag_name` (
    `version_id` int64 COMMENT '版本ID',
    `field1` nebula_type COMMENT '字段描述',
    `field2` nebula_type COMMENT '字段描述'
) comment='table_type:tag_type';
```

注意：

- 如果 `version_id` 已存在于原字段中，不要在 DDL 中重复添加
- 字段顺序保持 `table_schema.fields` 的原始顺序
- `version_id` 始终放在第一个位置（如果原表没有）

### 2.6 TAG 索引

为每个 TAG 创建 version_id 索引：

```sql
CREATE TAG INDEX IF NOT EXISTS `tag_name_version_id_index` ON `tag_name` (`version_id`);
```

## 3. EDGE 构造规则

### 3.1 命名

- `edge_name` = `object.table_schema.table_name`（完全一致）
- `edge_type` = `object.object_type`（枚举值：transport, link）

### 3.2 端点解析

**src_tag / dst_tag 确定**：

1. 从 `object.edge_endpoints.from_objects` 获取源对象名称列表
2. 从 `object.edge_endpoints.to_objects` 获取目标对象名称列表
3. 在算法本体模型的 `algorithm_objects.objects` 中查找匹配的对象
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

- 如果 `object.table_schema` 中存在排序字段（如 sort_order, sequence, priority），使用它
- 否则设为 `null`

### 3.4 字段列表和类型转换

与 TAG 的规则相同（见 2.3 和 2.4）。

### 3.5 DDL 格式

```sql
CREATE EDGE IF NOT EXISTS `edge_name` (
    `version_id` int64 COMMENT '版本ID',
    `field1` nebula_type COMMENT '字段描述',
    `src_field` string COMMENT '源节点ID',
    `dst_field` string COMMENT '目标节点ID'
) comment='table_type:edge_type';
```

注意：

- NebulaGraph EDGE 自动包含 src_vid 和 dst_vid，不需要在属性中显式定义
- 但 src_vid_field 和 dst_vid_field 必须在 data_mapping.json 中配置

### 3.6 EDGE 索引

为每个 EDGE 创建 version_id 索引：

```sql
CREATE EDGE INDEX IF NOT EXISTS `edge_name_version_id_index` ON `edge_name` (`version_id`);
```

## 4. 时间维度检测

### 4.1 时间字段识别

遍历 `table_schema.fields`，匹配以下模式：

**开始时间字段**：

- `start_*`, `begin_*`, `*_start_date`, `*_start_time`
- 常见字段名：`start_date`, `begin_date`, `start_time`

**结束时间字段**：

- `end_*`, `finish_*`, `*_end_date`, `*_end_time`
- 常见字段名：`end_date`, `finish_date`, `end_time`

### 4.2 量字段识别

遍历 `table_schema.fields`，匹配以下模式：

- `*_quantity`, `*_amount`, `*_volume`, `*_count`, `*_num`
- `quantity`, `amount`, `volume`, `count`, `num`（单独出现）
- `*_qty`, `*_vol`, `*_amt`（缩写形式）

### 4.3 配置规则

1. 如果表中同时包含开始时间和结束时间字段，配置 `time_dimension`
2. 如果表中没有时间范围字段，不配置 `time_dimension`
3. `time_interval` 默认使用 `D`（按日拆分）
4. `transport` 类型的 EDGE 通常需要配置时间维度
5. `link` 类型的 EDGE 通常不需要配置时间维度

## 5. 数据映射配置格式

### 5.1 TAG 配置

```json
{
  "tag_name": "表名",
  "tag_type": "类型标记",
  "vid_field": "VID字段名",
  "source_table": "源表名",
  "description": "描述",
  "fields": ["所有属性字段列表"],
  "field_types": {
    "field_name": "nebula_type"
  },
  "time_dimension": {
    "start_time_field": "开始时间字段名",
    "end_time_field": "结束时间字段名",
    "time_interval": "D",
    "quantity_fields": ["量字段列表"]
  }
}
```

### 5.2 EDGE 配置

```json
{
  "edge_name": "边名称",
  "edge_type": "类型标记",
  "src_vid_field": "源节点VID字段",
  "dst_vid_field": "目标节点VID字段",
  "rank_field": "排序字段",
  "source_table": "源表名",
  "src_tag": "源节点TAG名称",
  "dst_tag": "目标节点TAG名称",
  "description": "描述",
  "fields": ["所有属性字段列表"],
  "field_types": {
    "field_name": "nebula_type"
  },
  "time_dimension": {
    "start_time_field": "开始时间字段名",
    "end_time_field": "结束时间字段名",
    "time_interval": "D",
    "quantity_fields": ["量字段列表"]
  }
}
```

### 5.3 data_mapping.json 整体结构

```json
{
  "tags": [ ... ],
  "edges": [ ... ]
}
```

### 5.4 字段取值来源

| 字段 | 取值来源 |
|------|---------|
| `tag_name` / `edge_name` | `table_schema.table_name` |
| `tag_type` / `edge_type` | `object_type` |
| `vid_field` | `table_schema.indexes` 唯一索引字段或 `primary_key[0]` |
| `src_vid_field` / `dst_vid_field` | 通过 `edge_endpoints` + `foreign_keys` 解析 |
| `source_table` | 与 `tag_name` / `edge_name` 一致 |
| `src_tag` / `dst_tag` | `edge_endpoints.from_objects` / `to_objects` 对应对象的 `table_name` |
| `description` | `table_schema.table_desc` |
| `fields` | `table_schema.fields[].name` 列表（确保包含 version_id） |
| `field_types` | MySQL → NebulaGraph 类型转换结果 |
| `rank_field` | 排序字段（如有）或 `null` |
| `time_dimension` | 按时间维度检测规则生成（如不存在则省略此字段） |

## 6. 交叉引用校验

在输出最终结果前，必须完成以下校验：

### 6.1 TAG 列表完整性

- 每个 TAG 的 `tag_name` 唯一
- 每个 TAG 的 `vid_field` 存在于 `fields` 列表中
- 每个 TAG 的 `fields` 包含 `version_id`
- 每个 TAG 的 `field_types` 包含 `fields` 中的所有字段

### 6.2 EDGE 列表完整性

- 每个 EDGE 的 `edge_name` 唯一
- 每个 EDGE 的 `src_vid_field` 和 `dst_vid_field` 存在于 `fields` 列表中
- 每个 EDGE 的 `fields` 包含 `version_id`
- 每个 EDGE 的 `field_types` 包含 `fields` 中的所有字段

### 6.3 TAG-EDGE 关联

- 每个 EDGE 的 `src_tag` 存在于 TAG 列表中
- 每个 EDGE 的 `dst_tag` 存在于 TAG 列表中
- 如果某个 EDGE 的 `src_tag` 或 `dst_tag` 不存在，抛出错误并说明缺失的 TAG 名称

### 6.4 DDL 一致性

- DDL 中的 TAG 数量与 nebula_graph_schema.json 中的 TAG 数量一致
- DDL 中的 EDGE 数量与 nebula_graph_schema.json 中的 EDGE 数量一致
- DDL 中每个 TAG/EDGE 都有对应的 version_id 索引

