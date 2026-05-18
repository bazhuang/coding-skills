#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nebula图数据库路径查询模块（运行态执行）

自动生成时间: 2026-02-04 23:40:46

功能：根据version_id查询从资源节点到需求节点的所有可行路径
用途：为运筹优化模型提供路径集合数据

使用方法：
    from path_loader import PathLoader

    # 使用默认配置
    loader = PathLoader()
    loader.connect()
    paths = loader.load_paths(version_id="V20240127")
    loader.close()

    # 使用自定义配置
    loader = PathLoader(config_path="custom_config.json")
    loader.connect()
    paths = loader.load_paths(version_id="V20240127")
    loader.close()
"""

import os
import json
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

# Nebula 相关导入
from nebula3.gclient.net import ConnectionPool
from nebula3.Config import Config as NebulaConfig

logger = logging.getLogger(__name__)


# ============================================================================
# 默认配置（构建时嵌入）
# ============================================================================

# Nebula 连接配置（从标准化输入嵌入）
DEFAULT_NEBULA_CONFIG = {"connection": {"graphd_host": "10.203.124.45", "graphd_port": 9669, "timeout_ms": 6000, "max_connection_pool_size": 10}, "auth": {"username": "gas_match_rw", "password": "2CbAetxCua"}, "query": {"default_space": "gas_match_new", "default_timeout_ms": 3000}, "retry": {"max_retries": 3, "retry_interval_ms": 1000}, "version_field": "version_id"}

# 路径查询模板（已填充 resource_tables, demand_tables, edges）
PATH_QUERY_TEMPLATE = """MATCH p = (r)-[:rel_resource_site|monthly_transport_pool|rel_demand_gate_station*1..10]->(d)
WHERE ANY(label IN labels(r) WHERE label IN ["monthly_resource_pool"]) == true
  AND ANY(label IN labels(d) WHERE label IN ["monthly_demand_pool"]) == true
  AND properties(r).version_id == {version_id}
  AND properties(d).version_id == {version_id}
  AND ALL(e IN relationships(p) WHERE e.version_id == {version_id}) == true
RETURN p"""

# 主键映射配置（标签 → 主键字段名）
# 用于从图节点属性中提取业务主键
PRIMARY_KEY_MAPPING = {
    "monthly_demand_pool": "demand_plan_code",
    "monthly_resource_pool": "purchase_agreement_no",
    "ontology_city_gas_station_info": "gate_station_code",
    "ontology_resource_download_site": "resource_download_site_code",
    "rel_demand_gate_station": "id",
    "rel_resource_site": "id",
    "monthly_transport_pool": "id",
}


# ============================================================================
# Nebula 连接管理
# ============================================================================

class NebulaConnection:
    """Nebula 连接管理类"""

    def __init__(self, config: Dict[str, Any]):
        """初始化连接配置

        Args:
            config: Nebula配置字典
        """
        self.config = config
        self.connection_pool = None
        self.session = None

    def connect(self):
        """建立连接"""
        conn_config = self.config.get("connection", {})
        auth_config = self.config.get("auth", {})
        query_config = self.config.get("query", {})

        logger.info(f"连接Nebula数据库: {conn_config.get('graphd_host')}:{conn_config.get('graphd_port')}")

        try:
            # 创建连接配置
            nebula_config = NebulaConfig()
            nebula_config.max_connection_pool_size = conn_config.get("max_connection_pool_size", 10)
            nebula_config.timeout = conn_config.get("timeout_ms", 6000)

            # 创建连接池
            self.connection_pool = ConnectionPool()
            self.connection_pool.init([
                (conn_config.get("graphd_host"), conn_config.get("graphd_port", 9669))
            ], nebula_config)

            # 获取会话
            self.session = self.connection_pool.get_session(
                auth_config.get("username", "root"),
                auth_config.get("password", "nebula")
            )

            # 切换到指定空间
            space = query_config.get("default_space")
            if space:
                result = self.session.execute(f"USE {space}")
                if not result.is_succeeded():
                    raise RuntimeError(f"切换图空间失败: {result.error_msg()}")
                logger.info(f"已切换到图空间: {space}")

            logger.info("Nebula连接成功")

        except Exception as e:
            logger.error(f"连接Nebula失败: {e}")
            raise ConnectionError(f"无法连接到Nebula数据库: {e}")

    def execute_query(self, query: str, max_retries: int = 3) -> Any:
        """执行查询语句

        Args:
            query: nGQL查询语句
            max_retries: 最大重试次数

        Returns:
            查询结果

        Raises:
            RuntimeError: 查询失败时抛出
        """
        logger.debug(f"执行查询: {query[:100]}...")

        for attempt in range(max_retries):
            try:
                result = self.session.execute(query)

                if result.is_succeeded():
                    logger.debug(f"查询成功，返回 {result.row_size()} 行")
                    return result
                else:
                    logger.warning(f"查询失败 (尝试 {attempt + 1}/{max_retries}): {result.error_msg()}")

            except Exception as e:
                logger.warning(f"查询异常 (尝试 {attempt + 1}/{max_retries}): {e}")

            if attempt < max_retries - 1:
                time.sleep(1)  # 重试前等待

        raise RuntimeError(f"查询失败，已重试 {max_retries} 次")

    def close(self):
        """关闭连接"""
        if self.session:
            self.session.release()
        if self.connection_pool:
            self.connection_pool.close()
        logger.info("Nebula连接已关闭")


# ============================================================================
# 路径数据解析
# ============================================================================

def _extract_property_value(prop_value: Any) -> Any:
    """从Nebula DataObject中提取属性值，转换为Python原生对象

    Nebula3的DataObject设计特性：
    - string类型：使用 as_string() 返回 str
    - int类型：使用 as_int() 返回 int
    - double类型：使用 as_double() 返回 float
    - datetime类型：使用 as_datetime() 返回 datetime
    - bool类型：使用 as_bool() 返回 bool
    - 不能对非string类型调用 as_string()，会触发异常

    Args:
        prop_value: Nebula返回的属性值对象

    Returns:
        Any: Python原生对象 (str, int, float, datetime, bool等)
    """
    if prop_value is None:
        return None

    # 根据类型调用对应的方法，返回Python原生对象
    if hasattr(prop_value, 'is_string') and prop_value.is_string():
        return prop_value.as_string()
    elif hasattr(prop_value, 'is_int') and prop_value.is_int():
        return prop_value.as_int()
    elif hasattr(prop_value, 'is_double') and prop_value.is_double():
        return prop_value.as_double()
    elif hasattr(prop_value, 'is_datetime') and prop_value.is_datetime():
        return prop_value.as_datetime()
    elif hasattr(prop_value, 'is_bool') and prop_value.is_bool():
        return prop_value.as_bool()
    else:
        # 兜底：返回原对象
        return prop_value


def parse_path(path_data: Any) -> List[Any]:
    """解析Nebula返回的单条路径数据，提取业务主键

    Args:
        path_data: Nebula返回的原始路径数据

    Returns:
        List[Any]: 路径序列，使用业务对象的主键（不是图数据库的节点ID）
        格式: [resource_pk, edge_pk, node_pk, edge_pk, ..., demand_pk]

        示例:
        - string类型主键: ["RES001", "REL001", "GATE001", "REL002", "DEM001"]
        - int类型主键: [1001, 9001, 2001, 9002, 3001]
        - 混合类型: ["RES001", 9001, 2, 9002, "DEM001"]

    注意：
        - 节点ID：从节点属性中提取业务主键，保持原生类型（str/int/float等）
        - 边ID：从边属性中提取业务主键，保持原生类型（str/int/float等）
        - 所有节点和边都必须有主键配置，否则抛出异常
        - 不强制转换为字符串，保持主键的原始类型
    """
    # 提取节点列表，从属性中获取业务主键
    nodes = path_data.nodes()
    node_pks = []
    for node in nodes:
        # 获取节点的标签（tag）
        tags = node.tags()
        if not tags:
            raise ValueError(f"节点没有标签: {node.get_id()}")

        tag = tags[0]  # 假设每个节点只有一个主标签

        # 获取该标签对应的主键字段名
        if tag not in PRIMARY_KEY_MAPPING:
            raise ValueError(f"未知的节点标签: {tag}，请检查 PRIMARY_KEY_MAPPING 配置")

        pk_field = PRIMARY_KEY_MAPPING[tag]

        # 从节点属性中提取主键值（Nebula对象 → Python对象）
        properties = node.properties()
        pk_value = properties.get(pk_field)
        if pk_value is None:
            raise ValueError(f"节点缺少主键字段 '{pk_field}': VID={node.get_id()}, tag={tag}")

        # 转换为Python原生对象
        pk_native = _extract_property_value(pk_value)
        if pk_native is None:
            raise ValueError(f"无法提取主键值: VID={node.get_id()}, tag={tag}, field={pk_field}")

        # 保持原生类型（不强制转换为字符串）
        node_pks.append(pk_native)

    # 提取边列表，从边属性中获取业务主键
    edges = path_data.relationships()
    edge_pks = []
    for i, edge in enumerate(edges):
        # 获取边的类型（edge type）
        edge_type = edge.edge_name()

        # 检查边是否有主键配置
        if edge_type not in PRIMARY_KEY_MAPPING:
            raise ValueError(f"边类型 '{edge_type}' 未配置主键映射，请在 PRIMARY_KEY_MAPPING 中添加")

        # 从边属性中提取业务主键
        pk_field = PRIMARY_KEY_MAPPING[edge_type]
        properties = edge.properties()
        pk_value = properties.get(pk_field)

        if pk_value is None:
            raise ValueError(f"边缺少主键字段 '{pk_field}': edge_type={edge_type}, src={node_pks[i] if i < len(node_pks) else 'unknown'}, dst={node_pks[i+1] if i+1 < len(node_pks) else 'unknown'}")

        # 使用边的业务主键（保持原生类型）
        edge_pk = _extract_property_value(pk_value)
        if edge_pk is None:
            raise ValueError(f"无法提取边主键值: edge_type={edge_type}, field={pk_field}")

        edge_pks.append(edge_pk)

    # 构建路径序列：[node1_pk, edge1_pk, node2_pk, edge2_pk, ..., nodeN_pk]
    path_sequence = []
    for i in range(len(node_pks)):
        path_sequence.append(node_pks[i])
        if i < len(edge_pks):
            path_sequence.append(edge_pks[i])

    return path_sequence


# ============================================================================
# 路径加载器
# ============================================================================

class PathLoader:
    """路径加载器（与 TableLoader 设计保持一致）"""

    def __init__(self, config_path: Optional[str] = None):
        """初始化路径加载器

        Args:
            config_path: 配置文件路径（可选，用于覆盖默认配置）
        """
        self.connection = None
        self.nebula_config = self._load_config(config_path)

    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """加载配置

        Args:
            config_path: 配置文件路径（可选）

        Returns:
            Nebula配置字典
        """
        # 优先使用外部配置文件（如果提供）
        if config_path and os.path.exists(config_path):
            logger.info(f"使用外部配置文件: {config_path}")
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 从配置文件中提取 Nebula 配置
            # 支持两种格式：
            # 1. 直接是 nebula 配置: {"connection": {...}, "auth": {...}, ...}
            # 2. 包含 data_source: {"source_type": "nebula", "nebula": {...}}
            if "source_type" in config and config.get("source_type") == "nebula":
                return config.get("nebula", DEFAULT_NEBULA_CONFIG)
            elif "connection" in config or "auth" in config:
                # 直接是 nebula 配置
                return config
            else:
                logger.warning("配置文件格式不正确，使用默认配置")
                return DEFAULT_NEBULA_CONFIG
        else:
            # 使用构建时嵌入的默认配置
            logger.info("使用构建时嵌入的默认配置")
            return DEFAULT_NEBULA_CONFIG

    def connect(self):
        """建立Nebula连接"""
        self.connection = NebulaConnection(self.nebula_config)
        self.connection.connect()

    def close(self):
        """关闭Nebula连接"""
        if self.connection:
            self.connection.close()

    def load_paths(self, version_id: str, save_to_file: bool = True, output_dir: str = "data") -> List[List[Any]]:
        """加载指定版本的所有可行路径

        Args:
            version_id: 数据版本ID（如：V20240127）
            save_to_file: 是否保存数据到文件（默认：True）
            output_dir: 数据文件输出目录（默认：data）

        Returns:
            List[List[Any]]: 路径序列列表的集合
            每个路径序列是 [node1, edge1, node2, edge2, ..., nodeN]
            节点和边的ID使用业务主键，保持原生类型（str/int/float等）

            示例:
            [
                ["R001", "REL001", "M001", "REL002", "D001"],  # string类型
                [1001, 9001, 2001, 9002, 3001],  # int类型
                ...
            ]
        """
        if not self.connection:
            raise RuntimeError("未建立连接，请先调用 connect()")

        logger.info("=" * 80)
        logger.info(f"开始加载路径数据（版本：{version_id}）")
        logger.info("=" * 80)

        # 替换查询模板中的 version_id 占位符
        # 注意：version_id 是数值型，不需要引号
        query = PATH_QUERY_TEMPLATE.replace("{version_id}", str(version_id))
        logger.debug(f"查询语句: {query}")

        # 执行查询
        retry_config = self.nebula_config.get("retry", {})
        max_retries = retry_config.get("max_retries", 3)
        result = self.connection.execute_query(query, max_retries)

        # 解析路径
        path_sequences = []

        for i in range(result.row_size()):
            row = result.row_values(i)
            # 假设查询返回的第一列是路径
            path_data = row[0].as_path()
            path_sequence = parse_path(path_data)
            path_sequences.append(path_sequence)

        logger.info("=" * 80)
        logger.info(f"路径数据加载完成，共找到 {len(path_sequences)} 条路径")
        logger.info("=" * 80)

        # 打印统计信息
        if path_sequences:
            # 从path_sequences中提取资源和需求节点（第一个和最后一个节点）
            unique_resources = set(seq[0] for seq in path_sequences if seq)
            unique_demands = set(seq[-1] for seq in path_sequences if seq)
            # 计算平均路径长度（节点数 = (序列长度 + 1) / 2）
            avg_length = sum((len(seq) + 1) // 2 for seq in path_sequences) / len(path_sequences)

            logger.info("路径统计:")
            logger.info(f"  - 总路径数: {len(path_sequences)}")
            logger.info(f"  - 唯一资源数: {len(unique_resources)}")
            logger.info(f"  - 唯一需求数: {len(unique_demands)}")
            logger.info(f"  - 平均路径长度: {avg_length:.2f}")

        # 保存数据到文件
        if save_to_file:
            self._save_paths_to_file(path_sequences, version_id, output_dir)

        return path_sequences

    def _save_paths_to_file(self, path_sequences: List[List[str]], version_id: str, output_dir: str):
        """将路径数据保存到文件

        Args:
            path_sequences: 路径序列列表
            version_id: 版本ID
            output_dir: 输出目录
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        file_path = output_path / f"paths_{version_id}.json"

        data = {
            "version_id": version_id,
            "query_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_paths": len(path_sequences),
            "path_sequences": path_sequences
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info("=" * 80)
        logger.info(f"路径数据已保存到: {file_path} ({len(path_sequences)} 条路径)")
        logger.info("=" * 80)