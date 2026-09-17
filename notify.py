#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""企微通知脚本，供 Jenkins pipeline 调用"""

import sys
import json
import urllib.request
import os


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
        result = resp.read().decode("utf-8")
        print(f"Wechat notify success: {result}")
        return True
    except Exception as e:
        print(f"Wechat notify failed: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python notify.py <webhook_url> <message_file>")
        sys.exit(1)

    webhook = sys.argv[1]
    msg_file = sys.argv[2]

    with open(msg_file, encoding="utf-8") as f:
        content = f.read()

    success = send_wechat(webhook, content)
    sys.exit(0 if success else 1)