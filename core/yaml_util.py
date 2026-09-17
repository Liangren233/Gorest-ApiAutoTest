import os
import yaml

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# print(_ROOT)

def load_yaml(path):
    abs_path = os.path.join(_ROOT, path)
    with open(abs_path,"r",encoding="utf-8") as f:
        return yaml.safe_load(f) or {}