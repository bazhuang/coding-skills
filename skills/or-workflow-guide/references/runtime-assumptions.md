# 运行时假设与路径约定

> 本文件记录 skills/ 流水线在不同运行时下的产物路径与状态真相源约定，供跨运行时对齐。
> 关联：`skills/or-workflow-guide/SKILL.md`（路由与进度账本）、`skills/ontology-modeling/references/script/finish_ontology.py`（外部运行时集成脚本）。
> 更新日期：2026-06-24。

---

## 1. 仓内 skill 流：以 `docs/` 为制品根目录

skills/ 下的本地流程（Claude Code / Codex / ZCode 等直接读写文件的 agent）统一约定：

- 所有规格与过程制品写入项目根的 `docs/` 目录（`docs/ontology_schema.json`、`docs/brd.md`、`docs/requirements-baseline.json`、`docs/contracts/*`、`docs/impl-plan.md`、`docs/traceability.json`、`docs/spec-versions.json`、`docs/workflow-progress.md`）。
- 跨会话状态唯一真相源 = `docs/workflow-progress.md`（进度账本）。
- 跨 agent 契约是文件本身，而非对话消息格式或平台专用标记。

## 2. `finish_ontology.py` 是外部运行时集成脚本

`skills/ontology-modeling/references/script/finish_ontology.py` 经核实属于**外部 agent 运行时**的一部分，**不被仓内 skill 流程调用**：

- 第 7–10 行：`sys.path.insert(.../common)` 后 `from config import ...`、`from http_proxy import http_proxy`——依赖一个 `common/` 模块。该目录在本仓库**不存在**（属更大系统的一部分）。**此依赖未消除**，脚本在仓内环境仍无法独立运行。
- **读取路径：已与主流程对齐**（工作区改动，本会话期间确认）——从原来的 `<repo>/../output/ontology_schema.json` 改为 `<repo>/docs/ontology_schema.json`（`Path(__file__).resolve().parents[4] / "docs" / "ontology_schema.json"`）。即 schema 读取路径这一项 C3 不一致**已解决**。
- 第 28–32 行：向本地代理 `http://127.0.0.1:8080/aicoding/agent/step/skill/complete` POST 回调，表明它服务于一个会回调完成状态的 agent 编排系统（未变）。

**结论**：脚本**仍是外部运行时集成**（依赖 `common/`、POST 回调本地代理），仓内流程不依赖它。schema 读取路径已统一到 `docs/`（C3 路径项已落地）；但 `common/` 依赖、`openai.yaml` 编排策略的统一仍未做（见 §4）。

## 3. `agents/openai.yaml`：外部 OpenAI agent 隐式调用入口

`skills/or-workflow-guide/agents/openai.yaml` 声明 `allow_implicit_invocation: true`，即本 skill（or-workflow-guide）可被外部 OpenAI agent 入口隐式调用。其运行时假设（进度状态权威、产物路径、阶段触发方式）需与本地 skill 文件保持一致——**以 `docs/workflow-progress.md` 为跨运行时唯一状态真相源**。该文件本身的编排策略改动属高风险，本轮不动。

## 4. C3-code 仍待做（高风险，待外部运行时评估）

C3「运行时与产物路径统一」中，**schema 读取路径已统一**（`finish_ontology.py` 工作区已改为读 `<repo>/docs/ontology_schema.json`）。以下仍未做，待外部运行时结构评估后再单独处理：

- 移除 `finish_ontology.py` 的 `common/` 依赖（`from config/http_proxy import ...`）——`common/` 仓内不存在，脚本仍无法独立运行。
- 修改 `agents/openai.yaml` 的隐式调用策略或编排假设。
- 评估外部 OpenAI agent 回调是否参与阶段流转。

**接续要点**（待评估）：先确认外部 OpenAI agent 回调是否参与阶段流转；`docs/workflow-progress.md` 已选定（本文件 §1 写明）为跨运行时唯一状态真相源；剩余统一 `common/` 依赖与 `openai.yaml` 编排。
