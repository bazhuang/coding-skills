# CBM CLI 调用契约

> 适用版本：`codebase-memory-mcp >= 0.9.0`；当前核对版本为 0.10.0。
> 本契约只约束 repo-wiki 的可选事实提取，不扩展现有扫描器或验证门禁。

## 调用与降级

所有命令以参数数组直接调用，不经过 shell：

```text
["codebase-memory-mcp", "cli", "<tool>", "--<flag>", "<value>", ...]
```

命令退出码非 0、超时、stdout 非 JSON 对象、响应含 `error`、daemon/索引不可用，均视为 CBM 不可用。提取脚本输出标准降级结果并以 exit 0 结束，不阻断 repo-wiki 原流程。

## 使用的命令

| 工具 | 参数 | 消费字段 |
|---|---|---|
| `--version` | 无 `cli` 子命令 | 首个 `major.minor.patch`；低于 0.9.0 时降级 |
| `index_repository` | `--repo-path <绝对路径> --mode fast --name <项目名>` | `project`、`status`、`skipped_count`、`excluded`；后续查询使用响应中的实际 `project` |
| `get_architecture` | `--project <项目名> --aspects '["overview"]'` | `hotspots[].qualified_name`；只在能补齐源码位置时生成事实 |
| `search_graph` | `--project <项目名> --name-pattern <正则> --fields '["route_path","route_method"]'` | `results[].qualified_name/label/file_path/route_path/route_method`，用于按入口文件、路由和 HTTP 方法解析真实处理函数；路由字段不是核心列，必须显式请求 |
| `trace_path` | `--project <项目名> --function-name <qualified_name> --direction outbound --depth 3` | `callees[].qualified_name/hop` |
| `get_code_snippet` | `--project <项目名> --qualified-name <qualified_name>` | `file_path/start_line/end_line`，为每条图谱事实补齐可验证证据 |

## 数据约束

- CLI JSON 顶层必须是对象；数组、字符串、数字和 `null` 均按无效响应降级。
- 图谱事实的每条 evidence 必须包含仓库相对 `source` 和正整数 `line`；仓库外路径、缺失位置和不可解析节点不得进入事实层。
- API 扫描器的 `symbol` 可能是注解名（如 `HelloController#GetMapping`），不能据此构造处理函数。此时必须使用 `search_graph`，并同时按入口文件、`route_path` 和 `route_method` 消歧；无法唯一解析时跳过该入口。
- `trace_path` 不提供源码位置，必须逐节点通过 `get_code_snippet` 补齐。
- 架构摘要不直接转为 observed 事实；当前仅提取可定位的热点和调用链。

## 索引范围

CBM fast/moderate 模式内置跳过名为 `scripts` 的目录。若目标仓库需要分析该目录，在仓库根 `.cbmignore` 中用否定规则重新纳入，例如：

```gitignore
!/skills/repo-wiki/scripts/
```

该规则只影响 CBM 索引范围，不改变 repo-wiki 自身的文件扫描规则。

## 验收边界

仓库内单元测试只使用内联 mock 验证命令参数、响应解析、证据约束和降级语义，不维护测试应用。真实准确性由用户在现有 Java/Spring 项目中分别启动和关闭 CBM 后进行 A/B 对比。
