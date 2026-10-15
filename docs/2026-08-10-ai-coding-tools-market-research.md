# AI Coding 工具市场调研报告

> 调研时间：2026年8月  
> 调研背景：团队正在评估 AI Coding 工具选型，当前与智谱洽谈 GLM Coding Plan 采购

---

## 一、工具概览对比表

### A 组：国内厂商工具

| 工具 | 厂商 | 类型 | 流行度 | 定价 | 模型 | GLM兼容 |
|------|------|------|--------|------|------|---------|
| **Qoder CN（通义灵码）** | 阿里 | IDE插件+CLI+Agent | 国内市场份额47.6%（IDC） | Credits制，2026.5.20更新定价 | Qwen3系列 | 否（自有模型） |
| **Qwen Code** | 阿里 Qwen团队 | 开源CLI Agent | GitHub 25K+ stars | 免费(开源)+API费用，Coding Plan $50/月 | Qwen3-Coder为主，支持60+供应商 | 可通过OpenAI兼容接口 |
| **Trae** | 字节跳动 | AI-Native IDE | 增长迅速，国内外均有用户 | 免费/$3/$10月 | 国际版:Claude/GPT；国内版:Doubao/DeepSeek | 否 |
| **豆包 MarsCode** | 字节跳动 | IDE插件+Cloud IDE | 免费用户群体大，初学者友好 | 免费 | 豆包大模型 | 否 |
| **ZCode** ⭐ | 智谱 (Z.ai) | AI-Native IDE | 2026.7发布，新工具 | GLM Coding Plan $18-$160/月 | GLM-5.2（原生绑定） | 原生支持 |
| **MiMo Code** | 小米 | 开源CLI Agent | 2026.6开源，MIT | 免费+Token Plan | MiMo-V2.5-Pro为主 | 可通过OpenAI兼容接口 |
| **百度 Comate** | 百度 | IDE插件 | Comate 4.0已发布 | 免费/企业版 | 文心大模型 | 否 |
| **DevEco Code** | 华为 | CLI Agent (OpenCode fork) | HDC 2026发布 | 免费(GLM-5.1) | 毕方大模型+GLM | 支持（使用GLM） |

### B 组：国际主流工具

| 工具 | 厂商 | 类型 | 流行度 | 定价 | 模型 | GLM兼容 |
|------|------|------|--------|------|------|---------|
| **Cursor** | Anysphere | AI-Native IDE | 估值$50B，ARR $500M+ | $20/月(Pro) | Composer 2.5(Kimi K2.5)+Claude/GPT | 可通过OpenAI兼容接口 |
| **GitHub Copilot** | Microsoft | IDE插件 | 市占率68%（SO调研） | $0-$39/月(个人)，$19-$39/seat(企业) | GPT系列+Claude+Gemini | 否（封闭模型选择） |
| **Claude Code** | Anthropic | CLI Agent | 132K+ GitHub stars | $20-$200/月(捆绑Claude订阅) | Claude Opus 4.8/5系列 | 可通过Anthropic协议转接 |
| **OpenAI Codex CLI** | OpenAI | CLI Agent | 绑定ChatGPT生态 | $20-$200/月(捆绑ChatGPT订阅) | GPT-5.3-Codex | 否 |
| **Kiro** | AWS | AI-Native IDE | 2026新发布 | $19-$100/月 | Claude Opus/Sonnet+GPT-5.6 | 否（封闭模型选择） |

### C 组：开源 / BYOK 工具

| 工具 | 协议 | 类型 | 流行度 | 定价 | 模型支持 | GLM兼容 |
|------|------|------|--------|------|----------|---------|
| **OpenCode** | MIT | CLI+Desktop+IDE扩展 | 195K+ stars，16M月活 | 免费(开源)+API费用 | 75+供应商，任意OpenAI兼容 | ✅ GLM Coding Plan官方支持 |
| **Cline** | Apache-2.0 | VS Code/JetBrains扩展 | 60K+ stars | 免费(开源)+API费用 | BYOK，任意OpenAI/Anthropic兼容 | ✅ GLM Coding Plan官方支持 |
| **Kilo Code** | MIT | VS Code/JetBrains扩展 | 20K stars，150万+用户 | 免费(开源)+API费用 | 500+模型，BYOK | ✅ 通过OpenAI兼容接口 |
| **Gemini CLI** | Apache-2.0 | CLI Agent | 100K+ stars | 2026.6.18后免费层取消 | Gemini系列 | 否（仅Gemini） |
| **Aider** | Apache-2.0 | CLI Agent | 39K+ stars | 免费(开源)+API费用 | 任意OpenAI/Anthropic兼容+Ollama | ✅ 通过OpenAI兼容接口 |

---

## 二、维度详细评估

### 1. 流行度

| 梯队 | 工具 | 关键指标 |
|------|------|----------|
| **T0 顶流** | GitHub Copilot | 68%开发者使用率(SO 2025)，最大装机量 |
| **T0 顶流** | Qoder CN（通义灵码） | 国内市场份额47.6%(IDC)，国内第一 |
| **T1 一线** | Cursor | 估值$50B，ARR $500M+，AI IDE标杆 |
| **T1 一线** | OpenCode | 195K stars，16M月活，开源第一 |
| **T1 一线** | Claude Code | 132K stars，10%+ GitHub公开commits |
| **T2 主流** | Gemini CLI | 100K+ stars（但免费层已取消） |
| **T2 主流** | Cline | 60K+ stars，VS Code Agent先驱 |
| **T2 主流** | Trae | 增长快，字节推广力度大 |
| **T3 新锐/垂直** | ZCode、MiMo Code、Kilo Code、Aider、Kiro 等 | 各有特色但规模较小 |

### 2. Harness 工程完成度

| 工具 | SWE-bench相关得分 | Agent能力 | 多文件重构 | 自主规划 | 评价 |
|------|-------------------|-----------|------------|----------|------|
| **Claude Code** | 88.6% Verified (Opus 4.8) | ⭐⭐⭐⭐⭐ | 强 | 强 | 当前最强harness |
| **Cursor** | Composer 2.5 ~79.8% Multilingual | ⭐⭐⭐⭐⭐ | 强 | 强 | IDE内最强体验 |
| **OpenAI Codex** | GPT-5.3-Codex ~85% Verified | ⭐⭐⭐⭐ | 强 | 强 | 4x token效率 |
| **ZCode** | GLM-5.2: 62.1% Pro | ⭐⭐⭐⭐ | 中 | Goal Mode | 性价比突出 |
| **OpenCode** | 取决于接入模型 | ⭐⭐⭐⭐ | 强 | Plan/Build模式 | harness层优秀 |
| **Cline** | 取决于接入模型 | ⭐⭐⭐⭐ | 强 | 计划-审批流 | 成熟稳定 |
| **Qoder CN** | Qwen3-Coder系列 | ⭐⭐⭐⭐ | 强 | Agent模式 | 国内最完整 |
| **MiMo Code** | MiMo-V2-Pro 78% Verified | ⭐⭐⭐⭐ | 强 | 持久记忆系统 | 长任务优势 |
| **Trae** | 取决于模型选择 | ⭐⭐⭐ | 中 | SOLO Mode | 绿地项目好用 |
| **GitHub Copilot** | ~56% Verified | ⭐⭐⭐ | 中 | Agent Mode | 覆盖广但深度一般 |
| **Kiro** | 取决于模型选择 | ⭐⭐⭐⭐ | 强 | Spec驱动 | 结构化开发流 |

### 3. 数据安全性

| 安全等级 | 工具 | 关键安全特性 |
|----------|------|--------------|
| **🟢 最安全（可完全本地/自托管）** | OpenCode、Cline、Kilo Code、Aider、MiMo Code | 开源可审计，BYOK，数据不出本地，可接本地模型(Ollama) |
| **🟢 国内合规** | Qoder CN、ZCode、百度Comate、DevEco Code、豆包MarsCode | 数据存国内服务器，符合国内数据合规 |
| **🟡 有条件安全** | Cursor | 企业版零数据留存，但代码经云端处理 |
| **🟡 有条件安全** | GitHub Copilot | 企业版不用于训练，SOC2认证 |
| **🟡 有条件安全** | Kiro | AWS基础设施，地理区域内处理 |
| **🟡 需注意** | Trae | ByteDance遥测收集，个人数据保留5年，无opt-out |
| **🔴 数据出境风险** | Claude Code、OpenAI Codex | 数据传输至海外，需评估合规风险 |

**重要提示**：对于使用 GLM Coding Plan + 开源工具（如 Cline/OpenCode）的方案，代码通过 Z.ai API 处理，数据存储在国内智谱服务器，合规风险低。

### 4. 大模型适配度

| 工具 | 模型自由度 | GLM支持 | 国产模型支持 | 本地模型 | BYOK |
|------|-----------|---------|-------------|----------|------|
| **OpenCode** | ⭐⭐⭐⭐⭐ | ✅ 官方支持 | Qwen/GLM/DeepSeek/MiMo | ✅ Ollama | ✅ |
| **Cline** | ⭐⭐⭐⭐⭐ | ✅ 官方支持 | 全部OpenAI兼容 | ✅ Ollama | ✅ |
| **Kilo Code** | ⭐⭐⭐⭐⭐ | ✅ OpenAI兼容 | 500+模型 | ✅ | ✅ |
| **Aider** | ⭐⭐⭐⭐⭐ | ✅ OpenAI兼容 | 全部兼容接口 | ✅ Ollama | ✅ |
| **Qwen Code** | ⭐⭐⭐⭐ | ✅ OpenAI兼容 | Qwen+60+供应商 | ✅ | ✅ |
| **MiMo Code** | ⭐⭐⭐⭐ | ✅ OpenAI兼容 | MiMo+多供应商 | ✅ | ✅ |
| **Cursor** | ⭐⭐⭐⭐ | ✅ OpenAI兼容 | 可配置 | 有限 | 部分 |
| **ZCode** | ⭐⭐ | ✅ 原生 | 仅GLM系列 | 否 | 否 |
| **Trae** | ⭐⭐⭐ | 否 | Doubao/DeepSeek(国内版) | 否 | 否 |
| **GitHub Copilot** | ⭐⭐ | 否 | 否 | 否 | 否 |
| **Claude Code** | ⭐ | 可转接 | 需第三方路由 | 否 | 否 |
| **OpenAI Codex** | ⭐ | 否 | 否 | 否 | 否 |

### 5. 定价与 Token Plan 适配

| 工具 | 月费 | 能否接入外部Token Plan | GLM Coding Plan适配 | 性价比评价 |
|------|------|------------------------|---------------------|-----------|
| **ZCode** | $18-$160(GLM Plan) | 原生绑定 | ⭐⭐⭐⭐⭐ 原生 | 最直接 |
| **OpenCode** | 免费(工具)+API | ✅ | ⭐⭐⭐⭐⭐ 官方支持 | 极高 |
| **Cline** | 免费(工具)+API | ✅ | ⭐⭐⭐⭐⭐ 官方支持 | 极高 |
| **Kilo Code** | 免费(工具)+API | ✅ | ⭐⭐⭐⭐ OpenAI兼容 | 极高 |
| **Aider** | 免费(工具)+API | ✅ | ⭐⭐⭐⭐ OpenAI兼容 | 极高 |
| **DevEco Code** | 免费 | 内置GLM | ⭐⭐⭐⭐ 内置支持 | 高（鸿蒙限定） |
| **Cursor** | $20/月+用量 | 可配置自定义endpoint | ⭐⭐⭐ 需手动配置 | 中（叠加订阅费） |
| **Trae** | $0-$10/月 | 否 | ❌ | 高（自有模型免费） |
| **GitHub Copilot** | $10-$39/月 | 否 | ❌ | 中 |
| **Claude Code** | $20-$200/月 | 可转接但非官方 | ⭐⭐ 非官方 | 低（重复付费） |
| **OpenAI Codex** | $20-$200/月 | 否 | ❌ | 低 |

### 6. IDE 集成与 MCP 支持

| 工具 | VS Code | JetBrains | 终端CLI | MCP协议 | 其他 |
|------|---------|-----------|---------|---------|------|
| **Qoder CN** | ✅ | ✅ | ✅(Qoder CLI) | ✅ | 独立Desktop |
| **Cursor** | ✅(fork) | 否 | 否 | ✅ | 独立IDE |
| **ZCode** | 否 | 否 | 否 | ✅ | 独立Desktop |
| **Trae** | ✅(fork) | 否 | 否 | ✅ | 独立IDE |
| **OpenCode** | ✅(扩展) | 否 | ✅ | ✅ | Desktop App |
| **Cline** | ✅ | ✅ | 否 | ✅ | Neovim/Zed |
| **Kilo Code** | ✅ | ✅ | ✅ | ✅ | 云Agent |
| **GitHub Copilot** | ✅ | ✅ | ✅ | 有限 | 6+ IDE |
| **Claude Code** | 否 | 否 | ✅ | ✅ | VS Code扩展(社区) |
| **Kiro** | ✅(fork) | 否 | ✅ | ✅ | Web App |
| **Aider** | 否 | 否 | ✅ | 否 | 纯CLI |
| **MiMo Code** | 否 | 否 | ✅ | ✅ | Desktop App |

---

## 三、智谱 GLM Coding Plan 适配分析

### Plan 详情

| 层级 | 月费 | 5小时额度(Credits) | 周额度(Credits) | 预估周Token量(GLM-5.2) |
|------|------|-------------------|-----------------|------------------------|
| **Lite** | $18/月 | 2,000 | 10,000 | 43-87M tokens |
| **Pro** | 未公开(推测~$60) | 12,000 | 60,000 | 263-526M tokens |
| **Max** | 未公开(推测~$160) | 28,000 | 140,000 | 613-1226M tokens |

### 支持的模型

- GLM-5.2（旗舰，744B MoE，1M上下文）
- GLM-5-Turbo
- GLM-4.7

### 官方支持的工具

| 工具 | 接入协议 | 配置难度 | 备注 |
|------|----------|----------|------|
| **ZCode** | 原生 | 零配置 | 登录即用，1.5x额度加成 |
| **Claude Code** | Anthropic Messages | 低 | 替换base_url为api.z.ai |
| **Cline** | OpenAI Compatible | 低 | 官方文档有配置指南 |
| **OpenCode** | OpenAI Compatible | 低 | 官方支持 |
| **其他OpenAI兼容工具** | OpenAI Chat Completions | 中 | Cursor/Aider/Kilo Code等 |

### GLM-5.2 性能定位

- SWE-bench Pro: 62.1%（超越GPT-5.5的58.6%）
- 上下文窗口: 1M tokens
- 定价: $1.40/M input, $4.40/M output（约为Claude Opus的1/5-1/6）
- 开放权重: MIT协议，可自托管

---

## 四、场景推荐

### 推荐方案：GLM Coding Plan + 开源工具组合

基于团队正在采购智谱 Token Plan 的背景，推荐以下组合方案：

#### 方案 A：IDE 内开发（推荐）

```
GLM Coding Plan (Pro/Max) + Cline (VS Code/JetBrains插件)
```

- **优势**：IDE内无缝体验，计划-审批工作流，GLM官方支持，数据合规
- **适合**：日常开发、代码审查、重构

#### 方案 B：终端 Agent 开发

```
GLM Coding Plan (Pro/Max) + OpenCode (CLI)
```

- **优势**：最成熟的终端harness，Plan/Build模式，195K stars社区，GLM官方支持
- **适合**：复杂工程任务、CI/CD集成、批量操作

#### 方案 C：一体化体验

```
GLM Coding Plan + ZCode
```

- **优势**：零配置、原生GLM绑定、1.5x额度加成、Goal Mode
- **劣势**：新工具生态不成熟、仅绑定GLM无法切换、IDE锁定
- **适合**：想要最简配置且完全依赖GLM的场景

#### 方案 D：混合策略（推荐大团队）

```
GLM Coding Plan + Cline/OpenCode (日常) + Cursor (复杂任务备选)
```

- **优势**：日常用GLM控成本，复杂任务可切换Cursor Composer 2.5
- **适合**：对模型能力有分级需求的团队

### 不推荐的方案

| 方案 | 原因 |
|------|------|
| GitHub Copilot + GLM | Copilot不支持外部模型，重复付费 |
| Claude Code/Codex 作为主力 | 数据出境风险 + 无法接GLM Plan + 费用高 |
| Trae 企业使用 | 遥测问题 + 无法接GLM + 字节数据合规存疑 |
| ZCode 作为唯一工具 | 太新、生态不成熟、锁定单一模型 |

---

## 五、关键结论

1. **GLM Coding Plan 性价比突出**：GLM-5.2 在 SWE-bench Pro 上超越 GPT-5.5，但成本仅为Claude的1/5-1/6，适合作为团队主力模型

2. **开源工具 + GLM Plan 是最优解**：Cline/OpenCode 免费且 GLM 官方支持，团队只需支付 Plan 费用即可获得完整 AI Coding 能力

3. **数据安全可控**：GLM API 数据存储在国内智谱服务器，搭配开源可审计工具，合规风险最低

4. **建议分层使用**：
   - 日常补全/问答：GLM-5-Turbo（低成本，额度消耗少）
   - 复杂Agent任务：GLM-5.2（旗舰能力）
   - 非高峰时段执行大任务：可享50%额度折扣

5. **需关注的风险**：
   - GLM Coding Plan 额度制（5小时+周限制）可能在高强度使用时不够
   - ZCode 太新，建议观望而非作为唯一依赖
   - GLM-5.2 虽然SWE-bench Pro分数好，但在工程实践中体验可能不如Claude Code成熟的harness调优

---

## 六、数据来源

- IDC 中国 AI 编程市场报告 2026
- Stack Overflow Developer Survey 2025
- SWE-bench Verified/Pro Leaderboard (vals.ai, scale.com)
- Z.ai 官方文档 (docs.z.ai)
- 各工具官方定价页面
- 第三方评测：Digital Applied, Tech Insider, Vibecoding.app, codersera.com 等

> 本报告数据截至2026年8月，市场变化较快，建议定期更新。
