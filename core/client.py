import os
import requests
from dotenv import load_dotenv
from core.yaml_util import load_yaml

# 启动时加载 .env(凭据不入库,本地用;CI 由 Jenkins Credentials 注入同名环境变量)
load_dotenv()

# 按 RUN_ENV 读对应环境配置,默认 test;env.yaml 存 base_url + token 变量名(多环境分离)
ENV = os.getenv("RUN_ENV", "test")
cfg = load_yaml("config/env.yaml")[ENV]
BASE_URL = cfg["base_url"]           # 接口基址
TOKEN_ENV_KEY = cfg["token_env"]    # 读哪个环境变量拿 token(test/prod 各自独立)


class ApiClient:
    """HTTP 封装:自动拼 base_url、按 auth 开关注入 Bearer token。"""

    def request(self, method, url, auth=True, **kwargs):
        # auth=False 跳过 token 注入,用于构造 401 鉴权失败场景(负向用例)
        headers = kwargs.get("headers", {})
        if auth:
            token = os.getenv(TOKEN_ENV_KEY)
            if token:
                headers["Authorization"] = f"Bearer {token}"
            else:
                print(f"[WARN] 未读取到 token({TOKEN_ENV_KEY})，可能报 401")
        kwargs["headers"] = headers

        # 相对路径拼 base_url,绝对路径(http 开头)直接用(支持外部 URL)
        full_url = url if url.startswith("http") else f"{BASE_URL}{url}"
        resp = requests.request(method, full_url, **kwargs)
        self.last_resp = resp
        return resp  # 只发一次!早期 bug:末尾又 return requests.request(...) 导致 POST 等非幂等操作执行两次
