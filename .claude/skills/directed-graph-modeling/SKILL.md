---
name: directed-graph-modeling
description: Convert algorithm ontology objects into NebulaGraph TAG/EDGE schema, DDL execution code, and data mapping configuration.
---

# Directed Graph Modeling

将算法本体模型中的节点和边对象转化为 NebulaGraph 图数据库的 TAG/EDGE 定义，生成 DDL 语句和执行代码。

## 适用输入

1. business-to-or-ontology skill 产出的算法本体模型 JSON（自包含运筹语义结果，包含 `algorithm_objects.objects` 中的节点、边定义及 `table_schema`）

## 内置参考

- 图映射规则：[references/graph-mapping-rules.md](references/graph-mapping-rules.md)
- NebulaGraph 连接配置：[references/nebula_config.json](references/nebula_config.json)

## 输出文件

1. **nebula_schema.sql** — 可执行的 NebulaGraph DDL 语句
2. **DDL 执行代码** — Python 代码，连接 NebulaGraph 集群并执行 DDL
3. **data_mapping.json** — 数据映射配置，定义 TAG/EDGE 的字段信息和时间维度，供数据管线代码生成使用

## Workflow

### 1. 读取算法本体模型

读取 business-to-or-ontology 输出的算法本体模型 JSON，识别 `algorithm_objects.objects` 中每个对象的类别、类型、表结构、端点关系。

### 2. 筛选对象

- `object_category: "node"` → 映射为 TAG
- `object_category: "edge"` → 映射为 EDGE

### 3. 生成 TAG/EDGE 定义

按 [graph-mapping-rules.md](references/graph-mapping-rules.md) 中的 TAG 和 EDGE 构造规则生成定义。

### 4. 生成数据映射配置

按 [graph-mapping-rules.md](references/graph-mapping-rules.md) 中的规则和格式：

- 生成 `data_mapping.json`，包含每个 TAG/EDGE 的字段信息和时间维度配置

### 5. 生成 DDL 语句

按 [graph-mapping-rules.md](references/graph-mapping-rules.md) 中的 DDL 格式规则生成，写入 `nebula_schema.sql`。

### 6. 生成 DDL 执行代码

按 [graph-mapping-rules.md](references/graph-mapping-rules.md) 中的要求生成 Python 代码。

### 8. 校验

按 [graph-mapping-rules.md](references/graph-mapping-rules.md) 中的校验规则逐项检查。

## 禁止事项

- 不要修改 `table_schema` 中的表名或字段名
- 不要编造不存在的字段
- 不要遗漏 `version_id` 字段和索引
- 不要跳过交叉引用校验

## 质量标准

1. TAG/EDGE 名称与 `table_schema.table_name` 完全一致
2. 字段名称与 `table_schema.fields[].name` 完全一致
3. 大小写全文一致
4. 每个 TAG/EDGE 都有 `version_id` 字段和对应索引
5. EDGE 的 src_tag/dst_tag 可回溯到 TAG 定义
6. 类型转换严格遵循 MySQL → NebulaGraph 规则表
