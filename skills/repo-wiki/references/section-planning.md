# 阶段2：章节规划

把阶段1产出的模块树组织为**业务章节树**——每个章节是一个物理目录，章节下放置相关的模块文件。

> 设计原则：章节按**业务领域**划分（如"概览"、"系统架构"、"核心功能"、"数据管理"、"部署与基础设施"），不映射源码目录结构。一个章节 = 一个物理目录，章节可嵌套（最多 2 层）。

## 输入

- 阶段1的模块树（内存中）：含模块路径 + 业务描述 + 业务领域标签
- 仓库 README（如有）
- 项目名

## 步骤

### 1. 分析模块树，识别业务领域

从模块树中提取每个模块的 `domain`（业务领域）标签，统计各领域下的模块数量：

```
概览/入门类：项目概述, 快速上手, ...
系统架构类：整体架构, 数据流, ...
核心功能类：匹配引擎, 技能注册, ...
数据管理类：数据访问层, 缓存, ...
部署与基础设施类：构建系统, CI/CD, ...
```

### 2. 规划章节树

基于业务领域分组，设计章节树结构。每章节：

```
<section id="section-1">
  <title>系统架构</title>
  <description>系统整体设计、分层策略、核心抽象与模块间协作</description>
  <modules>
    <module_ref>page-1</module_ref>
    <module_ref>page-2</module_ref>
  </modules>
  <subsections>
    <section_ref>section-3</section_ref>
  </subsections>
</section>
```

### 3. 输出章节树 XML

LLM 输出如下 XML 格式（借鉴 DeepWiki 的 `<wiki_structure>`）：

```xml
<section_tree>
  <title>项目名 仓库知识库</title>
  <description>项目简述</description>
  <sections>
    <section id="section-1">
      <title>概览</title>
      <description>项目概述、快速上手、核心概念入门</description>
      <modules>
        <module_ref id="page-1">
          <title>项目概述</title>
          <source_module_path>/</source_module_path>
        </module_ref>
        <module_ref id="page-2">
          <title>快速上手</title>
          <source_module_path>docs/</source_module_path>
        </module_ref>
      </modules>
    </section>
    <section id="section-2">
      <title>系统架构</title>
      <description>系统整体设计、分层策略、核心抽象与模块间协作</description>
      <modules>
        <module_ref id="page-3">
          <title>整体架构</title>
          <source_module_path>src/core/</source_module_path>
        </module_ref>
      </modules>
      <subsections>
        <section_ref>section-3</section_ref>
      </subsections>
    </section>
    <section id="section-3">
      <title>数据流与状态管理</title>
      <description>数据在系统中的流转路径与状态管理策略</description>
      <modules>
        <module_ref id="page-4">
          <title>数据流</title>
          <source_module_path>src/data/</source_module_path>
        </module_ref>
      </modules>
    </section>
    <!-- 更多章节 -->
  </sections>
</section_tree>
```

### 4. 规划约束

| 约束 | 说明 |
|---|---|
| 根章节数 | 3-10 个 |
| 每章节模块数 | 1-8 个 |
| 嵌套深度 | 最多 2 层（根章节 → 子章节） |
| 章节名 | 全中文，3-10 个汉字，聚焦业务领域 |
| 模块归属 | 每个非噪音模块必须归属且仅归属一个章节 |
| 章节不映射源码目录 | 章节按业务领域划分，不是源码目录的镜像 |

### 5. 章节命名指南

常见章节名（按项目类型选择/组合）：

| 章节名 | 覆盖内容 |
|---|---|
| 概览 | 项目概述、快速上手、核心概念 |
| 系统架构 | 整体设计、分层策略、核心抽象 |
| 核心功能 | 主要业务功能模块 |
| 数据管理 | 数据访问、存储、缓存、数据流 |
| 前端组件 | UI 组件、页面、路由（纯后端仓跳过） |
| 后端服务 | API、服务层、中间件 |
| 集成与扩展 | 外部集成、插件、扩展点 |
| 部署与基础设施 | 构建、部署、CI/CD、容器化 |
| 测试与质量 | 测试策略、质量保障 |

### 6. 内存中保留

章节规划在内存中保留，包含：
- 章节树结构（中文目录名 + 描述 + 模块分配）
- 每个 module_ref 的 id → 中文文件名映射
- 章节目录名 → section id 映射

供阶段3生成文件时参照。

## 准出（阶段2）

- 章节树覆盖全部非噪音模块（每个模块有且仅有一个章节归属）
- 根章节 3-10 个，每章节 1-8 个模块
- 章节名全中文，3-10 个汉字
- 章节规划在内存中保留，供阶段3使用
- 章节按业务领域划分，不映射源码目录结构
