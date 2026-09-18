import pytest
import os
import time
import json
import urllib.request
from datetime import timedelta, datetime

# ========== Fixture 区（原有，不能删） ==========

@pytest.fixture
def client():
    from core.client import ApiClient
    return ApiClient()

@pytest.fixture(scope="session")
def vars_pool():
    pool = {
        "timestamp": int(time.time() * 1000),
        "due_date": (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        "__cleanup__": [],  # [(resource, id), ...] session 结束兜底删除
    }
    yield pool
    # teardown: 兜底清理未删除的资源（用例中途失败时保底）
    if pool["__cleanup__"]:
        from core.client import ApiClient
        cleaner = ApiClient()
        print(f"\n[CLEANUP] session 结束，兜底清理 {len(pool['__cleanup__'])} 个资源")
        for resource, rid in reversed(pool["__cleanup__"]):
            try:
                resp = cleaner.request("DELETE", f"/{resource}/{rid}")
                print(f"  [CLEANUP] {resource}/{rid} -> {resp.status_code}")
            except Exception as e:
                print(f"  [CLEANUP] failed {resource}/{rid}: {e}")

@pytest.fixture(scope="session")
def run_env(request):
    return request.config.getoption("--env", default="test")

def pytest_generate_tests(metafunc):
    if "case" in metafunc.fixturenames:
        from core.yaml_util import load_yaml
        raw = load_yaml("data/users.yaml")          # ← 改文件名
        cases = raw["cases"] if isinstance(raw, dict) and "cases" in raw else raw
        ids = [c.get("name", "未命名") for c in cases]
        metafunc.parametrize("case", cases, ids=ids)

# ========== 通知模块（追加在末尾） ==========

_test_stats = {"passed": 0, "failed": 0, "skipped": 0}
_session_start_time = None


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    global _session_start_time
    _session_start_time = time.time()
    _test_stats["passed"] = 0
    _test_stats["failed"] = 0
    _test_stats["skipped"] = 0


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
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
    webhook = os.environ.get('WECHAT_WEBHOOK')
    if not webhook:
        return

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

    # 开始时间格式化
    start_time_str = datetime.fromtimestamp(_session_start_time).strftime('%Y-%m-%d %H:%M') if _session_start_time else 'N/A'

    is_success = exitstatus == 0
    icon = '✅' if is_success else '❌'
    title = '接口自动化测试通过' if is_success else '接口自动化测试失败'

    job_name = os.environ.get('JOB_NAME', 'Gorest-ApiAutoTest-test')
    build_number = os.environ.get('BUILD_NUMBER', 'local')

    msg = f"{icon} **{title}**\n" \
          f"> **项目**：{job_name}\n" \
          f"> **构建**：#{build_number} {start_time_str}\n" \
          f"> **耗时**：{duration}\n" \
          f"> **结果**：通过 {passed} | 失败 {failed} | 跳过 {skipped}\n"

    if not is_success:
        msg += f"\n> <@all> **构建失败！请前往 Jenkins 机器上自行查看详情。**"

    _send_wechat(webhook, msg)