# Ontology Schema 契约

本文件说明 `docs/ontology_schema.json` 的写入和校验要求。需要生成或修复 schema 时读取。

## 目录

- 基本要求
- 顶层字段
- 对象字段
- 关系字段
- 规则字段
- SOP 字段
- 校验

## 基本要求

Schema JSON 必须写入 `docs/ontology_schema.json`，内容为纯 JSON：

- 不带 Markdown 代码块。
- 不带 XML、HTML、artifact/card wrapper。
- 不写注释。
- 字段结构以 `references/ontology_schema.schema.json` 为权威结构约束。
- 强校验以 `scripts/validate_ontology.py` 为准。

## 顶层字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `biz_logic` | string | 业务逻辑，持续记录用户的对话输入和确认过的业务上下文 |
| `domain` | string | 业务场景归属领域 |
| `objects` | array | 实体对象列表 |
| `edges` | array | 本体中的关系列表 |
| `rules` | array | 分析提取出的高价值业务规则约束 |
| `sop_flows` | array | 业务逻辑 SOP 执行流程列表 |

## 对象字段

`objects[]` 中每个对象包含：

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | string | 对象 code，仅英文、数字、下划线，字母开头，长度不超过 32 |
| `name` | string | 对象名称 |
| `comment` | string | 对象扩展信息 |
| `properties` | array | 对象属性列表 |

`properties[]` 中每个属性包含：

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | string | 属性 code，仅英文、数字、下划线，字母开头，长度不超过 32 |
| `name` | string | 属性名称 |
| `comment` | string | 属性描述 |
| `type` | string | 仅允许 `String`、`Integer`、`Double` |

## 关系字段

`edges[]` 中每个关系包含：

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | string | 关系 code，仅英文、数字、下划线，字母开头，长度不超过 32 |
| `name` | string | 关系名称 |
| `comment` | string | 关系描述 |
| `source_code` | string | 来源对象 code，必须指向已定义 object |
| `target_code` | string | 目标对象 code，必须指向已定义 object |
| `constraint` | string | 对象之间的关系约束 |

## 规则字段

`rules[]` 中每个规则包含：

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | string | 规则唯一编码，英文、数字、下划线，字母开头，长度不超过 64 |
| `description` | string | 规则内容 |

## SOP 字段

`sop_flows[]` 中每个流程包含：

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | string | SOP 流程编码，英文、数字、下划线，字母开头，长度不超过 32 |
| `title` | string | SOP 流程标题 |
| `steps` | array | 流程步骤列表，按执行顺序排列 |

`steps[]` 中每个步骤包含：

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | string | SOP 步骤编码，英文、数字、下划线，字母开头，长度不超过 32 |
| `title` | string | SOP 步骤标题 |

## 校验

运行：

```bash
python3 skills/ontology-modeling/scripts/validate_ontology.py docs/ontology_schema.json
```

校验内容：

- 结构完整性：顶层字段、object/edge/rule/sop 的必填字段。
- code 唯一性：objects、object 内 properties、edges、rules、sop_flows、sop_steps。
- edge 引用完整性：`source_code` / `target_code` 必须指向已定义 object。
- 属性类型枚举：仅允许 `String` / `Integer` / `Double`。
- code 格式与长度：英文+数字+下划线，字母开头，长度限制。

退出码：

- `0`：通过，可能包含软警告。
- `1`：存在硬错误，必须修复后重跑。

如环境安装了 `jsonschema`，脚本会额外按 `ontology_schema.schema.json` 做结构校验；未安装也能运行。
