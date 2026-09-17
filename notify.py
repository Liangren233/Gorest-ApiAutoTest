# -*- coding: utf-8 -*-
import sys
import json
import urllib.request
import os


def build_message(status):
    job_name = os.environ.get('JOB_NAME', 'N/A')
    build_number = os.environ.get('BUILD_NUMBER', 'N/A')
    branch = os.environ.get('BRANCH_NAME', 'master')
    if branch is None or branch == 'null':
        branch = 'master'
    build_url = os.environ.get('BUILD_URL', '')
    duration = os.environ.get('BUILD_DURATION', 'N/A')

    if status == 'success':
        icon = '\u2705'
        title = '接口自动化测试通过'
    else:
        icon = '\u274c'
        title = '接口自动化测试失败'

    report_url = build_url + 'allure/' if build_url else 'N/A'
    detail_url = build_url + 'console' if build_url else 'N/A'

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
    if len(sys.argv) < 3:
        print("Usage: python notify.py <webhook_url> <status>")
        sys.exit(1)

    webhook = sys.argv[1]
    status = sys.argv[2]

    msg = build_message(status)
    send_wechat(webhook, msg)