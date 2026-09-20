import jsonschema


class Assertor:
    """三档断言引擎:status(状态码)→ contains(字段值)→ schema(JSON Schema 结构契约)。

    由弱到强,status 保底线、contains 校业务语义、schema 校结构契约(基于 jsonschema 库,
    支持 type/required/properties/items/enum/pattern 等标准关键字)。
    """

    def __init__(self, resp, case_name):
        self.resp = resp
        self.case_name = case_name

    def assert_status(self, expected_status):
        actual = self.resp.status_code
        assert actual == expected_status, f"[{self.case_name}]状态码断言失败，期望：{expected_status}，实际{actual}"

    def assert_contains(self, expects: dict):
        """字段值精确匹配。

        dict 响应直接比对字段值;list 响应(如 422 错误数组 [{"field":"email","message":"..."}])
        用 any 遍历找是否存在元素含 field=value。
        """
        actual = self.resp.json()
        for k, v in expects.items():
            if isinstance(actual, list):
                # 422 错误响应是数组,检查是否存在元素的 field=value
                found = any(isinstance(item, dict) and item.get(k) == v for item in actual)
                assert found, f"[{self.case_name}]响应数组中未找到含 {k}={v} 的元素，实际：{actual}"
            else:
                assert k in actual, f"[{self.case_name}]字段缺失：{k}"
                assert actual[k] == v, f"[{self.case_name}]字段值不符：{k}期望{v}，实际{actual[k]}"

    def assert_schema(self, expected_schema: dict):
        """用 JSON Schema 校验响应结构(draft-07,支持 type/required/properties/items/enum/pattern 等)。

        dict 响应直接校验;list 响应(如查询列表)用 schema 的 type:array + items 描述元素结构。
        失败抛 AssertionError,包装 jsonschema.ValidationError 的可读消息并带字段路径定位。
        """
        actual = self.resp.json()
        try:
            jsonschema.validate(instance=actual, schema=expected_schema)
        except jsonschema.ValidationError as e:
            path = ".".join(str(p) for p in e.absolute_path) or "(root)"
            raise AssertionError(f"[{self.case_name}] Schema 校验失败 @ {path}: {e.message}") from e

    def run(self, expects: dict):
        """按 status → contains → schema 顺序执行,任一档失败即抛 AssertionError 终止该用例。"""
        self.assert_status(expects.get("status", 200))
        if "contains" in expects:
            self.assert_contains(expects["contains"])
        if "schema" in expects:
            self.assert_schema(expects["schema"])
