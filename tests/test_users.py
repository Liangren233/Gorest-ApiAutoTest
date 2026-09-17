import json
import allure
from core.client import ApiClient
from core.assertor import Assertor

def _extract(resp, case, vars_pool):
    import re
    extract_cfg = case.get("extract")
    if not extract_cfg:
        return
    data = resp.json()

    for var_name, expr in extract_cfg.items():
        val = None

        if expr.startswith("$."):
            path = expr[2:]
            parts = path.split(".")

            if isinstance(data, list) and len(data) > 0:
                val = data[0]
                for p in parts:
                    if isinstance(val, dict):
                        val = val.get(p)
                    else:
                        val = None
                        break
            elif isinstance(data, dict):
                val = data
                for p in parts:
                    if isinstance(val, dict):
                        val = val.get(p)
                    else:
                        val = None
                        break

        elif expr.startswith("$[") and ".id" in expr:
            idx = int(re.search(r'\[(\d+)\]', expr).group(1))
            if isinstance(data, list) and len(data) > idx:
                val = data[idx].get("id")

        if val is not None:
            vars_pool[var_name] = val
            print(f"  [提取] {var_name} = {val}")
        else:
            print(f"  [WARN] 提取失败: {var_name} (表达式: {expr})")

@allure.feature("用户管理")
@allure.story("用户查询")
def test_api(client, case, vars_pool):
    req = case["request"]
    allure.dynamic.title(case["name"])

    # 替换 url 变量
    url = req["url"]
    for k, v in vars_pool.items():
        url = url.replace(f"${{{k}}}", str(v))

    # ---- 步骤1：发送请求 ----
    with allure.step(f"发送 {req['method']} 请求 → {url}"):
        resp = client.request(req["method"], url)
        allure.attach(
            f"{req['method']} {url}",
            name="请求信息",
            attachment_type=allure.attachment_type.TEXT
        )

    # ---- 步骤2：提取变量 ----
    if case.get("extract"):
        with allure.step("提取响应变量"):
            _extract(resp, case, vars_pool)
            if vars_pool:
                allure.attach(
                    json.dumps(vars_pool, ensure_ascii=False, indent=2),
                    name="变量池",
                    attachment_type=allure.attachment_type.JSON
                )

    # ---- 步骤3：断言 ----
    with allure.step("执行断言"):
        Assertor(resp, case["name"]).run(case["expects"])

    # ---- 响应体始终作为附件落报告 ----
    allure.attach(
        json.dumps(resp.json(), ensure_ascii=False, indent=2),
        name=f"响应体 (HTTP {resp.status_code})",
        attachment_type=allure.attachment_type.JSON
    )