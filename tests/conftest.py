import pytest
import os
import time
import json
import urllib.request
from datetime import timedelta, datetime

# ========== Fixture 区 ==========

@pytest.fixture
def client():
    """每条用例新建一个 ApiClient(无状态,可安全复用)。"""
    from core.client import ApiClient
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
        from core.client import ApiClient
        cleaner = ApiClient()
        print(f"\n[CLEANUP] session 结束，兜底清理 {len(pool['__cleanup__'])} 个资源")
        for resource, rid in reversed(pool["__cleanup__"]):  # 后注册先删(通常是最新依赖)
            try:
                resp = cleaner.request("DELETE", f"/{resource}/{rid}")
                print(f"  [CLEANUP] {resource}/{rid} -> {resp.status_code}")  # 404 是预期(资源已删),其他码才告警
            except Exception as e:
                print(f"  [CLEANUP] failed {resource}/{rid}: {e}")


@pytest.fixture(scope="session")
def run_env(request):
    return request.config.getoption("--env", default="test")


def pytest_generate_tests(metafunc):
    """数据驱动入口:收集阶段读 YAML,把每条 case 变成参数化用例。

    ids 用 case["name"] 作测试 ID,所以报告里显示 test_api[创建新用户] 而非 test_api[0]。
    新增用例只需改 YAML,无需动 Python(零代码扩展)。
    """
    if "case" in metafunc.fixturenames:
        from core.yaml_util import load_yaml
        raw = load_yaml("data/users.yaml")
        cases = raw["cases"] if isinstance(raw, dict) and "cases" in raw else raw
        ids = [c.get("name", "未命名") for c in cases]
        metafunc.parametrize("case", cases, ids=ids)


# ========== 企微通知模块 ==========

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


def _send_wechat(webhook, msg):
    """POST markdown 到企微机器人,失败不中断测试。"""
    payload = json.dumps(
        {"msgtype": "markdown", "markdown": {"content": msg}},
        ensure_ascii=False
    ).encode("utf-8")
    req = urllib.request.Request(
        webhook, data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        print("[NOTIFY] Wechat sent successfully")
    except Exception as e:
        print(f"[NOTIFY] Wechat failed: {e}")


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """session 结束:组装通过/失败/跳过统计 + 耗时,发企微通知。失败 @all,成功静默。"""
    webhook = os.environ.get('WECHAT_WEBHOOK')
    if not webhook:
        return  # 未配 Webhook 静默跳过(本地常用)

    passed = _test_stats["passed"]
    failed = _test_stats["failed"]
    skipped = _test_stats["skipped"]
    if passed == 0 and failed == 0 and skipped == 0:
        try:
            failed = session.testsfailed or 0
            passed = (session.testscollected or 0) - failed
        except Exception:
            pass

    duration = str(timedelta(seconds=int(time.time() - _session_start_time))) if _session_start_time else 'N/A'
    start_time_str = datetime.fromtimestamp(_session_start_time).strftime('%Y-%m-%d %H:%M') if _session_start_time else 'N/A'

    is_success = exitstatus == 0
    icon = '✅' if is_success else '❌'
    title = '接口自动化测试通过' if is_success else '接口自动化测试失败'

    job_name = os.environ.get('JOB_NAME', 'Gorest-ApiAutoTest-test')  # Jenkins 注入,本地默认
    build_number = os.environ.get('BUILD_NUMBER', 'local')           # Jenkins 注入,本地默认

    msg = f"{icon} **{title}**\n" \
          f"> **项目**：{job_name}\n" \
          f"> **构建**：#{build_number} {start_time_str}\n" \
          f"> **耗时**：{duration}\n" \
          f"> **结果**：通过 {passed} | 失败 {failed} | 跳过 {skipped}\n"

    if not is_success:
        msg += f"\n> <@all> **构建失败！请前往 Jenkins 机器上自行查看详情。**"

    _send_wechat(webhook, msg)
