# 后端技术规范选择入口

本文件仅适用于 `target_kind = backend-java` 或 `target_kind = backend-python` 的后端设计。其他目标类型先读取 `implementation-target-guidelines.md`，不要强制用户选择 Java/Python，也不要为了满足后端模板而生成后端契约。

## 语言选择规则

1. 先检查现有项目、历史文档、构建文件和用户要求，判断后端语言是否已经被约束。
2. 如果现有项目已经明确是 Java/Spring Boot 或 Python/FastAPI，向用户说明推断结果并确认。
3. 如果目标确实是新建/扩展后端且没有明确约束，必须在澄清问题阶段让用户选择后端语言；这是后端 target 的必问项，计入澄清问题预算。
4. 用户选择后，将结果写入 `docs/app-design.md` 的技术选型部分，并写入 `docs/contracts/app-contract.yaml` 的 `project.targetKind`（`backend-java` / `backend-python`）与 `project.implementation` 字段。
5. 读取并遵守所选语言的专用规范：
   - Java: `references/backend-java-tech-guidelines.md`
   - Python: `references/backend-python-tech-guidelines.md`

## 选择题模板

当上下文没有锁定语言时，使用以下问题：

> 后端开发语言你希望采用哪一种？  
> A. Java / Spring Boot（适合既有企业 Java 体系、多模块 Maven、MyBatis）  
> B. Python / FastAPI（适合轻量 API、AI/数据处理集成、快速迭代）  
> 我会根据你的选择继续生成对应的架构、接口、目录和测试规范。

## 通用数据库约束

无论选择 Java 还是 Python，数据库设计仍遵守 `db-design-rules.md` 的持久化决策门禁和表结构规约。只有当前应用需要长期持久化对象时才生成或修改权威 DDL。
