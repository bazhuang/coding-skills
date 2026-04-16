# App-Generate Skill

基于本体图谱进行数据建模、架构设计、详细设计的开发流程工具。

## 如何触发

在 CodeBuddy IDE 中，以下场景会自动触发此 skill：

### 触发关键词

| 场景 | 触发语句 |
|------|----------|
| 数据建模 | "根据 ontology 图谱生成 DDL"、"做数据库建模" |
| 架构设计 | "做架构设计"、"输出架构设计文档" |
| 详细设计 | "做详细设计"、"输出详细设计文档" |
| 本体建模 | "基于本体建模"、"进行 ontology 建模" |
| 全流程 | "从头开始"、"重新进行建模" |

### 示例对话

```
用户: 基于 ontology.txt 做数据库建模
      → 自动触发 app_generate skill

用户: 进行本体建模
      → 自动触发 app_generate skill

用户: 做架构设计
      → 自动触发 app_generate skill

用户: 需要详细的接口设计
      → 自动触发 app_generate skill (阶段五)
```

## 工作流程

```
阶段一: 本体图谱Schema解析
   ↓
阶段二: 数据建模 (DDL生成)
   ↓
阶段三: 头脑风暴 (架构师决策)
   ↓
阶段四: 架构设计 (概要设计)
   ↓
阶段五: 详细设计
   ↓
阶段六: 代码生成
```

## 适用场景

- 根据 ontology 图谱 schema 进行 DDL 生成
- 天然气供需匹配运筹项目开发
- 数据库建模、架构设计、详细设计全流程

## 文件结构

```
app_generate/
├── SKILL.md                    # Skill 主文件
└── references/
    ├── arch-design-template.md    # 架构设计模板
    ├── ddl-specs.md                # DDL 规范
    ├── detail-design-template.md  # 详细设计模板
    └── tech-specs.md              # 技术规范
```
