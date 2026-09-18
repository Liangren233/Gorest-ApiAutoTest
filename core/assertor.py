import json
from dataclasses import field
from typing import cast


class Assertor:
    def __init__(self,resp,case_name):
        self.resp=resp
        self.case_name=case_name

    def assert_status(self,expected_status):
        actual = self.resp.status_code
        assert actual==expected_status,f"[{self.case_name}]状态码断言失败，期望：{expected_status}，实际{actual}"

    def assert_contains(self,expects:dict):
        actual = self.resp.json()
        for k,v in expects.items():
            if isinstance(actual, list):
                # 422 错误响应是数组,检查是否存在元素的 field=value
                found = any(isinstance(item, dict) and item.get(k) == v for item in actual)
                assert found, f"[{self.case_name}]响应数组中未找到含 {k}={v} 的元素，实际：{actual}"
            else:
                assert k in actual,f"[{self.case_name}]字段缺失：{k}"
                assert actual[k] == v,f"[{self.case_name}]字段值不符：{k}期望{v}，实际{actual[k]}"

    def assert_schema(self, expected_schema: dict):
        actual = self.resp.json()

        # 如果响应是数组，取第一个元素做 schema 校验
        if isinstance(actual, list):
            assert len(actual) > 0, f"[{self.case_name}] 响应数组为空，无法校验 schema"
            actual = actual[0]

        for field, rule in expected_schema.items():
            assert field in actual, f"[{self.case_name}] 必填字段缺失: {field}"
            if "type" in rule:
                typ = rule["type"]
                assert isinstance(actual[field], eval(typ)), \
                    f"[{self.case_name}] 类型不符: {field} 期望{typ}, 实际{type(actual[field]).__name__}"

    def run(self,expects:dict):
        self.assert_status(expects.get("status",200))
        if "contains" in expects:
            self.assert_contains(expects["contains"])
        if "schema" in expects:
            self.assert_schema(expects["schema"])