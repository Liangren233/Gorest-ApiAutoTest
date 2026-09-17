# api-auto-test/conftest.py
def pytest_addoption(parser):
    parser.addoption("--env", action="store", default="test", help="运行环境: test/prod")