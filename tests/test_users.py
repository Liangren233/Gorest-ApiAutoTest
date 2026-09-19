"""用例执行主体:替换变量 → 发请求 → 提取 → 注册清理 → 断言 → Allure 记录。

框架能力(变量替换/JSONPath 提取)在 core.context,断言在 core.assertor,
本文件只保留单一测试函数,新增测试文件可直接复用同一套能力。
"""
import json
import allure
from core.client import ApiClient
from core.assertor import Assertor
from core.context import resolve, resolve_obj, extract


def test_api(client, case, vars_pool):
    """case 由 pytest_generate_tests 从 YAML 参数化注入,vars_pool 是 session 级共享变量池。"""
    req = case["request"]
    allure.dynamic.title(case["name"])

    # ---- 变量替换(发请求前,把 url/json/params 里的 ${var} 换成实际值)----
    url = resolve(req["url"], vars_pool)

    json_body = resolve_obj(req["json"], vars_pool) if "json" in req else None
    params = resolve_obj(req["params"], vars_pool) if "params" in req else None

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
            extract(resp, case["extract"], vars_pool)
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
                rid = resolve(id_expr, vars_pool)
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
