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

按顺序执行以下三步，每一步的输出作为下一步的输入。

### 1. 创建模型

```
工具: create_model
必填:
  - modelName: 模型名称（由大模型生成）
```

记录返回的模型 ID。

### 2. 打包并上传模型 zip

先打包 runtime 目录下的内容（注意不要打包 runtime 目录本身）：

```bash
cd runtime && zip -r ../model.zip . && cd ..
```

然后上传：

```
工具: upload_model_zip
必填:
  - filePath: zip 文件的本地路径
```

记录返回的 OSS 地址。

### 3. 提交代码

```
工具: commit_model
必填:
  - modelId: 步骤 1 返回的模型 ID
  - ossUrl: 步骤 2 返回的 OSS 地址
```

提交成功后会返回 Git 仓库地址。

### 4. 记录部署信息

将本次部署的关键信息（时间、环境、模型ID、模型编码、模型名称、服务地址、schemeMd5、OSS地址、Git地址、批次号等）追加写入项目根目录的 `deploy-records.json`，便于后续追溯。

## 注意事项

- `create_model` 和 `commit_model` 会修改数据，执行前应向用户确认
- 生产环境部署需格外谨慎，确认无误后再执行
