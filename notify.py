# -*- coding: utf-8 -*-
import sys
import json
import urllib.request
import os


def build_message(status):
    # 基础信息从 Jenkins 自动注入的环境变量读取
    job_name = os.environ.get('JOB_NAME', 'N/A')
    build_number = os.environ.get('BUILD_NUMBER', 'N/A')
    branch = os.environ.get('BRANCH_NAME') or 'master'

    # 进阶：读取 Jenkinsfile 传入的精确耗时
    duration = os.environ.get('BUILD_DURATION_STR') or '见详情页'

    # 基础链接
    build_url = os.environ.get('BUILD_URL') or ''

    if build_url:
        report_url = build_url + 'allure/'
        detail_url = build_url + 'console'
    else:
        report_url = 'N/A'
        detail_url = 'N/A'

    # 状态标识
    if status == 'success':
        icon = '\u2705'
        title = '接口自动化测试通过'
    else:
        icon = '\u274c'
        title = '接口自动化测试失败'

    # 组装 Markdown 消息
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