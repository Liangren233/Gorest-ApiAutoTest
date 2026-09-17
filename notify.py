# -*- coding: utf-8 -*-
import sys
import json
import urllib.request

def main():
    if len(sys.argv) < 3:
        print("Usage: python notify.py <webhook_url> <message_file>")
        sys.exit(1)

    webhook = sys.argv[1]
    msg_file = sys.argv[2]

    with open(msg_file, 'r', encoding='utf-8') as f:
        content = f.read()

    payload = json.dumps(
        {"msgtype": "markdown", "markdown": {"content": content}},
        ensure_ascii=False
    ).encode("utf-8")

    req = urllib.request.Request(
        webhook,
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
    main()