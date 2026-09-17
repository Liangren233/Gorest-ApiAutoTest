import pytest
from core.client import ApiClient
from core.yaml_util import load_yaml

# 注册命令行参数
def pytest_addoption(parser):
    parser.addoption("--env", action="store", default="test", help="运行环境: test/prod")

# session 级变量池（跨用例共享提取的值）
@pytest.fixture(scope="session")
def vars_pool():
    return {}

# 环境配置 fixture
@pytest.fixture(scope="session")
def run_env(request):
    return request.config.getoption("--env")

# 参数化驱动：从 YAML 读用例
def pytest_generate_tests(metafunc):
    if "case" in metafunc.fixturenames:
        cases = load_yaml("data/users.yaml")
        ids = [c.get("name", "未命名") for c in cases]
        metafunc.parametrize("case", cases, ids=ids)

# client fixture
@pytest.fixture
def client():
    return ApiClient()