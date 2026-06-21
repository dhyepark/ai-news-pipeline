"""Slack 전송 단계. Incoming Webhook + Block Kit으로 보기 좋게 보낸다."""
from datetime import datetime, timezone, timedelta

import requests

from . import config

KST = timezone(timedelta(hours=9))


def _build_blocks(items: list[dict]) -> list[dict]:
    today = datetime.now(KST).strftime("%Y-%m-%d")
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"🤖 오늘의 AI 소식 ({today})"},
        },
        {"type": "divider"},
    ]

    for idx, item in enumerate(items, 1):
        title = item.get("title", "(제목 없음)")
        url = item.get("url", "")
        summary = item.get("summary", "")
        why = item.get("why", "")
        source = item.get("source", "")

        text = f"*{idx}. <{url}|{title}>*\n{summary}"
        if why:
            text += f"\n💡 _{why}_"
        if source:
            text += f"\n`{source}`"

        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": text}}
        )
        blocks.append({"type": "divider"})

    return blocks


def send(items: list[dict]) -> bool:
    """요약 항목을 Slack으로 전송한다. 성공 여부를 반환한다."""
    if not items:
        print("[notify] 보낼 항목이 없어 전송을 건너뜀")
        return False

    payload = {
        "blocks": _build_blocks(items),
        "text": f"오늘의 AI 소식 {len(items)}건",  # 알림 미리보기용 fallback
    }

    resp = requests.post(config.SLACK_WEBHOOK_URL, json=payload, timeout=15)
    if resp.status_code != 200:
        print(f"[notify] Slack 전송 실패 {resp.status_code}: {resp.text}")
        return False
    print(f"[notify] Slack 전송 완료 ({len(items)}건)")
    return True