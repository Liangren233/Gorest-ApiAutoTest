"""企微机器人通知:组装测试结果 markdown 消息并发送。

纯函数模块,不依赖 pytest;由 conftest 的 sessionfinish 钩子调用,
便于未来扩展钉钉/邮件等渠道时只改本模块。
"""
import os
import json
import urllib.request
from datetime import timedelta, datetime


def build_message(passed, failed, skipped, exitstatus, start_time):
    """根据统计结果组装企微 markdown 消息。失败 @all,成功静默不 @。"""
    is_success = exitstatus == 0
    icon = '✅' if is_success else '❌'
    title = '接口自动化测试通过' if is_success else '接口自动化测试失败'

    duration = str(timedelta(seconds=int(datetime.now().timestamp() - start_time))) if start_time else 'N/A'
    start_time_str = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M') if start_time else 'N/A'

    job_name = os.environ.get('JOB_NAME', 'Gorest-ApiAutoTest-test')  # Jenkins 注入,本地默认
    build_number = os.environ.get('BUILD_NUMBER', 'local')           # Jenkins 注入,本地默认

    msg = f"{icon} **{title}**\n" \
          f"> **项目**：{job_name}\n" \
          f"> **构建**：#{build_number} {start_time_str}\n" \
          f"> **耗时**：{duration}\n" \
          f"> **结果**：通过 {passed} | 失败 {failed} | 跳过 {skipped}\n"

    if not is_success:
        msg += f"\n> <@all> **构建失败！请前往 Jenkins 机器上自行查看详情。**"
    return msg


def send_wechat(webhook, msg):
    """POST markdown 到企微机器人,网络异常只打印不抛出(通知失败不影响测试退出码)。"""
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


def notify(passed, failed, skipped, exitstatus, start_time):
    """通知门面:未配 WECHAT_WEBHOOK 静默跳过(本地常用),CI 配置后自动发送。"""
    webhook = os.environ.get('WECHAT_WEBHOOK')
    if not webhook:
        return
    msg = build_message(passed, failed, skipped, exitstatus, start_time)
    send_wechat(webhook, msg)
