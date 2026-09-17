# -*- coding: utf-8 -*-
import sys
import json
import urllib.request
import os


def build_message(status, duration, report_url, detail_url):
    job_name = os.environ.get('JOB_NAME', 'N/A')
    build_number = os.environ.get('BUILD_NUMBER', 'N/A')
    branch = os.environ.get('BRANCH_NAME') or 'master'

    if status == 'success':
        icon = '\u2705'
        title = '接口自动化测试通过'
    else:
        icon = '\u274c'
        title = '接口自动化测试失败'

    msg = f"{icon} **{title}**\n" \
          f"> 项目：{job_name}\n" \
          f"> 构建：#{build_number}\n" \
          f"> 分支：{branch}\n" \
          f"> 耗时：{duration}\n" \
          f"> 报告：{report_url}\n" \
          f"> 详情：{detail_url}"

    return msg


def send_wechat(webhook_url, content):
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
        print("Wechat notify success:", resp.read().decode("utf-8"))
    except Exception as e:
        print("Wechat notify failed:", e)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: python notify.py <webhook> <status> <duration> <report_url> <detail_url>")
        sys.exit(1)

    webhook = sys.argv[1]
    status = sys.argv[2]
    duration = sys.argv[3]
    report_url = sys.argv[4]
    detail_url = sys.argv[5]

    # 调试打印，确认参数是否传进来了
    print(f"[DEBUG] duration={duration}, report={report_url}, detail={detail_url}")

    msg = build_message(status, duration, report_url, detail_url)
    send_wechat(webhook, msg)