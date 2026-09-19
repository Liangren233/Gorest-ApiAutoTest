"""pytest 粘合层:fixture 生命周期、YAML 参数化、结果通知钩子。

本文件只做 pytest 协议相关的事;HTTP/数据处理/通知等业务能力均在 core/ 下,
通过下方薄钩子委托调用,避免 conftest 退化为"垃圾桶"。
"""
import time
import pytest
from datetime import timedelta, datetime

from core.client import ApiClient
from core.context import load_yaml
from core import notifier


# ========== Fixture 区 ==========

@pytest.fixture
def client():
    """每条用例新建一个 ApiClient(无状态,可安全复用)。"""
    return ApiClient()


@pytest.fixture(scope="session")
def vars_pool():
    """session 级变量池:整轮测试共享一个 dict,前序用例 extract 的值后序用例可读。

    之所以 session 级而非 function 级:CRUD 是跨用例链路(创建→更新→删除),
    前序用例提取的 id 要给后序用例用,function 级每次新建会断开关联。
    初始含 timestamp(毫秒,生成唯一 email 避免跨运行碰撞)、due_date(todos 用)、
    __cleanup__(session 结束兜底删除的资源列表)。
    """
    pool = {
        "timestamp": int(time.time() * 1000),  # 毫秒级,避免同秒运行 email 碰撞
        "due_date": (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),  # todos 的 due_on
        "__cleanup__": [],  # session 结束兜底删除,防止用例中途失败残留垃圾数据
    }
    yield pool
    # teardown:兜底删除已注册但未被用例自己删掉的资源
    if pool["__cleanup__"]:
        cleaner = ApiClient()
        print(f"\n[CLEANUP] session 结束，兜底清理 {len(pool['__cleanup__'])} 个资源")
        for resource, rid in reversed(pool["__cleanup__"]):  # 后注册先删(通常是最新依赖)
            try:
                resp = cleaner.request("DELETE", f"/{resource}/{rid}")
                print(f"  [CLEANUP] {resource}/{rid} -> {resp.status_code}")  # 404 是预期(资源已删),其他码才告警
            except Exception as e:
                print(f"  [CLEANUP] failed {resource}/{rid}: {e}")


def pytest_generate_tests(metafunc):
    """数据驱动入口:收集阶段读 YAML,把每条 case 变成参数化用例。

    ids 用 case["name"] 作测试 ID,所以报告里显示 test_api[创建新用户] 而非 test_api[0]。
    新增用例只需改 YAML,无需动 Python(零代码扩展)。
    """
    if "case" in metafunc.fixturenames:
        raw = load_yaml("data/users.yaml")
        cases = raw["cases"] if isinstance(raw, dict) and "cases" in raw else raw
        ids = [c.get("name", "未命名") for c in cases]
        metafunc.parametrize("case", cases, ids=ids)


# ========== 结果统计与企微通知(薄钩子,业务逻辑在 core/notifier.py)==========

_test_stats = {"passed": 0, "failed": 0, "skipped": 0}
_session_start_time = None


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    """session 开始:记录起始时间,统计清零。"""
    global _session_start_time
    _session_start_time = time.time()
    _test_stats["passed"] = 0
    _test_stats["failed"] = 0
    _test_stats["skipped"] = 0


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """每条用例 call 阶段结束后累加 passed/failed/skipped。"""
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call":
        if rep.passed:
            _test_stats["passed"] += 1
        elif rep.failed:
            _test_stats["failed"] += 1
        elif rep.skipped:
            _test_stats["skipped"] += 1


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """session 结束:把统计结果交给 notifier 发送(未配 Webhook 时其内部静默跳过)。"""
    passed, failed, skipped = _test_stats["passed"], _test_stats["failed"], _test_stats["skipped"]
    if passed == 0 and failed == 0 and skipped == 0:
        try:
            failed = session.testsfailed or 0
            passed = (session.testscollected or 0) - failed
        except Exception:
            pass
    notifier.notify(passed, failed, skipped, exitstatus, _session_start_time)
