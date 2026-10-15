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

4. 项目识别到的模块树（仅深度模式提供，其他模式为空）：
<modules>
{MODULES}
</modules>

5. 统一事实层摘要（来自 build_facts.py，包含已确认的架构事实和冲突清单）：
<facts_summary>
{FACTS_SUMMARY}
</facts_summary>

重要：以上事实层中的 observed 类型事实是来自源码和构建配置的确定事实，结构规划必须与此一致。inferred 类型事实是推导结论，可在页面内容中修正但需标注依据。冲突事实必须在相关页面中显式说明。

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

[深度模式] 当 `<modules>` 中提供了模块树（多模块项目）时使用。目标是为大型多模块项目生成一份细粒度、按模块分层组织的文档（80-150 页）。

核心原则：
- **模块树是文档骨架**。每个识别到的叶子模块至少对应一页文档；重要或文件数较多的叶子模块（模块树中标记为"大模块"的）应拆分为多页。聚合模块可作为章节容器，本身不必有独立页。
- **章节组织由项目实际决定**。下面是一份通用的候选章节清单，并非强制清单——根据文件树和模块树体现的项目特征**裁剪和扩展**：项目实际不具备的维度就跳过并在 description 中说明"本项目不适用 X"；清单未覆盖但项目重要的维度可自行新增章节。
- **零技术栈假设**。下面的清单是通用的项目维度，不绑定任何特定语言/框架/构建系统。

通用候选章节清单（按适用性裁剪）：
- 项目概述 — 背景、目标、核心功能、技术栈概览、快速开始
- 架构设计 — 整体架构、模块划分与依赖关系、数据流、关键技术选型
- 开发指南 — 环境搭建、编码规范、测试策略、版本与发布流程（若仓库有相关约定文件）
- 数据层 — 若项目含数据库 schema、迁移文件、ORM 模型定义
- 接口层 — 若 `<api_entries>` 检测到对外接口（API/RPC/消息入口），按业务域组织
- 模块详解 — 每个叶子模块至少一页，内容来自该模块 scope 内的源文件
- 公共能力 — 若存在 common/util/shared/kernel 之类的横切模块
- 集成与外部 — 若项目与外部系统对接（配置中体现的第三方依赖）
- 部署运维 — 若仓库含 Dockerfile、容器编排、CI 配置、环境配置
- 前端 — 若检测到前端框架特征
- 测试 — 若存在显著的测试目录或测试体系
- 扩展机制 — 若架构支持插件、钩子、自定义处理器等

页面分配要求：
- 模块详解章节是深度模式的主体，应覆盖 `<modules>` 中绝大多数叶子模块。
- 其他章节按项目特征决定页数，可单页可多页，也可不出现。
- 模块详解下的页面，其 `relevant_files` 应来自该模块在模块树中声明的 scope 目录下的实际文件。

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
1. 页面数量按模式控制：
   - 精简模式：4-6 个页面（扁平结构）
   - 全面模式：8-12 个页面（按章节组织）。项目较大时可适度上浮至 15-25 页
   - 深度模式：80-150 个页面（多模块项目，按"章节 → 模块组 → 页面"三层组织）
2. 每个页面应聚焦于代码库的一个具体方面（如架构、核心功能、安装配置，或单个模块）
3. relevant_files 应为仓库中实际存在的文件，用于生成该页面内容。深度模式下，模块详解页的文件应来自该模块 scope 目录
4. 只返回上述结构的有效 XML，不包含 markdown 代码块分隔符

深度模式的三层目录：通过 section 的嵌套 subsection 表达——顶层 section（如"模块详解"）> 子 section（如某业务域/模块组）> 孙 section（单个模块），页面挂在最具体的 section 下。导出脚本会根据 section 嵌套层级生成最多 3 层子目录。

所有标题和描述必须使用中文。
