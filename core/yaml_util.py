import os
import yaml

# 项目根目录(core 的上一级),用于把相对路径解析成绝对路径
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_yaml(path):
    """加载 YAML 文件,path 相对项目根。返回 dict,空文件返回 {}。"""
    abs_path = os.path.join(_ROOT, path)
    with open(abs_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
