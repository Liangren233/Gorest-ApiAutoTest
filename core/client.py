import os
import requests
from dotenv import load_dotenv
from core.yaml_util import load_yaml

# 1. 自动加载根目录 .env（解决每次手敲 token）
load_dotenv()

# 2. 加载环境配置（默认 test 环境）
ENV = os.getenv("RUN_ENV", "test")
cfg = load_yaml("config/env.yaml")[ENV]

BASE_URL = cfg["base_url"]
TOKEN_ENV_KEY = cfg["token_env"]


class ApiClient:
    def request(self, method, url, auth=True, **kwargs):
        # auth=False 时跳过 token 注入,用于覆盖 401 鉴权失败场景
        headers = kwargs.get("headers", {})
        if auth:
            token = os.getenv(TOKEN_ENV_KEY)
            if token:
                headers["Authorization"] = f"Bearer {token}"
            else:
                print(f"[WARN] 未读取到token({TOKEN_ENV_KEY})，可能报401")
        kwargs["headers"] = headers

        full_url = url if url.startswith("http") else f"{BASE_URL}{url}"
        resp = requests.request(method, full_url, **kwargs)
        self.last_resp = resp
        return resp