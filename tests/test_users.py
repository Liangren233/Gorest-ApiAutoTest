import json
import jsonpath
import allure
import pytest
from core.client import ApiClient
from core.assertor import Assertor


def _resolve(text, vars_pool):
    """字符串变量替换"""
    if not isinstance(text, str):
        return text
    for k, v in vars_pool.items():
        text = text.replace(f"${{{k}}}", str(v))
    return text


def _resolve_obj(obj, vars_pool):
    """递归替换 dict/list 里的变量"""
    if isinstance(obj, str):
        return _resolve(obj, vars_pool)
    elif isinstance(obj, dict):
        return {k: _resolve_obj(v, vars_pool) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_obj(i, vars_pool) for i in obj]
    return obj


def _extract(resp, case, vars_pool):
    extract_cfg = case.get("extract")
    if not extract_cfg:
        return

    try:
        data = resp.json()
    except Exception:
        print(f"  [WARN] 响应非JSON (HTTP {resp.status_code})，跳过提取")
        return

    # 使用 jsonpath 库解析标准 JSONPath 表达式（如 $.id / $[0].id / $.data[0].id）
    for var_name, expr in extract_cfg.items():
        matches = jsonpath.jsonpath(data, expr)
        if matches:
            vars_pool[var_name] = matches[0]
            print(f"  [提取] {var_name} = {matches[0]}")
        else:
            print(f"  [WARN] 提取失败: {var_name} (表达式: {expr})")


def test_api(client, case, vars_pool):
    req = case["request"]
    allure.dynamic.title(case["name"])

    # ---- 变量替换 ----
    url = _resolve(req["url"], vars_pool)

    json_body = None
    if "json" in req:
        json_body = _resolve_obj(req["json"], vars_pool)

    params = None
    if "params" in req:
        params = _resolve_obj(req["params"], vars_pool)

    # ---- 步骤1：发送请求 ----
    auth = req.get("auth", True)
    with allure.step(f"发送 {req['method']} 请求 → {url}"):
        if json_body is not None:
            resp = client.request(req["method"], url, auth=auth, json=json_body, params=params)
        elif params:
            resp = client.request(req["method"], url, auth=auth, params=params)
        else:
            resp = client.request(req["method"], url, auth=auth)

        allure.attach(
            f"{req['method']} {url}"
            + (f"\nBody: {json.dumps(json_body, ensure_ascii=False)}" if json_body else "")
            + (f"\nParams: {json.dumps(params, ensure_ascii=False)}" if params else ""),
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

    # ---- 步骤2.5：注册兜底清理资源 ----
    if case.get("cleanup"):
        with allure.step("注册兜底清理资源"):
            for item in case["cleanup"]:
                # item 格式: "users:${created_user_id}"
                resource, id_expr = item.split(":", 1)
                rid = _resolve(id_expr, vars_pool)
                vars_pool["__cleanup__"].append((resource, rid))
                print(f"  [CLEANUP注册] {resource}/{rid}")

    # ---- 步骤3：断言 ----
    with allure.step("执行断言"):
        Assertor(resp, case["name"]).run(case["expects"])

    # ---- 响应体附件 ----
    with allure.step("响应详情"):
        try:
            resp_body = resp.json()
            allure.attach(
                json.dumps(resp_body, ensure_ascii=False, indent=2),
                name=f"响应体 (HTTP {resp.status_code})",
                attachment_type=allure.attachment_type.JSON
            )
        except Exception:
            allure.attach(
                resp.text[:2000],
                name=f"响应体 (HTTP {resp.status_code}, 非JSON)",
                attachment_type=allure.attachment_type.TEXT
            )