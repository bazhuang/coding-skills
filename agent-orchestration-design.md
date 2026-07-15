# 多角色 Agent 编排设计：基于 TAB Harness 实战的方法论与实现

> 来源分析：腾讯 TAB A/B 实验平台团队的 Harness 工程实践分享文章。
> 文章核心观点：AI 的瓶颈不是模型，而是协作、流程、信任。Harness 的目标不是让 AI 更聪明，而是让 AI 在复杂工程里更可控、更可靠、更可维护。

---

## 一、文章中的 Agent 角色分析

文章定义了 5 个 Agent（4 个认知角色 + 1 个总控调度），以及若干层支撑资产。

### 1.1 角色契约一览

| 角色 | 职责 | 必读 | 必写 | 不许做 |
|------|------|------|------|--------|
| 需求 Agent | TAPD 链接 转成 结构化需求理解 + 影响半径分析 | TAPD 单 / PRD 文本 | 需求理解文档 / 代码影响地图 | 不许写技术方案 |
| 方案 Agent | 需求 转成 可执行的技术方案 | 需求理解文档 / 代码影响地图 | 设计文档 / 技术规约 / 任务清单 | 不许改需求理解文档 |
| 开发 Agent | 按设计落代码 + 接口测试 | 需求理解 / 设计 / 技术规约 / 任务 | 实际代码 + 接口用例文档 + 增量 Go 接口测试 + 单元测试 | 不许超出设计文档计划范围 |
| 代码审查 Agent | 从 4 维度收口 | 上游全部产物 + git diff | 代码审查结论文档 | 不许改代码，只能产出阻塞项 |
| 总控 Agent | 流程调度 / 状态机 / 跑门禁 / 提 MR | checkpoint 文件 / 流程定义 | checkpoint 状态更新 / 度量报告 | 不做认知工作 |

### 1.2 为什么是这 4+1 个

文章明确指出：这 5 个 Agent 不是设计出来的，是被撞墙一步步逼出来的：

- 第一阶段单 Agent 跑全流程，出现上下文混杂、缺乏制衡、倾向推进、token 爆炸
- 第二阶段拆出需求 Agent + 方案 Agent，发现方案 Agent 会顺手改需求理解，于是定了最重纪律：下游不可直接修改上游产物
- 第三阶段拆出代码审查 Agent，不能让写代码的 Agent 自己审自己
- 第四阶段开发 Agent 从"只写代码"扩展到"代码 + 单测 + 接口用例文档 + 增量接口测试"（让产生问题的人同时产生验证手段）
- 不再继续拆（比如把开发拆成数据访问层/服务层/处理层三个 Agent），因为四层架构有强依赖，并行收益不大但协调成本极高，且 Skill 已解决了分层规范问题

### 1.3 关键设计原则

文章反复强调的几条铁律：

1. 下游 Agent 不可直接修改上游产物。需要改时只能提阻塞项，由总控打回上一棒。
2. 能写成 bash 的就别让 Agent 跑。流程调度、门禁、测试、提 MR 全部下沉成确定性脚本。
3. Agent 之间是接力关系，不是协商关系。每一棒交什么、下一棒接到什么才能开跑、跑砸了回到哪一棒。
4. 关键节点必须留人。模型对自己生成的东西没有否决欲望，半自动是当前最优解。
5. 门禁脚本把"完成"的定义权从 AI 手里拿回来。脚本判定通过才算做完。

---

## 二、多角色 Agent 编排架构设计

### 2.1 整体架构图

```
                        +---------------------------------------------------+
                        |                  总控 Agent (Orchestrator)         |
                        |   +-------------------------------------------+   |
                        |   | 状态机(13阶段接力赛) | 人工关卡路由 | 打回规则表 |   |
                        |   +-------------------------------------------+   |
                        |                        |                           |
                        |   +----------+  +----------+  +----------+  +----------+
                        |   | 需求Agent |->| 方案Agent |->| 开发Agent |->| 审查Agent |
                        |   |  GPT-4o  |  | Claude   |  | Claude   |  |  GPT-4o  |
                        |   |          |  | 3.5 Son  |  | 3.5 Son  |  | (独立审查) |
                        |   +----------+  +----------+  +----------+  +----------+
                        |                        |                           |
                        |   +-------------------------------------------+   |
                        |   | 门禁脚本层(7道) | MCP接口层(5个) | 知识库     |   |
                        |   +-------------------------------------------+   |
                        +---------------------------------------------------+
```

### 2.2 大模型分配策略

这是本方案的核心设计：不同 Agent 使用不同大模型，利用模型差异实现天然制衡。

| Agent | 推荐模型 | 选型理由 | 备选模型 |
|-------|---------|---------|---------|
| 总控 Agent | GPT-4o-mini | 纯调度工作：状态机跳转、阶段路由、打回判定。不需要深度推理，需要快、稳、便宜。指令遵循能力强，适合结构化路由。 | Claude Haiku / Qwen-Plus |
| 需求 Agent | GPT-4o | 需求理解需要强语义解析 + 主动提问能力。GPT-4o 在理解模糊需求、多轮澄清方面表现稳定。模型偏"谨慎推进"的特性正好适合需求分析阶段。 | o3 / DeepSeek-V3 |
| 方案 Agent | Claude 3.5 Sonnet | 技术方案设计需要深度推理 + 大上下文窗口。Claude 3.5 Sonnet 在架构设计、跨模块分析、长文档生成方面表现突出，200K 上下文适合读全量影响半径。 | GPT-4o / o3 |
| 开发 Agent | Claude 3.5 Sonnet | 代码生成质量是第一位。Claude 3.5 Sonnet 在 HumanEval / SWE-bench 等代码基准上表现最强。同时产出接口测试代码也需要强编码能力。 | GPT-4o / DeepSeek-Coder |
| 代码审查 Agent | GPT-4o | 必须与开发 Agent 使用不同模型族。文章强调"不能让写代码的 Agent 自己审自己"。如果开发用 Claude，审查就用 GPT-4o，实现模型层面的天然制衡。不同模型对同一段代码的关注点天然不同，能抓出更多问题。 | o3 / Gemini Pro |

模型制衡的核心逻辑：

文章原文："代码审查 Agent 就是专门来抓 AI 解释性执行的。AI 实现到一半经常觉得'设计这里写得不好，我顺手改一下'。"

如果开发和审查用同一个模型，模型对自己生成代码的"审美偏好"是一致的，天然不会否决自己风格的代码。用不同模型族做审查，等于引入一个有不同偏好的"新人"来 review，能更有效地发现"方案一致性"偏差。

### 2.3 13 阶段接力赛（Workflow）

每个阶段是接力赛的一棒，明确交付物和打回规则：

```
阶段1  初始化          [总控Agent + 脚本]    解析TAPD -> 派生需求ID -> 改TAPD状态 -> 打标签
阶段2  需求分析        [需求Agent]           PRD -> 需求理解文档 + 影响半径分析 + PRD自评
阶段3  需求确认  人工   [人工关卡]            看5行摘要 -> 确认继续 / 我要修改
阶段4  Bug复现  条件   [条件触发]            bugfix + 需要复现 -> 沙箱复现
阶段5  技术方案        [方案Agent]           需求理解 -> 设计文档 + 技术规约 + 任务清单
阶段6  方案确认  人工   [人工关卡]            跨子仓库/改协议时弹 -> 看层级变更清单
阶段7  方案评审  人工   [人工关卡]            极少触发 -> 真有问题的方案
阶段8  分支准备        [总控Agent + 脚本]    每个涉及子仓库创建特性分支
阶段9  开发            [开发Agent]           设计 -> 代码 + 单测 + 接口用例 + 增量接口测试
阶段10 集成测试        [脚本]                沙箱部署 + 真实HTTP跑接口用例 (硬门禁)
阶段11 代码审查        [代码审查Agent]       4维度收口 -> 审查结论文档
阶段12 验收            [脚本]                幂等重跑接口测试 + diff基线对比
阶段13 交付收尾        [总控Agent + 脚本]    提MR + 推iWiki + 回写TAPD + 企微通知
```

### 2.4 门禁脚本（7 道）

| 时机 | 门禁 | 类型 | 做什么 |
|------|------|------|--------|
| 开发完成 | 覆盖率检查 | 软门禁 | 全量>=40% 且 增量>=85% |
| 开发完成 | 制品一致性检查 | 软门禁 | 任务清单勾选项是否全勾 |
| 开发完成 | 静态检查+安全扫描 | 硬门禁 | golangci-lint 12检查器 + 硬编码密码 + SQL拼接 |
| 集成测试 | 沙箱部署 | 硬门禁 | make sandbox-platform-full-ensure + 网关健康检查 |
| 集成测试 | 接口测试 | 硬门禁 | 真实HTTP跑接口用例文档 |
| 集成测试 | 前端冒烟 | 软门禁(条件) | Playwright路由级渲染 + DOM断言 + 截图 |
| 验收 | 日志验收 | 软门禁(可选) | 关键操作日志存在 + 敏感信息脱敏 |

反作弊设计——基线对比：

开发前先跑一次门禁"基线快照"，开发后再跑一次，新增失败 = B - A，只有"新增的失败"才阻断流程。剥夺 AI 用"这是历史问题"解释的权力。

---

## 三、实现方案：多模型 Agent 编排框架

以下是一个可落地的 Python 实现骨架，展示如何用不同大模型驱动不同 Agent，以接力赛方式编排。

### 3.1 项目结构

```
harness/
  config/
    models.yaml          # 各 Agent 的模型配置
    workflow.yaml        # 13 阶段流程定义
  agents/
    base.py              # Agent 基类
    requirement.py       # 需求 Agent (GPT-4o)
    solution.py          # 方案 Agent (Claude 3.5 Sonnet)
    developer.py         # 开发 Agent (Claude 3.5 Sonnet)
    reviewer.py          # 代码审查 Agent (GPT-4o)
    orchestrator.py      # 总控 Agent (GPT-4o-mini)
  gates/
    baseline.py          # 基线快照
    coverage.py          # 覆盖率检查
    lint.py              # 静态检查
    integration_test.py  # 集成测试
    diff_compare.py      # 基线对比
  mcp/
    tapd.py              # TAPD MCP 封装
    iwiki.py             # iWiki MCP 封装
    gongfeng.py          # 工蜂 MCP 封装
    knot.py              # Knot MCP 封装
    wework.py            # 企微 MCP 封装
  workflow/
    state_machine.py     # 13 阶段状态机
    checkpoint.py        # checkpoint 文件管理
    human_gate.py        # 人工关卡路由
  skills/                # 11 个 Skill 文档
    scaffold_protocol.md
    dal_manual.md
    service_manual.md
    http_handler_manual.md
    unit_test_spec.md
    integration_test_gen.md
    prd_self_eval.md
    impact_radius.md
    prd_template.md
    scope_overflow_check.md
    frontend_review.md
  main.py                # 入口
```

### 3.2 模型配置

```yaml
# config/models.yaml

agents:
  orchestrator:
    provider: openai
    model: gpt-4o-mini
    temperature: 0.0        # 纯调度，确定性优先
    max_tokens: 4096
    role: "流程调度器，不做认知工作"

  requirement:
    provider: openai
    model: gpt-4o
    temperature: 0.3        # 需要一定灵活性理解模糊需求
    max_tokens: 16384
    role: "需求理解 + 影响半径分析"
    skills:
      - prd_self_eval
      - impact_radius
      - prd_template

  solution:
    provider: anthropic
    model: claude-3-5-sonnet-20241022
    temperature: 0.2        # 技术方案需要严谨但保留设计空间
    max_tokens: 32768
    role: "技术方案设计 + 任务拆解"
    skills:
      - scaffold_protocol
      - dal_manual
      - service_manual
      - http_handler_manual

  developer:
    provider: anthropic
    model: claude-3-5-sonnet-20241022
    temperature: 0.1        # 代码生成需要高确定性
    max_tokens: 32768
    role: "代码实现 + 单测 + 接口测试"
    skills:
      - dal_manual
      - service_manual
      - http_handler_manual
      - unit_test_spec
      - integration_test_gen

  reviewer:
    provider: openai        # 故意与 developer 用不同模型族
    model: gpt-4o
    temperature: 0.0        # 审查需要零温度，严格判定
    max_tokens: 16384
    role: "4 维度收口审查"
    skills:
      - scope_overflow_check
      - frontend_review
```

### 3.3 Agent 基类与多模型路由

```python
# agents/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
import json
import yaml


@dataclass
class AgentConfig:
    name: str
    provider: str        # "openai" | "anthropic" | ...
    model: str
    temperature: float
    max_tokens: int
    role: str
    skills: list[str] = field(default_factory=list)


class BaseAgent(ABC):
    """所有 Agent 的基类。每个 Agent 只看自己该看的输入，只产自己该产的输出。"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.llm = self._init_llm(config)

    def _init_llm(self, config: AgentConfig):
        """根据 provider 初始化不同的大模型客户端"""
        if config.provider == "openai":
            from openai import OpenAI
            return OpenAIClient(OpenAI(), config)
        elif config.provider == "anthropic":
            import anthropic
            return AnthropicClient(anthropic.Anthropic(), config)
        else:
            raise ValueError(f"Unknown provider: {config.provider}")

    @abstractmethod
    def required_inputs(self) -> list[str]:
        """本棒必读的产物文件"""
        ...

    @abstractmethod
    def produced_outputs(self) -> list[str]:
        """本棒必写的产物文件"""
        ...

    @abstractmethod
    def forbidden_actions(self) -> list[str]:
        """不许做的事"""
        ...

    @abstractmethod
    def build_prompt(self, context: dict) -> str:
        """构建本 Agent 的 prompt"""
        ...

    def run(self, context: dict) -> dict:
        """执行本棒：校验输入 -> 构建 prompt -> 调 LLM -> 校验输出"""
        self._validate_inputs(context)
        prompt = self.build_prompt(context)
        response = self.llm.chat(prompt)
        self._validate_outputs(response)
        return response

    def _validate_inputs(self, context: dict):
        """校验必读文件是否齐全"""
        for req in self.required_inputs():
            if req not in context:
                raise ValueError(f"[{self.config.name}] 缺少必读输入: {req}")

    def _validate_outputs(self, response: dict):
        """校验必写产物是否齐全"""
        for out in self.produced_outputs():
            if out not in response:
                raise ValueError(f"[{self.config.name}] 缺少必写产物: {out}")


class LLMClient(ABC):
    """统一 LLM 接口，屏蔽不同 provider 的差异"""
    @abstractmethod
    def chat(self, prompt: str) -> dict: ...


class OpenAIClient(LLMClient):
    def __init__(self, client, config: AgentConfig):
        self.client = client
        self.config = config

    def chat(self, prompt: str) -> dict:
        resp = self.client.chat.completions.create(
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content)


class AnthropicClient(LLMClient):
    def __init__(self, client, config: AgentConfig):
        self.client = client
        self.config = config

    def chat(self, prompt: str) -> dict:
        resp = self.client.messages.create(
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(resp.content[0].text)
```

### 3.4 各 Agent 实现

```python
# agents/requirement.py

class RequirementAgent(BaseAgent):
    """需求 Agent：TAPD 链接 -> 结构化需求理解 + 影响半径分析"""

    def required_inputs(self):
        return ["tapd_ticket", "prd_text"]

    def produced_outputs(self):
        return ["requirement_doc", "impact_map"]

    def forbidden_actions(self):
        return ["写技术方案", "改 TAPD 单状态"]

    def build_prompt(self, context):
        prd = context["prd_text"]
        return f"""你是需求分析 Agent。你的职责是把模糊的 PRD 转成结构化的需求理解文档。

【输入】TAPD 单内容：
{prd}

【任务】
1. 逐条提取功能点，标注"明确"或"模糊"
2. 对模糊点生成追问清单
3. 跑 PRD 完整性自评（5 维度 0~100 分）
4. 做影响半径分析：涉及哪些子仓库、哪些接口、哪些协议字段

【纪律】
- 不许写技术方案
- 不许改 TAPD 单状态
- 只产出需求理解文档和影响地图

【输出 JSON 格式】
{{
  "requirement_doc": "...",
  "impact_map": {{"sub_repos": [], "interfaces": [], "protocol_fields": []}},
  "prd_score": {{"completeness": 0, "clarity": 0, "testability": 0, "boundary": 0, "priority": 0}},
  "questions": []
}}
"""
```

```python
# agents/solution.py

class SolutionAgent(BaseAgent):
    """方案 Agent：需求 -> 可执行的技术方案"""

    def required_inputs(self):
        return ["requirement_doc", "impact_map"]

    def produced_outputs(self):
        return ["design_doc", "tech_spec", "task_list"]

    def forbidden_actions(self):
        return ["改需求理解文档", "直接写代码"]

    def build_prompt(self, context):
        return f"""你是技术方案 Agent。你的职责是把需求理解转成可执行的技术方案。

【必读】
需求理解文档：
{context["requirement_doc"]}

影响地图：
{context["impact_map"]}

【任务】
1. 基于影响地图，确定改哪些子仓库、哪些服务、哪些协议字段
2. 输出设计文档（架构变更 + 接口变更 + 数据变更）
3. 输出技术规约（命名约定 + 错误码 + 事务边界）
4. 输出任务清单（可勾选的 checklist）

【纪律】
- 不许改需求理解文档（发现问题只能提阻塞项）
- 不许直接写代码

【输出 JSON 格式】
{{
  "design_doc": "...",
  "tech_spec": "...",
  "task_list": [{{"id": "T1", "desc": "...", "repo": "...", "done": false}}]
}}
"""
```

```python
# agents/developer.py

class DeveloperAgent(BaseAgent):
    """开发 Agent：按设计落代码 + 接口测试"""

    def required_inputs(self):
        return ["requirement_doc", "design_doc", "tech_spec", "task_list"]

    def produced_outputs(self):
        return ["code_diff", "unit_tests", "api_test_cases", "api_test_code"]

    def forbidden_actions(self):
        return ["超出设计文档计划范围", "改设计文档"]

    def build_prompt(self, context):
        return f"""你是开发 Agent。你的职责是按设计方案落代码。

【必读】
设计文档：{context["design_doc"]}
技术规约：{context["tech_spec"]}
任务清单：{context["task_list"]}

【任务】
1. 按任务清单逐项实现代码
2. 为每个服务方法写单元测试（mock 框架 + 函数打桩）
3. 产出接口用例文档
4. 产出增量 Go 接口测试代码

【纪律】
- 不许超出设计文档计划范围
- 让产生问题的人同时产生验证手段

【输出 JSON 格式】
{{
  "code_diff": "...",
  "unit_tests": "...",
  "api_test_cases": "...",
  "api_test_code": "...",
  "task_checklist": [{{"id": "T1", "done": true}}]
}}
"""
```

```python
# agents/reviewer.py

class ReviewerAgent(BaseAgent):
    """代码审查 Agent：4 维度收口"""

    def required_inputs(self):
        return ["requirement_doc", "design_doc", "tech_spec",
                "code_diff", "unit_tests", "api_test_code"]

    def produced_outputs(self):
        return ["review_report"]

    def forbidden_actions(self):
        return ["改代码", "改任何上游产物"]

    def build_prompt(self, context):
        return f"""你是代码审查 Agent。你的职责是从 4 个维度做最终收口。

【必读】全部上游产物 + git diff：
需求理解：{context["requirement_doc"]}
设计文档：{context["design_doc"]}
代码变更：{context["code_diff"]}
单测：{context["unit_tests"]}
接口测试：{context["api_test_code"]}

【审查 4 维度】
1. 方案一致性：实现是否真的按设计走？有没有偷偷加范围外的东西？
2. 验收标准覆盖：每条验收标准是否都有对应代码 + 测试？
3. 质量基线：接口测试是否完整？覆盖率是否达标？错误处理是否合规？
4. 前端增量（条件触发）：涉及前端时按审查模板输出阻塞项

【纪律】
- 不许改代码，只能产出阻塞项
- 你用的是与开发不同的模型，天然有不同的关注点偏好

【输出 JSON 格式】
{{
  "review_report": "...",
  "blocking_items": [{{"dimension": "方案一致性", "severity": "high", "desc": "..."}}],
  "pass": false
}}
"""
```

### 3.5 总控 Agent + 状态机

```python
# agents/orchestrator.py

class OrchestratorAgent(BaseAgent):
    """总控 Agent：状态机调度，不做认知工作"""

    STAGES = [
        "init",               # 初始化
        "requirement",        # 需求分析
        "req_confirm",        # 需求确认 (人工)
        "bug_repro",          # Bug复现 (条件)
        "solution",           # 技术方案
        "sol_confirm",        # 方案确认 (人工)
        "sol_review",         # 方案评审 (人工)
        "branch_prep",        # 分支准备
        "develop",            # 开发
        "integration_test",   # 集成测试
        "code_review",        # 代码审查
        "acceptance",         # 验收
        "delivery",           # 交付收尾
    ]

    def required_inputs(self): return []
    def produced_outputs(self): return ["checkpoint", "metrics_report"]
    def forbidden_actions(self): return ["做认知工作", "写代码", "写方案"]

    def build_prompt(self, context):
        return f"""你是流程调度器。
当前阶段：{context.get("current_stage")}
上一棒结果：{context.get("last_result", "无")}

根据以下规则决定下一阶段：
- 需求分析通过 -> 需求确认
- 需求确认"确认继续" -> 技术方案（或 Bug复现 if bugfix）
- 方案通过 -> 方案确认（跨仓库时弹）
- 开发完成 -> 集成测试（硬门禁）
- 集成测试失败 -> 打回开发
- 代码审查不通过 -> 打回开发 或 打回方案
- 连续打回>=3次 -> 熔断暂停（人工介入）

只输出下一阶段名称。
"""
```

```python
# workflow/state_machine.py

class WorkflowStateMachine:
    """13 阶段接力赛状态机"""

    # 打回规则表：失败 -> 回退到哪个阶段
    ROLLBACK_MAP = {
        "integration_test": "develop",      # 集成测试失败 -> 回开发
        "code_review": "develop",           # 代码审查失败 -> 回开发
        "sol_review_fail": "solution",      # 方案评审失败 -> 回方案
        "req_clarify": "requirement",       # 需求要改 -> 回需求
    }

    # 人工关卡
    HUMAN_GATES = {"req_confirm", "sol_confirm", "sol_review"}

    def __init__(self, agents: dict, gates: dict, mcp: dict):
        self.agents = agents
        self.gates = gates
        self.mcp = mcp
        self.context = {}       # 跨阶段共享的产物
        self.rollback_count = 0

    def run(self, tapd_url: str):
        """跑完整条接力赛"""
        stage = "init"

        while stage != "done":
            print(f"[状态机] 当前阶段: {stage}")

            if stage in self.HUMAN_GATES:
                approved = self._human_gate(stage)
                if not approved:
                    stage = self._rollback(stage)
                    continue
                stage = self._next_stage(stage)
                continue

            stage = self._execute_stage(stage)

            if stage == "blocked":
                self.rollback_count += 1
                if self.rollback_count >= 3:
                    print("[熔断] 连续打回>=3次，暂停等待人工介入")
                    return
                continue

        print("[完成] 交付收尾完成")

    def _execute_stage(self, stage: str) -> str:
        """执行单个阶段，返回下一阶段或 'blocked'"""
        if stage == "init":
            self._do_init()
            return "requirement"

        elif stage == "requirement":
            result = self.agents["requirement"].run(self.context)
            self.context.update(result)
            return "req_confirm"

        elif stage == "solution":
            result = self.agents["solution"].run(self.context)
            self.context.update(result)
            return "sol_confirm"

        elif stage == "develop":
            self.gates["baseline"].snapshot()       # 先跑基线快照
            result = self.agents["developer"].run(self.context)
            self.context.update(result)
            if not self._run_gates(["coverage", "lint"]):
                return "blocked"
            return "integration_test"

        elif stage == "integration_test":
            if not self.gates["integration_test"].run(self.context):
                self._rollback_to("develop")
                return "blocked"
            return "code_review"

        elif stage == "code_review":
            result = self.agents["reviewer"].run(self.context)
            if not result.get("pass"):
                self._rollback_to("develop")
                return "blocked"
            self.context["review_report"] = result["review_report"]
            return "acceptance"

        elif stage == "acceptance":
            new_failures = self.gates["diff_compare"].compare()
            if new_failures:
                self._rollback_to("develop")
                return "blocked"
            return "delivery"

        elif stage == "delivery":
            self._do_delivery()
            return "done"

        return "blocked"

    def _do_init(self):
        self.mcp["tapd"].update_status(self.context["tapd_id"], "DOING")
        self.mcp["tapd"].add_label(self.context["tapd_id"], "harness")

    def _do_delivery(self):
        self.mcp["gongfeng"].create_mr()
        self.mcp["iwiki"].upload_artifacts()
        self.mcp["tapd"].update_status(self.context["tapd_id"], "DONE")
        self.mcp["wework"].notify()

    def _human_gate(self, stage: str) -> bool:
        """人工关卡：三级兜底（UI按钮 / 纯文本 / 语义识别）"""
        ...

    def _rollback(self, current: str) -> str:
        return self.ROLLBACK_MAP.get(current, "init")

    def _next_stage(self, current: str) -> str:
        idx = OrchestratorAgent.STAGES.index(current)
        return OrchestratorAgent.STAGES[idx + 1]
```

### 3.6 门禁脚本：基线对比

```python
# gates/diff_compare.py

class BaselineComparator:
    """反作弊设计：剥夺 AI 的解释权"""

    def snapshot(self):
        """开发前跑一次，冻结当前门禁状态为基线"""
        self.baseline_failures = self._run_all_gates()

    def compare(self) -> list:
        """开发后跑一次，算新增失败 = B - A"""
        current_failures = self._run_all_gates()
        new_failures = current_failures - self.baseline_failures
        # 只有新增的失败才阻断流程
        # "历史问题"这把万能钥匙被拿掉了
        return new_failures

    def _run_all_gates(self) -> set:
        failures = set()
        failures |= self.gates["lint"].run()
        failures |= self.gates["coverage"].run()
        failures |= self.gates["integration_test"].run()
        return failures
```

### 3.7 入口

```python
# main.py

import yaml
from agents.base import AgentConfig
from agents.orchestrator import OrchestratorAgent
from agents.requirement import RequirementAgent
from agents.solution import SolutionAgent
from agents.developer import DeveloperAgent
from agents.reviewer import ReviewerAgent
from workflow.state_machine import WorkflowStateMachine


def load_agent_config(name: str) -> AgentConfig:
    with open("config/models.yaml") as f:
        cfg = yaml.safe_load(f)
    a = cfg["agents"][name]
    return AgentConfig(name=name, **a)


def main():
    # 各 Agent 使用各自配置的大模型
    agents = {
        "orchestrator": OrchestratorAgent(load_agent_config("orchestrator")),
        "requirement":  RequirementAgent(load_agent_config("requirement")),
        "solution":     SolutionAgent(load_agent_config("solution")),
        "developer":    DeveloperAgent(load_agent_config("developer")),
        "reviewer":     ReviewerAgent(load_agent_config("reviewer")),
    }

    gates = load_gates()
    mcp = load_mcp()

    sm = WorkflowStateMachine(agents, gates, mcp)
    sm.run(tapd_url="https://tapd.tencent.com/...")
```

---

## 四、关键设计决策总结

### 4.1 为什么不同 Agent 用不同大模型

| 设计决策 | 理由 |
|---------|------|
| 开发用 Claude，审查用 GPT-4o | 模型层面的天然制衡：不同模型对同一段代码的"审美偏好"不同，能抓出更多"方案一致性"偏差。文章强调"不能让写代码的 Agent 自己审自己"，跨模型族审查把这个原则从 Agent 层面延伸到了模型层面。 |
| 总控用 GPT-4o-mini | 总控只做状态机跳转和路由，不需要深度推理。用轻量模型降低成本和延迟，同时避免"总控也想做认知工作"的越界。 |
| 需求用 GPT-4o，方案用 Claude | 需求理解偏语义解析 + 主动提问（GPT-4o 的强项），方案设计偏深度推理 + 长上下文分析（Claude 3.5 Sonnet 的强项）。各取所长。 |
| 方案和开发都用 Claude | 方案设计产出物直接喂给开发 Agent，同模型族对方案的理解一致性更高，减少"方案写得对但开发理解偏了"的问题。 |

### 4.2 编排模式选择

文章从 Team Mode 撞墙中总结的核心经验：

- 用同步阻塞调用，不用 Team Mode。4 个 spawn 点全部是串行单个模式，从未用过并行/互发消息/长驻留。Team Mode 带来的复杂度只是为了解决它自己引入的问题，这是"复杂度自给自足"陷阱。
- 能写成 bash 的就别让 Agent 跑。流程调度、门禁、测试、提 MR 全部下沉成确定性脚本。
- 接力关系，不是协商关系。每一棒交什么、下一棒接到什么才能开跑、跑砸了回到哪一棒。

### 4.3 文章原话提炼的金句

- AI 的瓶颈早就不是模型，是协作、流程、信任。
- 下游能改上游，整条流程的责任边界就崩了。
- 能写脚本的就别让 AI 解释执行。4 个 Agent 不是设计出来的，是被"什么不该 AI 干"逼出来的。
- 你不能阻止 AI 偷懒，但你可以剥夺它的解释权（基线对比），让偷懒变得很醒目（软门禁伤疤）。
- 半自动比全自动更难，但更值得做。它是当前 AI 能力下唯一稳定可推广的形态。

---

## 五、落地路径建议

1. 先跑通开发闭环（需求 -> 方案 -> 开发 -> 集成测试 -> 代码审查），不接 MCP。
2. 再加门禁脚本（覆盖率 + lint + 集成测试），建立基线对比。
3. 再加人工关卡（需求确认 + 方案确认），设三级兜底。
4. 最后接 MCP（TAPD + iWiki + 工蜂 + 企微），把开发闭环扩展成交付闭环。
5. 全程落地到仓库：所有规范、流程定义、Skill 文档、演进日志都在 git 里，不用 Memory。
