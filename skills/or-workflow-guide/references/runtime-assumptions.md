# 运行时 adapter 边界

> 关联：`skills/or-workflow-guide/SKILL.md`（路由与进度账本）、`skills/or-workflow-guide/agents/roles.yaml`（中立角色契约）。
> 本文件只回答一个问题：**各运行时环境（Codex/OpenAI、Claude Code、ZCode、自研 harness）的 adapter 能改什么、不能改什么。**

## adapter 只负责

- 选择模型槽位或具体模型（按 `agents/roles.yaml` 的 `model_slots`）。
- 把中立角色契约转成当前运行环境的 agent / subagent 配置。
- 调用对应 skill 阶段，把权威制品写入 `docs/` 下的既定路径。
- 读取 `docs/reviews/*.review.yaml` 的结论，把阶段状态写回 `docs/sdd-state.yaml`。

## adapter 不得改变

- 权威制品路径（`docs/ontology_schema.json` 等，见 SKILL.md「产物分层」）。
- 阶段标识符、`status` / `gate` 枚举（见 SKILL.md「进度账本」）。
- review 文件结构与 status 枚举（以 `agents/roles.yaml` 的 `review_schema` 为准）。
- 阶段门禁语义与下游消费契约。
- 业务流程定义（不得把私有协议泄漏到中立 skill 指令中）。

> 制品路径、状态真相源、产物分层等通用契约已在 SKILL.md 中定义，此处不重复。
