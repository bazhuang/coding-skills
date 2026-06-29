import json
import sys
import os
from pathlib import Path

# 添加 common 模块路径
if (common_dir := Path(__file__).resolve().parent.parent.parent.parent.parent / "common") not in sys.path:
    sys.path.insert(0, str(common_dir))

from config import get_app_config, get_auth_tokens, SKILL_AUTH_FINGERPRINT
from http_proxy import http_proxy

if __name__ == "__main__":
    fingerprint = get_auth_tokens()
    repo_root = Path(__file__).resolve().parents[4]
    file_path = repo_root / "docs" / "ontology_schema.json"
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    try:
        with open(file_path, "r", encoding='utf-8') as f:
            content = f.read()

            finish_body = get_app_config()
            finish_body["skill"] = "ontology-modeling"
            finish_body["output"] = content

            http_proxy(
                target_url="http://127.0.0.1:8080/aicoding/agent/step/skill/complete",
                method="POST",
                body=json.dumps(finish_body),
            )
    except Exception as e:
        print(f"File created failed, error: {str(e)}")
