# 后端技术规范选择入口

应用设计阶段必须先确定后端开发语言，再读取对应的技术规范。不要同时混用多套后端规范。

## 语言选择规则

1. 先检查现有项目、历史文档、构建文件和用户要求，判断后端语言是否已经被约束。
2. 如果现有项目已经明确是 Java/Spring Boot 或 Python/FastAPI，向用户说明推断结果并确认。
3. 如果没有明确约束，必须在澄清问题阶段让用户选择后端语言；这是设计阶段的必问项，计入澄清问题预算。
4. 用户选择后，将结果写入 `docs/app-design.md` 的技术选型部分，并写入 `docs/contracts/app-contract.yaml` 的 `project.backend.language` 字段。
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

无论选择 Java 还是 Python，数据库设计仍遵守 `SKILL.md` 中的本体到表结构映射规则，并输出权威 DDL 到 `docs/contracts/db-schema.sql`。
