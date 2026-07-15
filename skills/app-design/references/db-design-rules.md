# 数据库设计规则

本文件是 app-design 阶段的持久化决策和数据库设计规约。判断对象是否建表、设计数据库或生成 `docs/contracts/db-schema.sql` 时读取并遵守。

## 持久化决策门禁

在从本体对象推导表结构前，先判断每个对象的数据权威源和生命周期。只有由当前应用长期持久化、具有独立业务生命周期的对象才建表。

| 对象类型 | 是否建表 | 规则 |
|---|---|---|
| 核心业务实体 | 通常建表 | 有独立生命周期、需要本系统持久化 |
| 外部系统实体 | 不建表或只存引用 | 数据权威源在外部系统 |
| 短生命周期流程状态 | 默认不建表 | 如扫码票据、验证码、临时授权态 |
| UI 状态 | 不建表 | 组件内状态、store 状态或 URL 状态 |
| 既有本地 KV 状态 | 不新增表 | 复用现有 key，设计中说明 key 契约 |
| 审计事件 | 视项目已有审计能力 | 没有明确审计表时不强制新建 |

持久化决策必须写入 `docs/app-design.md`，并同步到 `app-contract.yaml` 的对象字段：

- 需要建表：`persistence: mysql-table`，同时填写 `table`。
- 不建表：填写 `persistence` 为 `external-service`、`transient-memory`、`existing-local-kv`、`ui-state` 或 `none`，并说明原因。

如果不涉及数据库变更，不强制生成 `docs/contracts/db-schema.sql` 或 `docs/db-schema.md`，但必须在 `docs/app-design.md` 写明“数据库影响：无”及原因。只有下游兼容流程明确依赖 SQL 文件存在时，才生成 no-op `docs/contracts/db-schema.sql`，并说明它不是实际数据库设计。

## 本体到表结构映射

- 每个需要当前应用长期持久化的本体业务对象默认对应一张业务表。
- 类名转换为表名：PascalCase 或 snake_case 统一转小写下划线。
- 可按项目规范添加前缀，如 `biz_`、`rel_`、`sys_`。
- 一对多关系：在多方表添加一方 id 字段并建普通索引。
- 多对多关系：创建独立关联表，包含自增主键、两侧 id、审计字段，并对两侧 id 建唯一索引。
- 不使用数据库外键，关联完整性由应用层保证。

## 基础建表规约

- 每张表必须有 `id bigint unsigned NOT NULL AUTO_INCREMENT` 作为主键。
- 每张表必须有审计字段：
  - `create_by varchar(64)`
  - `gmt_create datetime NOT NULL DEFAULT CURRENT_TIMESTAMP`
  - `update_by varchar(64)`
  - `gmt_modified datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP`
- 逻辑删除字段使用 `is_deleted tinyint unsigned NOT NULL DEFAULT '0'`。
- 表名、字段名使用小写字母和下划线，禁止 MySQL 保留字。
- 禁止 `float` / `double`，小数统一使用 `decimal`。
- 无符号非负数值使用 `unsigned`。
- 可能为负的金额、差价、利润类字段保留有符号 `decimal`。

## 字段建模规约

- 时间范围不得使用自由文本字段，使用 `*_start_time` / `*_end_time` 或明确业务前缀。
- 固定格式年月使用 `char(7)`，格式 `yyyy-MM`。
- 布尔字段使用 `is_xxx tinyint unsigned`。
- 状态、类型、枚举字段使用 `tinyint unsigned`，并在 COMMENT 中列出枚举值。
- 名称类字段如参与关联、统计或外部系统对接，应配套稳定编码字段，如 `customer_code` + `customer_name`。
- 区域、组织、客户、供应商等主数据优先使用 `code` 作为业务锚点，`name` 只用于展示。
- 气量、价格、金额等存在口径差异时，应在计划或明细层记录单位、含税口径或统计口径。
- 大文本、JSON 快照、执行日志等不放主表，拆到独立明细表或日志表。

## 索引规约

- 主键索引：`PRIMARY KEY (id)`。
- 唯一索引命名：`uk_字段名` 或 `uk_业务含义`。
- 普通索引命名：`idx_字段名` 或 `idx_业务含义`。
- 业务唯一字段必须建唯一索引。
- 高频关联字段必须建普通索引。
- 单表二级索引不超过 5 个；超过时优先合并为组合索引。
- 组合索引按查询最常用前缀排列。

## 输出要求

- 有数据库变更时，DDL 写入 `docs/contracts/db-schema.sql`，这是权威可执行源。
- `docs/db-schema.md` 只做说明和引用，不内嵌第二份权威 DDL。
- `app-contract.yaml` 中需要建表对象的 `objects[].table` 必须与 DDL 表名一致。
- 不建表对象不得为了满足模板虚构表名；改用 v2 contract 的 `persistence` 表达。
