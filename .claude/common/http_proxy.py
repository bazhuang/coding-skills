import sys
import json
from pathlib import Path

import requests

# 添加 common 模块路径
if (common_dir := Path(__file__).resolve().parent.parent.parent.parent / "common") not in sys.path:
    sys.path.insert(0, str(common_dir))

from config import SKILL_PROXY_URL, CONFIG,  get_auth_tokens

def http_proxy(
    target_url: str,
    method: str = "POST",
    headers: dict = None,
    body: str = None,
):
    # 获取认证 token
    auth_tokens = get_auth_tokens()

    req_headers = {
        "Content-Type": "application/json",
        "x-gw-accesskey": CONFIG.get("access_key"),
        **auth_tokens
    }

    request_body = {
        "targetUrl": target_url,
        "method": method,
        "headers": headers if headers is not None else {},
        "body": body,
    }
    print(f"url={CONFIG.get("gateway_url") + SKILL_PROXY_URL}")

    try:
        response = requests.post(
            url=CONFIG.get("gateway_url") + SKILL_PROXY_URL,
            headers=req_headers,
            json=request_body,
            timeout=30
        )
        response.raise_for_status()
        print(f"调用skill API 代理成功。")
    except requests.exceptions.RequestException as e:
        print(f"调用skill API 代理失败。: {e}")
        sys.exit(1)
