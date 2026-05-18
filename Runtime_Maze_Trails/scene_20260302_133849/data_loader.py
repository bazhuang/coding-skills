"""
统一数据加载器（运行态执行）

自动生成时间: 2026-03-02 13:39:27

功能：
- 整合表数据加载和路径数据加载
- 提供统一的数据加载接口
- 支持多种数据源：Nebula图数据库、MySQL、PostgreSQL、CSV文件等
- 根据 version_id 过滤数据版本

配置说明：
- 构建时已将数据源配置嵌入到 table_loader.py 和 path_loader.py 中
- 运行时可通过 --config 参数覆盖默认配置
- 配置文件会同时应用于表数据加载和路径数据加载
- 对于 Nebula 数据源，表加载和路径加载使用相同的连接配置

使用方法：
    # 方式1：使用构建时嵌入的配置（默认）
    python data_loader.py --version-id V20240127

    # 方式2：使用外部配置文件覆盖默认配置（可选）
    # 注意：此配置会同时应用于表加载和路径加载
    python data_loader.py --version-id V20240127 --config custom_config.json

    # 方式3：在代码中导入使用
    from data_loader import DataLoader

    # 使用默认配置
    loader = DataLoader()
    loader.connect()
    all_data = loader.load_all(version_id="V20240127")
    loader.close()

    # 使用自定义配置（同时应用于表加载和路径加载）
    loader = DataLoader(config_path="custom_config.json")
    loader.connect()
    all_data = loader.load_all(version_id="V20240127")
    loader.close()
"""

import os
import json
import logging
import argparse
from typing import Dict, Any, Optional
from pathlib import Path

# 导入表加载器和路径加载器
from table_loader import TableLoader
from path_loader import PathLoader

logger = logging.getLogger(__name__)


# ============================================================================
# 统一数据加载器
# ============================================================================

class DataLoader:
    """统一数据加载器 - 整合表数据和路径数据加载"""

    def __init__(self, config_path: Optional[str] = None):
        """初始化数据加载器

        Args:
            config_path: 配置文件路径（可选，用于覆盖默认配置）
                        注意：此配置会同时应用于 TableLoader 和 PathLoader
        """
        self.config_path = config_path
        self.table_loader = TableLoader(config_path)
        self.path_loader = PathLoader(config_path)

    def connect(self):
        """建立数据源连接"""
        logger.info("=" * 80)
        logger.info("建立数据源连接...")
        logger.info("=" * 80)

        # 连接表数据源
        self.table_loader.connect()
        logger.info("✓ 表数据源连接成功")

        # 连接路径数据源
        self.path_loader.connect()
        logger.info("✓ 路径数据源连接成功")

        logger.info("=" * 80)

    def close(self):
        """关闭数据源连接"""
        logger.info("=" * 80)
        logger.info("关闭数据源连接...")
        logger.info("=" * 80)

        # 关闭表数据源
        if self.table_loader:
            self.table_loader.close()
            logger.info("✓ 表数据源已关闭")

        # 关闭路径数据源
        if self.path_loader:
            self.path_loader.close()
            logger.info("✓ 路径数据源已关闭")

        logger.info("=" * 80)

    def load_all(
        self,
        version_id: str,
        save_to_file: bool = True,
        output_dir: str = "data"
    ) -> Dict[str, Any]:
        """加载所有数据（表数据 + 路径数据）

        Args:
            version_id: 数据版本ID
            save_to_file: 是否保存数据到文件（默认：True）
            output_dir: 数据文件输出目录（默认：data）

        Returns:
            包含所有数据的字典:
            {
                "tables": {
                    "table1": DataFrame,
                    "table2": DataFrame,
                    ...
                },
                "paths": [
                    [node1, edge1, node2, edge2, ..., nodeN],  # 路径序列1
                    [node1, edge1, node2, edge2, ..., nodeN],  # 路径序列2
                    ...
                ]
            }
        """
        logger.info("=" * 80)
        logger.info(f"开始加载所有数据（版本：{version_id}）")
        logger.info("=" * 80)

        result = {}

        try:
            # 1. 加载表数据
            logger.info("\n[1/2] 加载表数据...")
            tables = self.table_loader.load_all(
                version_id=version_id,
                save_to_file=save_to_file,
                output_dir=output_dir
            )
            result["tables"] = tables
            logger.info(f"✓ 表数据加载完成，共 {len(tables)} 个表")

            # 2. 加载路径数据
            logger.info("\n[2/2] 加载路径数据...")
            try:
                path_sequences = self.path_loader.load_paths(
                    version_id=version_id,
                    save_to_file=save_to_file,
                    output_dir=output_dir
                )
                result["paths"] = path_sequences
                logger.info(f"✓ 路径数据加载完成，共 {len(path_sequences)} 条路径")
            except Exception as e:
                logger.error(f"路径数据加载失败: {e}")
                raise  # 路径数据是必需的，加载失败应该抛出异常

            logger.info("\n" + "=" * 80)
            logger.info("所有数据加载完成")
            logger.info("=" * 80)

            # 打印数据摘要
            self._print_summary(result, version_id)

            return result

        except Exception as e:
            logger.error(f"数据加载失败: {str(e)}", exc_info=True)
            raise

    def _print_summary(self, data: Dict[str, Any], version_id: str):
        """打印数据摘要

        Args:
            data: 数据字典
            version_id: 版本ID
        """
        logger.info("\n数据摘要:")
        logger.info(f"  版本ID: {version_id}")

        # 表数据摘要
        tables = data.get("tables", {})
        logger.info(f"  表数量: {len(tables)}")
        total_rows = sum(len(df) for df in tables.values())
        logger.info(f"  总行数: {total_rows}")

        for table_name, df in tables.items():
            logger.info(f"    - {table_name}: {len(df)} 行 x {len(df.columns)} 列")

        # 路径数据摘要
        paths = data.get("paths")
        if paths is not None:
            logger.info(f"  路径数量: {len(paths)}")
            # 路径格式: [node1, edge1, node2, edge2, ..., nodeN]
            # 第一个元素是资源节点，最后一个元素是需求节点
            if len(paths) > 0:
                unique_resources = len(set(path[0] for path in paths))
                unique_demands = len(set(path[-1] for path in paths))
                logger.info(f"    - 唯一资源数: {unique_resources}")
                logger.info(f"    - 唯一需求数: {unique_demands}")
        else:
            logger.info(f"  路径数量: 0 (未配置路径查询)")

        logger.info("=" * 80)


# ============================================================================
# 辅助函数
# ============================================================================

def save_data_summary(
    data: Dict[str, Any],
    version_id: str,
    source_type: str,
    output_file: Optional[str] = None
):
    """保存数据摘要信息

    Args:
        data: 数据字典
        version_id: 数据版本ID
        source_type: 数据源类型
        output_file: 输出文件路径（可选，默认保存到 tmp/ 目录）
    """
    # 如果未指定输出文件，使用默认路径（tmp目录）
    if output_file is None:
        tmp_dir = Path("tmp")
        tmp_dir.mkdir(exist_ok=True)
        output_file = tmp_dir / f"data_summary_{version_id}.json"
    else:
        output_file = Path(output_file)
        # 确保输出目录存在
        output_file.parent.mkdir(parents=True, exist_ok=True)

    summary = {
        "version_id": version_id,
        "source_type": source_type,
        "tables": {},
        "paths": None
    }

    # 表数据摘要
    tables = data.get("tables", {})
    for table_name, df in tables.items():
        summary["tables"][table_name] = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "memory_usage_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2)
        }

    # 路径数据摘要
    paths = data.get("paths")
    if paths is not None:
        # 路径格式: [node1, edge1, node2, edge2, ..., nodeN]
        # 第一个元素是资源节点，最后一个元素是需求节点
        summary["paths"] = {
            "total_paths": len(paths),
            "unique_resources": len(set(path[0] for path in paths)) if len(paths) > 0 else 0,
            "unique_demands": len(set(path[-1] for path in paths)) if len(paths) > 0 else 0,
            "avg_path_length": sum(len(path) for path in paths) / len(paths) if len(paths) > 0 else 0
        }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info(f"数据摘要已保存到: {output_file}")


def main():
    """
    主函数

    命令行参数：
        --version-id: 数据版本ID（必需）
        --config: 配置文件路径（可选，用于覆盖默认配置）
        --output: 数据摘要输出文件（可选）

    说明：
        - 构建时已将 db_config.json 嵌入代码，无需外部配置文件即可运行
        - --config 参数仅用于运行时临时覆盖默认配置

    示例：
        # 使用默认配置（推荐）
        python data_loader.py --version-id V20240127

        # 覆盖默认配置
        python data_loader.py --version-id V20240127 --config custom_config.json
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="统一数据加载器 - 支持多种数据源"
    )
    parser.add_argument(
        "--version-id",
        required=True,
        help="数据版本ID（如：V20240127）"
    )
    parser.add_argument(
        "--config",
        help="配置文件路径（可选，用于覆盖构建时嵌入的默认配置）"
    )
    parser.add_argument(
        "--output",
        help="数据摘要输出文件（默认：tmp/data_summary_{version_id}.json）"
    )
    args = parser.parse_args()

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    loader = None

    try:
        # 创建数据加载器
        loader = DataLoader(args.config)

        # 连接数据源
        loader.connect()

        # 加载数据
        data = loader.load_all(args.version_id)

        # 保存数据摘要
        output_file = args.output or f"tmp/data_summary_{args.version_id}.json"
        save_data_summary(
            data,
            args.version_id,
            loader.table_loader.source_type,
            output_file
        )

        # 打印成功信息
        print(f"\n{'='*60}")
        print(f"数据加载成功")
        print(f"{'='*60}")
        print(f"版本ID: {args.version_id}")
        print(f"数据源: {loader.table_loader.source_type}")
        print(f"表数量: {len(data.get('tables', {}))}")
        print(f"总行数: {sum(len(df) for df in data.get('tables', {}).values())}")
        paths = data.get("paths")
        if paths is not None:
            print(f"路径数量: {len(paths)}")
        print(f"数据摘要: {output_file}")
        print(f"{'='*60}\n")

    except FileNotFoundError as e:
        logger.error(f"文件不存在: {e}")
        print(f"错误：找不到数据文件或配置文件")
        exit(1)

    except Exception as e:
        logger.error(f"程序执行失败: {e}", exc_info=True)
        print(f"错误：{e}")
        exit(1)

    finally:
        # 关闭连接
        if loader:
            loader.close()


if __name__ == "__main__":
    main()