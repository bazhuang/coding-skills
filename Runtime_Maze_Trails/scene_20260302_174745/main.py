"""
供需运筹模型运行态主程序

自动生成时间: 2026-03-02 17:52:44

使用方法:
    # 使用默认输出目录（result/{timestamp}_{version_id}）
    python main.py --version-id V20240127

    # 使用自定义配置文件
    python main.py --version-id V20240127 --config db_config.json

    # 指定输出目录
    python main.py --version-id V20240127 --output-dir results/my_result

输出目录结构:
    result/
    └── {timestamp}_{version_id}/
        ├── data/                           # 数据文件夹
        │   ├── monthly_demand_pool.csv
        │   ├── monthly_resource_pool.csv
        │   └── paths.json
        └── solution/                       # 求解结果文件夹
            ├── optimization_result.json    # 详细求解结果
            ├── decision_variables.xlsx     # 决策变量Excel（所有变量和目标函数）
            └── result_summary.txt          # 结果摘要
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# 配置日志
from logger_config import setup_logging, get_logger
setup_logging()
logger = get_logger(__name__)

# 导入数据加载器和模型构建器
from data_loader import DataLoader
from model_builder import build_model, solve_model, parse_result


def create_result_directory(version_id: str) -> Path:
    """创建结果目录结构

    目录结构:
        result/
        └── {timestamp}_{version_id}/
            ├── data/          # 数据文件夹
            └── solution/      # 求解结果文件夹

    Args:
        version_id: 数据版本ID

    Returns:
        Path: 结果根目录路径
    """
    # 生成时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 创建结果目录
    result_root = Path("result")
    result_dir = result_root / f"{timestamp}_{version_id}"
    data_dir = result_dir / "data"
    solution_dir = result_dir / "solution"

    # 创建目录
    data_dir.mkdir(parents=True, exist_ok=True)
    solution_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"创建结果目录: {result_dir}")
    logger.info(f"  - 数据目录: {data_dir}")
    logger.info(f"  - 求解结果目录: {solution_dir}")

    return result_dir


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="供需运筹模型运行态程序"
    )
    parser.add_argument(
        "--version-id",
        required=True,
        help="数据版本ID（如：V20240127）"
    )
    parser.add_argument(
        "--config",
        help="数据源配置文件路径（可选，用于覆盖构建时嵌入的默认配置）"
    )
    parser.add_argument(
        "--output-dir",
        help="结果输出目录（可选，默认：result/{timestamp}_{version_id}）"
    )
    args = parser.parse_args()

    data_loader = None

    try:
        logger.info("=" * 80)
        logger.info("开始运行供需运筹模型")
        logger.info(f"版本ID: {args.version_id}")
        logger.info("=" * 80)

        # 创建结果目录
        if args.output_dir:
            result_dir = Path(args.output_dir)
            data_dir = result_dir / "data"
            solution_dir = result_dir / "solution"
            data_dir.mkdir(parents=True, exist_ok=True)
            solution_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"使用指定的输出目录: {result_dir}")
        else:
            result_dir = create_result_directory(args.version_id)
            data_dir = result_dir / "data"
            solution_dir = result_dir / "solution"

        # 步骤1: 加载所有数据（表数据 + 路径数据）
        logger.info("\n步骤1: 加载所有数据...")
        data_loader = DataLoader(args.config)
        data_loader.connect()
        data = data_loader.load_all(
            args.version_id,
            save_to_file=True,
            output_dir=str(data_dir)  # 数据保存到 data 子目录
        )

        # 打印数据加载摘要
        num_tables = len(data.get("tables", {}))
        num_paths = len(data.get("paths", []))
        logger.info(f"数据加载完成: {num_tables} 个表, {num_paths} 条路径")

        # 步骤2: 构建模型
        logger.info("\n步骤2: 构建模型...")
        model = build_model(data)
        logger.info("模型构建完成")

        # 步骤3: 求解模型
        logger.info("\n步骤3: 求解模型...")
        solution = solve_model(model)
        logger.info("模型求解完成")

        # 步骤4: 解析结果
        logger.info("\n步骤4: 解析结果...")
        result = parse_result(solution, data, str(solution_dir))
        logger.info("结果解析完成")

        # 步骤5: 输出结果到 solution 子目录
        logger.info("\n步骤5: 输出结果...")
        output_path = solution_dir / "optimization_result.json"
        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"求解结果已保存到: {output_path}")

        # 输出Excel文件（如果有）
        if 'excel_output' in result:
            logger.info(f"决策变量Excel已保存到: {result['excel_output']}")

        # 输出结果摘要到 solution 子目录
        summary_path = solution_dir / "result_summary.txt"
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("优化结果摘要\n")
            f.write("=" * 80 + "\n")
            f.write(f"版本ID: {args.version_id}\n")
            f.write(f"求解状态: {result.get('status', 'unknown')}\n")
            if 'total_profit' in result:
                f.write(f"总利润: {result['total_profit']}\n")
            if 'path_flows' in result:
                f.write(f"有效路径数: {len(result['path_flows'])}\n")
            if 'excel_output' in result:
                f.write(f"决策变量Excel: {result['excel_output']}\n")
            f.write(f"结果目录: {result_dir}\n")
            f.write("=" * 80 + "\n")
        logger.info(f"结果摘要已保存到: {summary_path}")

        logger.info("\n" + "=" * 80)
        logger.info("运行完成！")
        logger.info(f"结果目录: {result_dir}")
        logger.info(f"  - 数据文件: {data_dir}")
        logger.info(f"  - 求解结果: {solution_dir}")
        logger.info("=" * 80)

        return result

    except FileNotFoundError as e:
        logger.error(f"文件不存在: {e}")
        print(f"错误：找不到数据文件或配置文件")
        sys.exit(1)

    except Exception as e:
        logger.error(f"运行失败: {str(e)}", exc_info=True)
        sys.exit(1)

    finally:
        # 关闭数据源连接
        if data_loader:
            data_loader.close()


if __name__ == "__main__":
    main()
