"""
系统环境配置模块
提供不同环境的 API 地址、访问密钥等配置
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

# 获取当前环境，默认为 fat
ENV = os.getenv('ENV', 'fat').lower()

# API 代理转发
SKILL_PROXY_URL = "/skill-auth/proxy"

ENV_CONFIG: Dict[str, Dict[str, Any]] = {
    "dev": {
        "access_key": "",
        "gateway_url": "http://127.0.0.1:8080"
    },
    "fat": {
        "access_key": "QqtHrotQB3GpLfj4GEWfcLrGGEitzHxj",
        "gateway_url": "https://rdfa-gateway.fat.ennew.com/bizmanage"
    },
    "uat": {
        "access_key": "xW9NFDX58YVHCO8XGZpIkzGvS3fs0NIL",
        "gateway_url": "https://rdfa-gateway.uat.ennew.com/bizmanage"
    },
    "prod": {
        "access_key": "9GeND2MF703TwYh3XQj1crMlz3Yp4eYi",
        "gateway_url": "https://rdfa-gateway.ennew.com/bizmanage"
    }
}


# 获取当前环境配置
CONFIG = ENV_CONFIG.get(ENV, ENV_CONFIG["fat"])


# 动态变量配置文件
APP_CONFIG_FILE = Path(__file__).parent.parent.parent / ".app_config.json"

# 动态变量
SKILL_TOKEN = 'skillToken'
FINGERPRINT = 'fingerprint'
STEP_ID = 'stepId'
CVCU_ID = 'cvcuId'

SKILL_AUTH_TOKEN = 'X-Skill-Auth-Token'
SKILL_AUTH_FINGERPRINT = 'X-Skill-Auth-Fingerprint'

def get_auth_tokens() -> Dict[str, str]:
    """
    实时读取 .app_config.json 中的认证 token

    Returns:
        Dict[str, str]: 包含 ennu_auth 和 csrf_token 的字典

    Raises:
        FileNotFoundError: 配置文件不存在
        KeyError: 配置文件缺少必要的字段
        json.JSONDecodeError: 配置文件格式错误
    """
    if not APP_CONFIG_FILE.exists():
        raise FileNotFoundError(f"应用配置文件不存在: {APP_CONFIG_FILE}")

    with open(APP_CONFIG_FILE, 'r', encoding='utf-8') as f:
        app_config = json.load(f)

    return {
        SKILL_AUTH_TOKEN: app_config[SKILL_TOKEN],
        SKILL_AUTH_FINGERPRINT: app_config[FINGERPRINT]
    }

def get_app_config() -> Dict[str, str]:
    """
    读取 .app_config.json 中的 stepId
    """
    if not APP_CONFIG_FILE.exists():
        raise FileNotFoundError(f"应用配置文件不存在: {APP_CONFIG_FILE}")

    with open(APP_CONFIG_FILE, 'r', encoding='utf-8') as f:
        app_config = json.load(f)

    return {
        STEP_ID: app_config[STEP_ID],
        CVCU_ID: app_config[CVCU_ID]
    }




