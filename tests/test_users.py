import json
import jsonpath
import allure
import pytest
from core.client import ApiClient
from core.assertor import Assertor


def _resolve(text, vars_pool):
    """字符串变量替换:把 ${var} 替换成 vars_pool[var] 的字符串值。

    放在 test 层而非 client 层:client 是无状态 HTTP 工具,不应感知测试变量语义(关注点分离)。
    """
    if not isinstance(text, str):
        return text
    for k, v in vars_pool.items():
        text = text.replace(f"${{{k}}}", str(v))
    return text


def _resolve_obj(obj, vars_pool):
    """递归替换 dict/list 里的 ${var}(如 json body 里的 ${timestamp}、${user_id})。"""
    if isinstance(obj, str):
        return _resolve(obj, vars_pool)
    elif isinstance(obj, dict):
        return {k: _resolve_obj(v, vars_pool) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_obj(i, vars_pool) for i in obj]
    return obj


def _extract(resp, case, vars_pool):
    """按 extract 配置的 JSONPath 从响应提取字段,写入 vars_pool。

    使用 jsonpath 库解析标准表达式($.id / $[0].id / $.data[0].id 嵌套)。
    提取失败(matches 为 False)不中断,打印 [WARN];后续 ${var} 找不到会原样保留,通常导致 404。
    """
    extract_cfg = case.get("extract")
    if not extract_cfg:
        return

    try:
        data = resp.json()
    except Exception:
        print(f"  [WARN] 响应非JSON (HTTP {resp.status_code})，跳过提取")
        return

    for var_name, expr in extract_cfg.items():
        matches = jsonpath.jsonpath(data, expr)
        if matches:
            vars_pool[var_name] = matches[0]
            print(f"  [提取] {var_name} = {matches[0]}")
        else:
            print(f"  [WARN] 提取失败: {var_name} (表达式: {expr})")


def test_api(client, case, vars_pool):
    """每条用例的执行主体:替换变量 → 发请求 → 提取 → 注册清理 → 断言 → Allure 记录。

    case 由 pytest_generate_tests 从 YAML 参数化注入,vars_pool 是 session 级共享变量池。
    """
    req = case["request"]
    allure.dynamic.title(case["name"])

    # ---- 变量替换(发请求前,把 url/json/params 里的 ${var} 换成实际值)----
    url = _resolve(req["url"], vars_pool)

    json_body = None
    if "json" in req:
        json_body = _resolve_obj(req["json"], vars_pool)

    params = None
    if "params" in req:
        params = _resolve_obj(req["params"], vars_pool)

    # ---- 步骤1:发送请求(auth 默认 True;case 里 auth:false 可跳过 token 触发 401)----
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

    # ---- 步骤2:提取变量(写入 vars_pool,后序用例可引用实现跨用例关联)----
    if case.get("extract"):
        with allure.step("提取响应变量"):
            _extract(resp, case, vars_pool)
            if vars_pool:
                allure.attach(
                    json.dumps(vars_pool, ensure_ascii=False, indent=2),
                    name="变量池",
                    attachment_type=allure.attachment_type.JSON
                )

    # ---- 步骤2.5:注册兜底清理(extract 到 id 且 case 有 cleanup 才注册;session 结束时统一 DELETE)----
    if case.get("cleanup"):
        with allure.step("注册兜底清理资源"):
            for item in case["cleanup"]:
                # item 格式: "users:${created_user_id}",冒号分隔 资源名:变量表达式
                resource, id_expr = item.split(":", 1)
                rid = _resolve(id_expr, vars_pool)
                vars_pool["__cleanup__"].append((resource, rid))
                print(f"  [CLEANUP注册] {resource}/{rid}")

    # ---- 步骤3:断言(status → contains → schema 三档,任一失败即终止该用例)----
    with allure.step("执行断言"):
        Assertor(resp, case["name"]).run(case["expects"])

    # ---- 响应体附件(便于失败时排查实际返回)----
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
