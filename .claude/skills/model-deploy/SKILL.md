---
name: model-deploy
description: "当用户需要部署模型到算法仓库时使用。支持创建新模型、上传 zip 到 OSS、提交代码到 gas-match-auto-opt 仓库。"
---

# 模型部署

通过 MCP 工具将优化模型部署到 `gas-match-auto-opt` 算法仓库。

## 可用 MCP 工具

| 工具名 | 功能 | 是否修改数据 |
| --- | --- | --- |
| `create_model` | 创建新模型，返回模型 ID | 是 |
| `upload_model_zip` | 上传本地 zip 文件到 OSS，返回 OSS 地址 | 是 |
| `commit_model` | 将 OSS 上的模型代码提交到算法仓库 | 是 |

## 部署流程

按顺序执行以下步骤，每一步的输出作为下一步的输入。每步完成后记录关键信息，最终写入 `deploy-records.json` 用于追溯。

### 1. 创建模型

```
工具: create_model
必填:
  - modelName: 模型名称（由大模型生成）
```

记录返回的：`modelId`、`modelCode`、`modelName`、`url`、`schemeMd5`、`当前环境`。

### 2. 打包并上传模型 zip

先打包 runtime 目录下的内容（注意不要打包 runtime 目录本身）：

```bash
# 正确做法：进入 runtime 目录，打包其内容
cd runtime && zip -r ../model.zip . && cd ..
```

错误做法：`zip -r model.zip runtime/` —— 这会导致解压后多一层 `runtime/` 目录。

然后上传：

```
工具: upload_model_zip
必填:
  - filePath: zip 文件的本地路径（如 ../model.zip 或绝对路径）
```

记录返回的：`OSS 地址`（ossUrl）。

### 3. 提交代码

```
工具: commit_model
必填:
  - modelId: 步骤 1 返回的模型 ID
  - ossUrl: 步骤 2 返回的 OSS 地址
```

记录返回的：`Git URL`（gitUrl）、`批次号`（batchNo）。

### 4. 写入部署记录

将以上所有信息追加写入项目根目录的 `deploy-records.json`：

```json
{
  "time": "<ISO 8601 时间戳>",
  "env": "<当前环境>",
  "modelId": "<步骤1的模型ID>",
  "modelCode": "<步骤1的模型编码>",
  "modelName": "<步骤1的模型名称>",
  "url": "<步骤1的服务地址>",
  "schemeMd5": "<步骤1的schemeMd5>",
  "ossUrl": "<步骤2的OSS地址>",
  "gitUrl": "<步骤3的Git地址>",
  "batchNo": "<步骤3的批次号>"
}
```

文件为 JSON 数组格式（追加到末尾）。首次部署时创建文件并写入 `[]` 初始数组。

## 注意事项

- `create_model` 和 `commit_model` 会修改数据，执行前应向用户确认
- 生产环境部署需格外谨慎，确认无误后再执行
- 部署记录写入 `deploy-records.json`，便于后续追溯每次部署的完整链路
