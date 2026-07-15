分析仓库 {REPO_NAME} 并为其创建一个文档结构。

1. 项目完整文件树：
<file_tree>
{FILE_TREE}
</file_tree>

2. 项目的 README 文件：
<readme>
{README}
</readme>

3. 项目识别到的 API 入口列表：
<api_entries>
{API_ENTRIES}
</api_entries>

我想为这个仓库创建一份文档。请根据仓库内容确定最合理的文档结构。

重要提示：文档内容将以中文生成。

在设计文档结构时，包含适合用图表展示的页面，例如：
- 架构总览
- 数据流描述
- 组件关系
- 业务流程
- 状态机
- 类层次结构

[全面模式] 创建一个结构化文档，包含以下主要章节：
- 概览（项目基本信息）
- 系统架构（系统的设计方式）
- 核心功能（关键功能）
- 数据管理/数据流：如适用，说明数据如何存储、处理、访问和管理（例如：数据库 schema、数据管线、状态管理）。
- 前端组件（UI 元素，如适用）
- 后端系统（服务端组件）
- 模型集成（AI 模型连接）
- 部署/基础设施（如何部署、基础设施是什么样的）
- 扩展性与定制化：如果项目架构支持，说明如何扩展或定制其功能（例如：插件、主题、自定义模块、钩子）。

每个章节应包含相关页面。例如，"前端组件" 章节可能包含 "首页"、"仓库文档页面"、"问答组件" 等页面。

按以下 XML 格式返回分析结果：

<wiki_structure>
  <title>[项目总标题]</title>
  <description>[仓库简要描述]</description>
  <sections>
    <section id="section-1">
      <title>[章节标题]</title>
      <pages>
        <page_ref>page-1</page_ref>
        <page_ref>page-2</page_ref>
      </pages>
      <subsections>
        <section_ref>section-2</section_ref>
      </subsections>
    </section>
    <!-- 根据需要添加更多章节 -->
  </sections>
  <pages>
    <page id="page-1">
      <title>[页面标题]</title>
      <description>[该页面将覆盖内容的简要描述]</description>
      <importance>high|medium|low</importance>
      <relevant_files>
        <file_path>[相关文件路径]</file_path>
        <!-- 根据需要添加更多文件路径 -->
      </relevant_files>
      <related_pages>
        <related>page-2</related>
        <!-- 根据需要添加更多相关页面 ID -->
      </related_pages>
      <parent_section>section-1</parent_section>
    </page>
    <!-- 根据需要添加更多页面 -->
  </pages>
</wiki_structure>

[精简模式] 按以下 XML 格式返回分析结果：

<wiki_structure>
  <title>[项目总标题]</title>
  <description>[仓库简要描述]</description>
  <pages>
    <page id="page-1">
      <title>[页面标题]</title>
      <description>[该页面将覆盖内容的简要描述]</description>
      <importance>high|medium|low</importance>
      <relevant_files>
        <file_path>[相关文件路径]</file_path>
        <!-- 根据需要添加更多文件路径 -->
      </relevant_files>
      <related_pages>
        <related>page-2</related>
        <!-- 根据需要添加更多相关页面 ID -->
      </related_pages>
    </page>
    <!-- 根据需要添加更多页面 -->
  </pages>
</wiki_structure>

重要格式要求：
- 只返回上述指定的有效 XML 结构
- 不要将 XML 包裹在 markdown 代码块中（不要使用 ``` 或 ```xml）
- 不要在 XML 前后包含任何解释文字
- 确保 XML 格式正确且有效
- 直接以 <wiki_structure> 开始，以 </wiki_structure> 结束

重要提示：
1. 创建 8-12 个页面（全面模式）或 4-6 个页面（精简模式），构成一份全面或精简的文档
2. 每个页面应聚焦于代码库的一个具体方面（如架构、核心功能、安装配置）
3. relevant_files 应为仓库中实际存在的文件，用于生成该页面内容
4. 只返回上述结构的有效 XML，不包含 markdown 代码块分隔符

所有标题和描述必须使用中文。
