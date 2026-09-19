"""用例数据运行时支持:YAML 加载 → ${var} 变量替换 → JSONPath 响应提取。

三个函数围绕同一主题——用例数据在运行时的流转——故集中在一个模块,
供 conftest(加载用例)与任意 test_*.py(替换/提取)复用。
"""
import os
import yaml
import jsonpath

# 项目根目录(core 的上一级),用于把相对路径解析成绝对路径
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_yaml(path):
    """加载 YAML 文件,path 相对项目根。返回 dict,空文件返回 {}。"""
    abs_path = os.path.join(_ROOT, path)
    with open(abs_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve(text, vars_pool):
    """字符串变量替换:把 ${var} 替换成 vars_pool[var] 的字符串值。

    放在 core 层而非 client 层:client 是无状态 HTTP 工具,不应感知测试变量语义(关注点分离)。
    """
    if not isinstance(text, str):
        return text
    for k, v in vars_pool.items():
        text = text.replace(f"${{{k}}}", str(v))
    return text


def resolve_obj(obj, vars_pool):
    """递归替换 dict/list 里的 ${var}(如 json body 里的 ${timestamp}、${user_id})。"""
    if isinstance(obj, str):
        return resolve(obj, vars_pool)
    elif isinstance(obj, dict):
        return {k: resolve_obj(v, vars_pool) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [resolve_obj(i, vars_pool) for i in obj]
    return obj


def extract(resp, extract_cfg, vars_pool):
    """按 extract 配置的 JSONPath 从响应提取字段,写入 vars_pool。

    使用 jsonpath 库解析标准表达式($.id / $[0].id / $.data[0].id 嵌套)。
    提取失败不中断,打印 [WARN];后续 ${var} 找不到会原样保留,通常导致 404。
    """
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
