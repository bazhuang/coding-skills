# 应用设计审查清单

完成 `docs/app-design.md`、`docs/contracts/db-schema.sql`、`docs/contracts/app-contract.yaml` 后读取并执行本清单。

## 通用设计质量

- 是否存在 TBD、TODO、占位符、互相矛盾的章节？
- 设计是否聚焦当前阶段，是否混入不必要功能？
- 是否明确后端语言和对应技术规范？
- 模块边界是否清晰，CRUD 数据维护与业务编排是否分离？
- 长耗时流程是否采用异步任务或可恢复任务，而不是同步接口阻塞？
- 明细结果之外是否需要汇总读模型，避免每次实时聚合？
- 状态流转是否有统一守卫，已确认数据是否禁止直接覆盖？
- 多轮迭代是否保留历史版本和输入快照？

## 数据模型

- 时间区间是否拆成开始/结束字段，而不是自由文本？
- 名称类字段是否需要稳定编码？
- 区域、组织、客户、供应商等主数据是否有 code？
- 气量、价格、金额是否有单位、含税口径或统计口径？
- 综合目标是否需要目标权重或策略配置？
- 路径、线路、站点等可复用对象是否有稳定 code？
- 大文本、JSON 快照、日志是否从主表拆出？
- 布尔/状态/枚举是否使用 `tinyint unsigned`？
- 非负数值是否使用 `decimal unsigned`？
- 可能为负的利润、差价是否保留有符号 decimal？
- 单表二级索引是否不超过 5 个？
- 是否没有外键、没有 float/double、没有 MySQL 保留字字段？

## 契约覆盖

- `app-contract.yaml` 是否覆盖 ontology 的全部对象？
- `app-contract.yaml` 是否覆盖全部规则？
- `app-contract.yaml` 是否覆盖全部 SOP？
- Markdown 人读映射表是否与 `app-contract.yaml` 一致？
- `db-schema.sql` 的表名是否与 `app-contract.yaml` 的 `objects[].table` 一致？

## 准出表达

在最终回复中输出：

```text
契约覆盖率：对象 X/X，规则 Y/Y，SOP Z/Z。
DDL 检查：无外键、无 float/double、索引数符合约束。
设计文档和结构化契约已保存，等待用户审查。
```
