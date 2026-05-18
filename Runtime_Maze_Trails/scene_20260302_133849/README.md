# 供需运筹模型运行态代码

## 生成信息
- 生成时间: 2026-03-02 13:41:28
- 场景ID: scene_20260302_133849

## 文件说明
- `standardized_input.json` - 标准化输入
- `dsl.json` - 建模DSL
- `data_loader.py` - 数据加载器
- `model_builder.py` - 模型构建器
- `main.py` - 主程序

## 运行方法

### 1. 安装依赖
```bash
pip install pandas numpy ortools  # 根据实际使用的求解器安装
```

### 2. 准备数据
数据源配置已在构建时嵌入代码，根据数据源类型准备数据：
- **CSV**: 将CSV文件放在当前目录下，文件名与表名对应
- **数据库（MySQL/PostgreSQL）**: 确保数据库可连接，连接信息已嵌入
- **Nebula图数据库**: 确保Nebula图数据库可连接，连接信息已嵌入

### 3. 运行模型
```bash
python main.py --version-id V20240127
```

**参数说明**:
- `--version-id`: （必填）数据版本ID，用于筛选业务数据
- `--config`: （可选）数据源配置文件路径，用于覆盖构建时嵌入的默认配置
- `--output-dir`: （可选）结果输出目录，默认为 `result/{timestamp}_{version_id}/`

**说明**:
- 数据源配置已在构建时嵌入代码，运行时无需额外配置文件
- `--config` 参数仅在需要临时切换数据源时使用
- 结果会自动保存在带时间戳的目录中，避免覆盖历史结果

**示例**:
```bash
# 使用默认输出目录（推荐，最常用）
python main.py --version-id V20240127

# 临时切换数据源配置
python main.py --version-id V20240127 --config custom_config.json

# 指定自定义输出目录
python main.py --version-id V20240127 --output-dir results/my_result
```

### 4. 查看结果
结果将保存在 `result/{timestamp}_{version_id}/` 目录下（默认）：

```
result/
└── 20260201_143025_V20240127/          # 时间戳_版本ID
    ├── data/                            # 数据文件夹
    │   ├── monthly_demand_pool.csv      # 需求表数据
    │   ├── monthly_resource_pool.csv    # 资源表数据
    │   ├── monthly_transport_pool.csv   # 运力表数据
    │   └── paths_V20240127.json         # 路径数据
    └── solution/                        # 求解结果文件夹
        ├── optimization_result.json     # 详细求解结果
        └── result_summary.txt           # 结果摘要
```

**优势**：
- ✅ **结果隔离**：每次运行都有独立的目录，不会覆盖历史结果
- ✅ **版本追溯**：目录名包含时间戳和版本ID，便于追溯
- ✅ **结构清晰**：数据和结果分离，逻辑清晰
- ✅ **快速查看**：`result_summary.txt` 提供结果摘要，无需打开JSON文件

## 注意事项
1. 确保数据文件格式与schema定义一致
2. 如使用商业求解器（Gurobi/CPLEX），需要配置license
3. 根据数据规模调整求解器参数（超时时间、线程数等）
