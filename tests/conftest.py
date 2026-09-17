import pytest
import os
import sys
import json
import urllib.request
import time
from datetime import timedelta
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

# ========== 通知模块 ==========


_session_start_time = None


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """pytest 启动：记录时间，检查 webhook"""
    global _session_start_time
    _session_start_time = time.time()

    if os.environ.get('WECHAT_WEBHOOK'):
        print("[NOTIFY] Webhook configured, will send notification after tests.")
    else:
        print("[NOTIFY] No WECHAT_WEBHOOK found, skipping notification.")


def _send_wechat(webhook_url, content):
    """发送企微 Markdown 通知"""
    payload = json.dumps(
        {"msgtype": "markdown", "markdown": {"content": content}},
        ensure_ascii=False
    ).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        print(f"[NOTIFY] Wechat success: {resp.read().decode('utf-8')}")
    except Exception as e:
        print(f"[NOTIFY] Wechat failed: {e}")


def _build_links():
    """构建报告和控制台链接"""
    jenkins_url = os.environ.get('JENKINS_PUBLIC_URL') or os.environ.get('JENKINS_URL')
    job_name = os.environ.get('JOB_NAME')
    build_number = os.environ.get('BUILD_NUMBER')

    if jenkins_url and job_name and build_number:
        jenkins_url = jenkins_url.rstrip('/')
        base = f"{jenkins_url}/job/{job_name}/{build_number}/"
        return base + 'allure/', base + 'console'

    return None, None


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """
    pytest 会话结束：组装并发送通知。
    无 WECHAT_WEBHOOK 时静默跳过，不影响任何测试逻辑。
    """
    global _session_start_time

    webhook = os.environ.get('WECHAT_WEBHOOK')
    if not webhook:
        return

    # 统计
    passed = 0
    failed = 0
    skipped = 0
    try:
        if hasattr(session, 'testscollected') and session.testscollected > 0:
            passed = session.testscollected - (session.testsfailed or 0) - (session.skipped or 0)
            failed = session.testsfailed or 0
            skipped = session.skipped or 0
    except Exception:
        pass

    # 耗时
    duration = os.environ.get('BUILD_DURATION')
    if not duration and _session_start_time:
        duration = str(timedelta(seconds=int(time.time() - _session_start_time)))
    elif not duration:
        duration = 'N/A'

    # 状态
    status = 'success' if exitstatus == 0 else 'failure'
    icon = '\u2705' if status == 'success' else '\u274c'
    title = '接口自动化测试通过' if status == 'success' else '接口自动化测试失败'

    # 环境信息
    job_name = os.environ.get('JOB_NAME', 'api-auto-test')
    build_number = os.environ.get('BUILD_NUMBER', 'local')
    branch = os.environ.get('BRANCH_NAME') or os.environ.get('GIT_BRANCH', 'local')

    # 链接
    report_url, detail_url = _build_links()
    report_text = f"[点击查看 Allure]({report_url})" if report_url else "[本地运行，无报告链接]"
    detail_text = f"[点击查看控制台]({detail_url})" if detail_url else "[本地运行，无日志链接]"

    # 组装消息
    msg = f"{icon} **{title}**\n" \
          f"> 项目：{job_name} | 构建：#{build_number}\n" \
          f"> 分支：{branch}\n" \
          f"> 结果：通过 {passed} | 失败 {failed} | 跳过 {skipped}\n" \
          f"> 耗时：{duration}\n" \
          f"> 报告：{report_text}\n" \
          f"> 详情：{detail_text}\n"

    if status == 'failure':
        msg += f"> <@all> 请关注构建失败！\n"

    _send_wechat(webhook, msg)