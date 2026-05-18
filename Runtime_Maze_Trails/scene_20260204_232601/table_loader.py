"""
表数据加载器（运行态执行）

自动生成时间: 2026-02-04 23:26:39

功能：
- 支持多种数据源：Nebula图数据库、MySQL、PostgreSQL、CSV文件等
- 根据 version_id 过滤数据版本
- 统一的数据接口和格式
- 数据预处理和验证

使用方法：
    from table_loader import TableLoader

    loader = TableLoader()
    loader.connect()
    data = loader.load_all(version_id="V20240127")
    loader.close()
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from abc import ABC, abstractmethod
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# 数据源抽象基类
# ============================================================================

class DataSource(ABC):
    """数据源抽象基类"""

    def __init__(self, config: Dict[str, Any]):
        """初始化数据源

        Args:
            config: 数据源配置
        """
        self.config = config
        self.version_field = config.get("version_field", "version_id")

    @abstractmethod
    def connect(self):
        """建立连接"""
        pass

    @abstractmethod
    def query_table(self, table_name: str, version_id: str, table_type: str = "node") -> pd.DataFrame:
        """查询表数据

        Args:
            table_name: 表名
            version_id: 版本ID
            table_type: 表类型（node或edge），默认为node

        Returns:
            DataFrame格式的表数据
        """
        pass

    @abstractmethod
    def close(self):
        """关闭连接"""
        pass


# ============================================================================
# Nebula 图数据库数据源
# ============================================================================

class NebulaDataSource(DataSource):
    """Nebula图数据库数据源"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.connection_pool = None
        self.session = None

    def connect(self):
        """连接Nebula数据库"""
        from nebula3.gclient.net import ConnectionPool
        from nebula3.Config import Config as NebulaConfig

        logger.info("连接Nebula图数据库...")

        conn_config = self.config.get("connection", {})
        auth_config = self.config.get("auth", {})
        query_config = self.config.get("query", {})

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
            self.session.execute(f"USE {space}")
            logger.info(f"已切换到图空间: {space}")

    def query_table(self, table_name: str, version_id: str, table_type: str = "node") -> pd.DataFrame:
        """从Nebula查询表数据（支持节点和边）

        Args:
            table_name: 表名（对应Nebula中的tag名称或edge type名称）
            version_id: 版本ID
            table_type: 表类型（node或edge），默认为node

        Returns:
            DataFrame格式的表数据
        """
        logger.info(f"从Nebula查询 {table_name} 表（版本：{version_id}，类型：{table_type}）...")

        # 根据表类型选择查询方式
        if table_type == "edge":
            return self._query_edge_table(table_name, version_id)
        else:
            return self._query_node_table(table_name, version_id)

    def _query_node_table(self, table_name: str, version_id: str) -> pd.DataFrame:
        """查询节点表数据

        Args:
            table_name: Tag名称
            version_id: 版本ID

        Returns:
            DataFrame格式的表数据
        """
        # 构建nGQL查询语句
        # 查询指定tag的所有节点，过滤version_id
        # 注意：Nebula节点属性访问需要使用 n.标签名.属性名 格式
        query = f"""
            MATCH (n:{table_name})
            WHERE n.{table_name}.{self.version_field} == {version_id}
            RETURN n
        """

        logger.debug(f"节点查询语句: {query}")

        # 执行查询
        result = self.session.execute(query)

        if not result.is_succeeded():
            raise RuntimeError(f"查询失败: {result.error_msg()}")

        # 解析结果
        rows = []
        for i in range(result.row_size()):
            row_values = result.row_values(i)
            # 获取节点对象
            node = row_values[0].as_node()

            # 提取节点属性
            properties = {}
            properties["_id"] = node.get_id().as_string()  # 节点ID

            # 提取所有属性
            for key in node.properties().keys():
                value = node.properties()[key]
                properties[key] = self._extract_value(value)

            rows.append(properties)

        df = pd.DataFrame(rows)
        logger.info(f"{table_name} 节点表查询完成: {len(df)} 行")

        return df

    def _query_edge_table(self, table_name: str, version_id: str) -> pd.DataFrame:
        """查询边表数据

        Args:
            table_name: EdgeType名称
            version_id: 版本ID

        Returns:
            DataFrame格式的表数据
        """
        # 构建nGQL查询语句
        # 查询指定edge type的所有边，过滤version_id
        query = f"""
            MATCH ()-[e:{table_name}]->()
            WHERE e.{self.version_field} == {version_id}
            RETURN e
        """

        logger.debug(f"边查询语句: {query}")

        # 执行查询
        result = self.session.execute(query)

        if not result.is_succeeded():
            raise RuntimeError(f"查询失败: {result.error_msg()}")

        # 解析结果
        rows = []
        for i in range(result.row_size()):
            row_values = result.row_values(i)
            # 获取边对象
            edge = row_values[0].as_relationship()

            # 提取边属性
            properties = {}
            properties["_src_id"] = edge.start_vertex_id().as_string()  # 起点ID
            properties["_dst_id"] = edge.end_vertex_id().as_string()    # 终点ID
            properties["_edge_id"] = f"{properties['_src_id']}_{properties['_dst_id']}"  # 边ID
            properties["_rank"] = edge.ranking()  # 边的rank值

            # 提取所有属性
            for key in edge.properties().keys():
                value = edge.properties()[key]
                properties[key] = self._extract_value(value)

            rows.append(properties)

        df = pd.DataFrame(rows)
        logger.info(f"{table_name} 边表查询完成: {len(df)} 行")

        return df

    def _extract_value(self, value):
        """从Nebula Value对象提取Python值

        Args:
            value: Nebula Value对象

        Returns:
            Python原生类型的值
        """
        if value.is_null():
            return None
        elif value.is_int():
            return value.as_int()
        elif value.is_double():
            return value.as_double()
        elif value.is_bool():
            return value.as_bool()
        elif value.is_string():
            return value.as_string()
        elif value.is_date():
            return value.as_date()
        elif value.is_time():
            return value.as_time()
        elif value.is_datetime():
            return value.as_datetime()
        else:
            return str(value)

    def close(self):
        """关闭连接"""
        if self.session:
            self.session.release()
        if self.connection_pool:
            self.connection_pool.close()
        logger.info("Nebula连接已关闭")


# ============================================================================
# MySQL 数据源
# ============================================================================

class MySQLDataSource(DataSource):
    """MySQL数据库数据源"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.engine = None

    def connect(self):
        """连接MySQL数据库"""
        import sqlalchemy

        logger.info("连接MySQL数据库...")

        connection_string = self.config.get("connection_string")
        if not connection_string:
            raise ValueError("MySQL配置缺少 connection_string")

        self.engine = sqlalchemy.create_engine(connection_string)
        logger.info("MySQL连接成功")

    def query_table(self, table_name: str, version_id: str, table_type: str = "node") -> pd.DataFrame:
        """从MySQL查询表数据

        Args:
            table_name: 表名
            version_id: 版本ID
            table_type: 表类型（node或edge），MySQL中不区分，保留参数以保持接口一致

        Returns:
            DataFrame格式的表数据
        """
        logger.info(f"从MySQL查询 {table_name} 表（版本：{version_id}）...")

        query = f"""
            SELECT * FROM {table_name}
            WHERE {self.version_field} = '{version_id}'
        """

        df = pd.read_sql(query, self.engine)
        logger.info(f"{table_name} 表查询完成: {len(df)} 行")

        return df

    def close(self):
        """关闭连接"""
        if self.engine:
            self.engine.dispose()
        logger.info("MySQL连接已关闭")


# ============================================================================
# PostgreSQL 数据源
# ============================================================================

class PostgreSQLDataSource(DataSource):
    """PostgreSQL数据库数据源"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.engine = None

    def connect(self):
        """连接PostgreSQL数据库"""
        import sqlalchemy

        logger.info("连接PostgreSQL数据库...")

        connection_string = self.config.get("connection_string")
        if not connection_string:
            raise ValueError("PostgreSQL配置缺少 connection_string")

        self.engine = sqlalchemy.create_engine(connection_string)
        logger.info("PostgreSQL连接成功")

    def query_table(self, table_name: str, version_id: str, table_type: str = "node") -> pd.DataFrame:
        """从PostgreSQL查询表数据

        Args:
            table_name: 表名
            version_id: 版本ID
            table_type: 表类型（node或edge），PostgreSQL中不区分，保留参数以保持接口一致

        Returns:
            DataFrame格式的表数据
        """
        logger.info(f"从PostgreSQL查询 {table_name} 表（版本：{version_id}）...")

        query = f"""
            SELECT * FROM {table_name}
            WHERE {self.version_field} = '{version_id}'
        """

        df = pd.read_sql(query, self.engine)
        logger.info(f"{table_name} 表查询完成: {len(df)} 行")

        return df

    def close(self):
        """关闭连接"""
        if self.engine:
            self.engine.dispose()
        logger.info("PostgreSQL连接已关闭")


# ============================================================================
# 文件数据源
# ============================================================================

class FileDataSource(DataSource):
    """文件数据源（CSV/Excel）"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.file_dir = Path(config.get("file_dir", "."))
        self.file_format = config.get("file_format", "csv")

    def connect(self):
        """检查文件目录"""
        logger.info(f"使用文件数据源: {self.file_dir}")

        if not self.file_dir.exists():
            raise FileNotFoundError(f"文件目录不存在: {self.file_dir}")

    def query_table(self, table_name: str, version_id: str, table_type: str = "node") -> pd.DataFrame:
        """从文件加载表数据

        Args:
            table_name: 表名（文件名）
            version_id: 版本ID
            table_type: 表类型（node或edge），文件数据源中不区分，保留参数以保持接口一致

        Returns:
            DataFrame格式的表数据
        """
        logger.info(f"从文件加载 {table_name} 表（版本：{version_id}）...")

        file_path = self.file_dir / f"{table_name}.{self.file_format}"

        if not file_path.exists():
            raise FileNotFoundError(f"数据文件不存在: {file_path}")

        # 读取文件
        if self.file_format == "csv":
            df = pd.read_csv(file_path)
        elif self.file_format == "excel":
            df = pd.read_excel(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {self.file_format}")

        # 过滤version_id
        if self.version_field in df.columns:
            original_count = len(df)
            df = df[df[self.version_field] == version_id].copy()
            logger.info(f"按 version_id 过滤: {original_count} -> {len(df)} 行")
        else:
            logger.warning(f"{table_name} 表中没有 {self.version_field} 字段，返回所有数据")

        logger.info(f"{table_name} 表加载完成: {len(df)} 行")

        return df

    def close(self):
        """文件数据源无需关闭连接"""
        pass


# ============================================================================
# 数据源工厂
# ============================================================================

class DataSourceFactory:
    """数据源工厂类"""

    @staticmethod
    def create(source_type: str, config: Dict[str, Any]) -> DataSource:
        """创建数据源实例

        Args:
            source_type: 数据源类型（nebula/mysql/postgresql/file）
            config: 数据源配置

        Returns:
            数据源实例
        """
        if source_type == "nebula":
            return NebulaDataSource(config)
        elif source_type == "mysql":
            return MySQLDataSource(config)
        elif source_type == "postgresql":
            return PostgreSQLDataSource(config)
        elif source_type == "file":
            return FileDataSource(config)
        else:
            raise ValueError(f"不支持的数据源类型: {source_type}")


# ============================================================================
# 表数据加载器
# ============================================================================

class TableLoader:
    """表数据加载器"""

    def __init__(self, config_path: Optional[str] = None):
        """初始化表数据加载器

        Args:
            config_path: 配置文件路径（可选，用于覆盖默认配置）
        """
        # 优先使用外部配置文件（如果提供）
        if config_path and os.path.exists(config_path):
            logger.info(f"使用外部配置文件: {config_path}")
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            # 使用构建时嵌入的默认配置
            logger.info("使用构建时嵌入的默认配置")
            config = self._get_default_config()

        self.source_type = config.get("source_type", "file")
        self.source_config = config.get(self.source_type, {})
        self.data_source = None

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置（构建时从 db_config.json 嵌入）"""
        # 这个配置在构建时由 Jinja2 模板从 db_config.json 生成
        return {"source_type": "nebula", "nebula": {"connection": {"graphd_host": "10.203.124.45", "graphd_port": 9669, "timeout_ms": 6000, "max_connection_pool_size": 10}, "auth": {"username": "gas_match_rw", "password": "2CbAetxCua"}, "query": {"default_space": "gas_match_new", "default_timeout_ms": 3000}, "retry": {"max_retries": 3, "retry_interval_ms": 1000}, "version_field": "version_id"}}

    def connect(self):
        """建立数据源连接"""
        self.data_source = DataSourceFactory.create(self.source_type, self.source_config)
        self.data_source.connect()

    def close(self):
        """关闭数据源连接"""
        if self.data_source:
            self.data_source.close()

    def load_monthly_demand_pool(self, version_id: str) -> pd.DataFrame:
        """加载monthly_demand_pool表数据

        Args:
            version_id: 数据版本ID

        Returns:
            DataFrame格式的表数据
        """
        # 根据table_type确定是节点表还是边表
        table_type = "demand"
        # 判断是否为边类型（transport或link）
        is_edge = table_type in ["transport", "link"]
        query_type = "edge" if is_edge else "node"

        df = self.data_source.query_table("monthly_demand_pool", version_id, query_type)

        # 数据验证
        required_fields = ["id", "version_id", "demand_plan_code", "customer_code", "quantity", "unit_selling_price", "delivery_start_time", "delivery_end_time"]
        missing_fields = set(required_fields) - set(df.columns)
        if missing_fields:
            raise ValueError(f"monthly_demand_pool表缺少必需字段: {missing_fields}")

        # 数据类型转换
        type_mapping = {"id": "int", "version_id": "int", "demand_plan_code": "string", "customer_code": "string", "customer_name": "string", "quantity": "float", "unit_selling_price": "float", "delivery_start_time": "datetime", "delivery_end_time": "datetime", "minimum_satisfy_quantity": "float", "must_supply_gas": "string", "allow_below_plan_supply": "string", "company_code": "string", "gmt_create": "datetime", "gmt_modified": "datetime", "creator": "string", "modifier": "string"}
        for field, dtype in type_mapping.items():
            if field in df.columns:
                if dtype == "int":
                    df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0).astype(int)
                elif dtype == "float":
                    df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0.0)
                elif dtype == "datetime":
                    df[field] = pd.to_datetime(df[field], errors='coerce')
                elif dtype == "boolean":
                    df[field] = df[field].astype(bool)

        return df

    def load_monthly_resource_pool(self, version_id: str) -> pd.DataFrame:
        """加载monthly_resource_pool表数据

        Args:
            version_id: 数据版本ID

        Returns:
            DataFrame格式的表数据
        """
        # 根据table_type确定是节点表还是边表
        table_type = "resource"
        # 判断是否为边类型（transport或link）
        is_edge = table_type in ["transport", "link"]
        query_type = "edge" if is_edge else "node"

        df = self.data_source.query_table("monthly_resource_pool", version_id, query_type)

        # 数据验证
        required_fields = ["id", "version_id", "purchase_agreement_no", "resource_supply_code", "quantity", "unit_price", "delivery_start_time", "delivery_end_time"]
        missing_fields = set(required_fields) - set(df.columns)
        if missing_fields:
            raise ValueError(f"monthly_resource_pool表缺少必需字段: {missing_fields}")

        # 数据类型转换
        type_mapping = {"id": "int", "version_id": "int", "purchase_agreement_no": "string", "company_code": "string", "resource_supply_code": "string", "resource_supply_name": "string", "quantity": "float", "min_quantity": "float", "unit_price": "float", "delivery_start_time": "datetime", "delivery_end_time": "datetime", "resource_status": "string", "over_extract": "string", "no_discuss_percent": "float", "resource_type": "string", "gmt_create": "datetime", "gmt_modified": "datetime", "creator": "string", "modifier": "string", "mandatory_delivery": "int"}
        for field, dtype in type_mapping.items():
            if field in df.columns:
                if dtype == "int":
                    df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0).astype(int)
                elif dtype == "float":
                    df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0.0)
                elif dtype == "datetime":
                    df[field] = pd.to_datetime(df[field], errors='coerce')
                elif dtype == "boolean":
                    df[field] = df[field].astype(bool)

        return df

    def load_ontology_city_gas_station_info(self, version_id: str) -> pd.DataFrame:
        """加载ontology_city_gas_station_info表数据

        Args:
            version_id: 数据版本ID

        Returns:
            DataFrame格式的表数据
        """
        # 根据table_type确定是节点表还是边表
        table_type = "passthrough_node"
        # 判断是否为边类型（transport或link）
        is_edge = table_type in ["transport", "link"]
        query_type = "edge" if is_edge else "node"

        df = self.data_source.query_table("ontology_city_gas_station_info", version_id, query_type)

        # 数据验证
        required_fields = ["version_id", "gate_station_code"]
        missing_fields = set(required_fields) - set(df.columns)
        if missing_fields:
            raise ValueError(f"ontology_city_gas_station_info表缺少必需字段: {missing_fields}")

        # 数据类型转换
        type_mapping = {"version_id": "int", "gate_station_code": "string", "city_gas_org_code": "string", "station_name": "string", "upper_bound": "float", "lower_bound": "float", "modifier": "string", "gmt_modified": "datetime"}
        for field, dtype in type_mapping.items():
            if field in df.columns:
                if dtype == "int":
                    df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0).astype(int)
                elif dtype == "float":
                    df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0.0)
                elif dtype == "datetime":
                    df[field] = pd.to_datetime(df[field], errors='coerce')
                elif dtype == "boolean":
                    df[field] = df[field].astype(bool)

        return df

    def load_ontology_resource_download_site(self, version_id: str) -> pd.DataFrame:
        """加载ontology_resource_download_site表数据

        Args:
            version_id: 数据版本ID

        Returns:
            DataFrame格式的表数据
        """
        # 根据table_type确定是节点表还是边表
        table_type = "passthrough_node"
        # 判断是否为边类型（transport或link）
        is_edge = table_type in ["transport", "link"]
        query_type = "edge" if is_edge else "node"

        df = self.data_source.query_table("ontology_resource_download_site", version_id, query_type)

        # 数据验证
        required_fields = ["version_id", "resource_download_site_code"]
        missing_fields = set(required_fields) - set(df.columns)
        if missing_fields:
            raise ValueError(f"ontology_resource_download_site表缺少必需字段: {missing_fields}")

        # 数据类型转换
        type_mapping = {"version_id": "int", "resource_download_site_code": "string", "resource_download_site_name": "string", "gmt_modified": "datetime"}
        for field, dtype in type_mapping.items():
            if field in df.columns:
                if dtype == "int":
                    df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0).astype(int)
                elif dtype == "float":
                    df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0.0)
                elif dtype == "datetime":
                    df[field] = pd.to_datetime(df[field], errors='coerce')
                elif dtype == "boolean":
                    df[field] = df[field].astype(bool)

        return df

    def load_rel_demand_gate_station(self, version_id: str) -> pd.DataFrame:
        """加载rel_demand_gate_station表数据

        Args:
            version_id: 数据版本ID

        Returns:
            DataFrame格式的表数据
        """
        # 根据table_type确定是节点表还是边表
        table_type = "link"
        # 判断是否为边类型（transport或link）
        is_edge = table_type in ["transport", "link"]
        query_type = "edge" if is_edge else "node"

        df = self.data_source.query_table("rel_demand_gate_station", version_id, query_type)

        # 数据验证
        required_fields = ["id", "version_id", "demand_plan_code", "gate_station_code"]
        missing_fields = set(required_fields) - set(df.columns)
        if missing_fields:
            raise ValueError(f"rel_demand_gate_station表缺少必需字段: {missing_fields}")

        # 数据类型转换
        type_mapping = {"id": "int", "version_id": "int", "demand_plan_code": "string", "gate_station_code": "string", "gmt_create": "datetime", "gmt_modified": "datetime", "creator": "string", "modifier": "string"}
        for field, dtype in type_mapping.items():
            if field in df.columns:
                if dtype == "int":
                    df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0).astype(int)
                elif dtype == "float":
                    df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0.0)
                elif dtype == "datetime":
                    df[field] = pd.to_datetime(df[field], errors='coerce')
                elif dtype == "boolean":
                    df[field] = df[field].astype(bool)

        return df

    def load_rel_resource_site(self, version_id: str) -> pd.DataFrame:
        """加载rel_resource_site表数据

        Args:
            version_id: 数据版本ID

        Returns:
            DataFrame格式的表数据
        """
        # 根据table_type确定是节点表还是边表
        table_type = "link"
        # 判断是否为边类型（transport或link）
        is_edge = table_type in ["transport", "link"]
        query_type = "edge" if is_edge else "node"

        df = self.data_source.query_table("rel_resource_site", version_id, query_type)

        # 数据验证
        required_fields = ["id", "version_id", "purchase_agreement_no", "resource_download_site_code"]
        missing_fields = set(required_fields) - set(df.columns)
        if missing_fields:
            raise ValueError(f"rel_resource_site表缺少必需字段: {missing_fields}")

        # 数据类型转换
        type_mapping = {"id": "int", "version_id": "int", "purchase_agreement_no": "string", "resource_download_site_code": "string", "gmt_create": "datetime", "gmt_modified": "datetime", "creator": "string", "modifier": "string"}
        for field, dtype in type_mapping.items():
            if field in df.columns:
                if dtype == "int":
                    df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0).astype(int)
                elif dtype == "float":
                    df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0.0)
                elif dtype == "datetime":
                    df[field] = pd.to_datetime(df[field], errors='coerce')
                elif dtype == "boolean":
                    df[field] = df[field].astype(bool)

        return df

    def load_monthly_transport_pool(self, version_id: str) -> pd.DataFrame:
        """加载monthly_transport_pool表数据

        Args:
            version_id: 数据版本ID

        Returns:
            DataFrame格式的表数据
        """
        # 根据table_type确定是节点表还是边表
        table_type = "transport"
        # 判断是否为边类型（transport或link）
        is_edge = table_type in ["transport", "link"]
        query_type = "edge" if is_edge else "node"

        df = self.data_source.query_table("monthly_transport_pool", version_id, query_type)

        # 数据验证
        required_fields = ["id", "version_id", "transport_code", "delivery_point_code", "station_code", "design_gas_capacity", "unit_price", "delivery_start_time", "delivery_end_time"]
        missing_fields = set(required_fields) - set(df.columns)
        if missing_fields:
            raise ValueError(f"monthly_transport_pool表缺少必需字段: {missing_fields}")

        # 数据类型转换
        type_mapping = {"id": "int", "version_id": "int", "company_code": "string", "transport_code": "string", "transport_name": "string", "delivery_point_name": "string", "delivery_point_code": "string", "station_name": "string", "station_code": "string", "consignor_name": "string", "resource_supplier": "string", "route": "string", "transport_status": "string", "pipe_type": "string", "design_gas_capacity": "float", "unit_price": "float", "min_amount": "float", "delivery_start_time": "datetime", "delivery_end_time": "datetime", "gmt_create": "datetime", "gmt_modified": "datetime", "creator": "string", "modifier": "string"}
        for field, dtype in type_mapping.items():
            if field in df.columns:
                if dtype == "int":
                    df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0).astype(int)
                elif dtype == "float":
                    df[field] = pd.to_numeric(df[field], errors='coerce').fillna(0.0)
                elif dtype == "datetime":
                    df[field] = pd.to_datetime(df[field], errors='coerce')
                elif dtype == "boolean":
                    df[field] = df[field].astype(bool)

        return df

    def load_all(self, version_id: str, save_to_file: bool = True, output_dir: str = "data") -> Dict[str, pd.DataFrame]:
        """加载所有表数据

        Args:
            version_id: 数据版本ID
            save_to_file: 是否保存数据到文件（默认：True）
            output_dir: 数据文件输出目录（默认：data）

        Returns:
            包含所有表数据的字典
        """
        logger.info("=" * 80)
        logger.info(f"开始加载表数据（版本：{version_id}，数据源：{self.source_type}）")
        logger.info("=" * 80)

        data = {}

        try:
            data["monthly_demand_pool"] = self.load_monthly_demand_pool(version_id)
            data["monthly_resource_pool"] = self.load_monthly_resource_pool(version_id)
            data["ontology_city_gas_station_info"] = self.load_ontology_city_gas_station_info(version_id)
            data["ontology_resource_download_site"] = self.load_ontology_resource_download_site(version_id)
            data["rel_demand_gate_station"] = self.load_rel_demand_gate_station(version_id)
            data["rel_resource_site"] = self.load_rel_resource_site(version_id)
            data["monthly_transport_pool"] = self.load_monthly_transport_pool(version_id)

            logger.info("=" * 80)
            logger.info("表数据加载完成")
            logger.info("=" * 80)

            # 打印数据统计
            for table_name, df in data.items():
                logger.info(f"  {table_name}: {len(df)} 行 x {len(df.columns)} 列")

            # 保存数据到文件
            if save_to_file:
                self._save_data_to_files(data, version_id, output_dir)

            return data

        except Exception as e:
            logger.error(f"表数据加载失败: {str(e)}", exc_info=True)
            raise

    def _save_data_to_files(self, data: Dict[str, pd.DataFrame], version_id: str, output_dir: str):
        """将数据保存到文件

        Args:
            data: 数据字典
            version_id: 版本ID
            output_dir: 输出目录
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info("=" * 80)
        logger.info(f"保存表数据到文件（目录：{output_dir}）")
        logger.info("=" * 80)

        for table_name, df in data.items():
            file_path = output_path / f"{table_name}_{version_id}.csv"
            df.to_csv(file_path, index=False, encoding='utf-8')
            logger.info(f"  {table_name}: {file_path} ({len(df)} 行)")

        logger.info("=" * 80)
        logger.info("表数据文件保存完成")
        logger.info("=" * 80)