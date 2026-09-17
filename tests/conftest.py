import os
import time
import json
import pytest
import urllib.request
from datetime import timedelta

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

    # 统计
    passed = _test_stats["passed"]
    failed = _test_stats["failed"]
    skipped = _test_stats["skipped"]
    if passed == 0 and failed == 0 and skipped == 0:
        try:
            failed = session.testsfailed or 0
            passed = (session.testscollected or 0) - failed
        except Exception:
            pass

    # 耗时
    duration = str(timedelta(seconds=int(time.time() - _session_start_time))) if _session_start_time else 'N/A'

    # 状态
    is_success = exitstatus == 0
    icon = '✅' if is_success else '❌'
    title = '接口自动化测试通过' if is_success else '接口自动化测试失败'

    # 项目信息
    job_name = os.environ.get('JOB_NAME', 'api-auto-test')
    build_number = os.environ.get('BUILD_NUMBER', 'local')

    # 组装消息 —— 无链接，纯喊话
    msg = f"{icon} **{title}**\n" \
          f"> **项目**：{job_name}\n" \
          f"> **构建**：#{build_number}\n" \
          f"> **耗时**：{duration}\n" \
          f"> **结果**：通过 {passed} | 失败 {failed} | 跳过 {skipped}\n"

    if not is_success:
        msg += f"\n> <@all> **构建失败！请前往 Jenkins 机器上自行查看详情。**"

    _send_wechat(webhook, msg)