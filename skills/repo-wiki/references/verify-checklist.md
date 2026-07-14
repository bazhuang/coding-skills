# 验证检查清单（Verify Checklist）

> `verify_wiki.py` 脚本的文档对照。脚本执行检查，本文档说明每项的判定标准、软硬门禁取舍依据。

## 门禁类型定义

| 类型 | 行为 | 退出码 |
|---|---|---|
| **硬门禁** | 失败即中止流程，必须修复后才能继续 | exit 1 |
| **软门禁** | 失败留 warning 到 stderr 和状态文件，不阻断流程 | exit 0 + warning |

## 取舍依据

硬门禁宁少不多。如果一个东西不是质量红线，就别让它阻断流程。

- **硬门禁**只保留"产物缺失"和"格式严重错误"——这些意味着流程本身出了问题，不是内容质量问题。
- **软门禁**覆盖"内容丰富度"指标（图表数、引用数、表格数）——这些是质量建议，LLM 可能因为项目本身没有足够素材而无法满足，不应该阻断。

## 硬门禁项

| 检查项 | 判定逻辑 | 失败原因 |
|---|---|---|
| 概览页面存在 | docs/wiki/ 下存在文件名含"概览/概述/overview/introduction"关键词的 .md | LLM 生成的结构中缺少概览页面，或 export_wiki.py 未正确识别 |
| 每个页面文件存在 | 遍历 structure.json 中所有 page，检查 page_id_to_file 映射的文件路径是否存在 | 某页内容未生成（子 agent 失败或 LLM 漏生成） |
| 每页第一行为 H1 | 读取每个 .md 文件首行，必须以 `# ` 开头 | 子 agent 未按 page-content-prompt.md 的"关键起始指令"生成 H1 标题 |
| 文件名无非法字符 | 检查 docs/wiki/ 下所有文件名，不含 `/\:*?"<>\|` | sanitize_filename() 未正确清洗，或 LLM 直接写文件绕过脚本 |
| **代码块围栏完整** | 每个 ``` 必须有对应的闭合 ```，不能有未闭合的代码块 | LLM 生成时漏写闭合围栏，导致渲染失败 |
| **禁止裸语言标识符** | 禁止出现单独的 `mermaid`、`java`、`python` 等语言标识符（没有三反引号包裹） | LLM 只写了语言名而忘记加围栏，导致代码块无法渲染 |
| **Mermaid 方向限制** | Mermaid 图表只能使用 `graph TD` 或 `flowchart TD`，禁止 `LR`、`TB`、`BT` | LLM 使用了禁止的图表方向，导致图表显示异常 |

## 软门禁项

| 检查项 | 判定逻辑 | 阈值 | 软门禁原因 |
|---|---|---|---|
| Mermaid 图表 | 每页正则匹配 ` ```mermaid ` 代码块数量 | ≥ 1 | 小型项目可能确实没有可图表化的架构，不应阻断 |
| 源文件引用 | 每页正则匹配 `来源：[xxx](../../xxx)` 行，统计引用的不同文件数 | ≥ 5 | 某些页面可能只涉及 2-3 个文件（如部署页面），不应强制要求 5 个 |
| Markdown 表格 | 每页正则匹配 Markdown 表格语法 | ≥ 1 | 某些页面可能以图为主，不一定需要表格 |
| 页面间链接有效 | 正则匹配 `[xxx](xxx.md)`，检查目标文件是否存在 | 全部有效 | 链接失效影响导航体验但不影响内容正确性 |

## 脚本调用方式

```bash
python3 skills/repo-wiki/scripts/verify_wiki.py docs/tmp/wiki_structure.json --wiki-dir docs/wiki
```

## 输出

- 硬门禁失败：stderr 输出 `HARD GATE FAILED: <检查项> - <详情>`，exit 1
- 软门禁失败：stderr 输出 `SOFT GATE WARNING: <检查项> - <详情>`，exit 0
- 全部通过：stderr 输出 `All gates passed (N pages verified)`，exit 0
- 检查结果同时更新到 `docs/.wiki-state.yaml` 的 `verify` 字段
