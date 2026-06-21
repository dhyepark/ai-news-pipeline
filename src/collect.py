"""뉴스 수집 단계.

Hacker News API와 기업/미디어 RSS에서 최근 AI 관련 글을 모은다.
이미 보낸 글은 seen.json으로 걸러 중복 전송을 막는다.
"""
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import requests

from . import config

HN_TOP_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"
# 상위 스토리 중 이 개수만 검사한다 (전체 검사하면 느림).
HN_SCAN_LIMIT = 60


def _now() -> datetime:
    return datetime.now(timezone.utc)


# 키워드를 단어 경계로 매칭한다 ("ai"가 "brain"/"raises"에 걸리는 오탐 방지).
_KEYWORD_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in config.HN_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def _is_ai_related(title: str) -> bool:
    return bool(_KEYWORD_RE.search(title))


def collect_hackernews() -> list[dict]:
    """Hacker News 상위 글 중 AI 관련 + 최근 글만 반환한다."""
    items: list[dict] = []
    cutoff = _now() - timedelta(hours=config.LOOKBACK_HOURS)
    try:
        ids = requests.get(HN_TOP_URL, timeout=15).json()[:HN_SCAN_LIMIT]
    except Exception as e:  # noqa: BLE001
        print(f"[collect] HN 목록 조회 실패: {e}")
        return items

    for story_id in ids:
        try:
            story = requests.get(
                HN_ITEM_URL.format(id=story_id), timeout=15
            ).json()
        except Exception:  # noqa: BLE001
            continue
        if not story or story.get("type") != "story":
            continue
        title = story.get("title", "")
        if not _is_ai_related(title):
            continue
        published = datetime.fromtimestamp(story.get("time", 0), tz=timezone.utc)
        if published < cutoff:
            continue
        url = story.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
        items.append(
            {
                "id": f"hn-{story_id}",
                "title": title,
                "url": url,
                "source": "Hacker News",
                "points": story.get("score", 0),
                "published": published.isoformat(),
            }
        )
        time.sleep(0.05)  # API 예의상 약간 쉼
    return items


def collect_rss() -> list[dict]:
    """설정된 RSS 피드에서 최근 글을 반환한다."""
    items: list[dict] = []
    cutoff = _now() - timedelta(hours=config.LOOKBACK_HOURS)

    for feed_url in config.RSS_FEEDS:
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as e:  # noqa: BLE001
            print(f"[collect] RSS 실패 {feed_url}: {e}")
            continue

        source = parsed.feed.get("title", feed_url)
        for entry in parsed.entries:
            published = _entry_datetime(entry)
            if published and published < cutoff:
                continue
            link = entry.get("link", "")
            if not link:
                continue
            items.append(
                {
                    "id": f"rss-{entry.get('id', link)}",
                    "title": entry.get("title", "(제목 없음)"),
                    "url": link,
                    "source": source,
                    "points": None,
                    "published": (published or _now()).isoformat(),
                }
            )
    return items


def _entry_datetime(entry) -> datetime | None:
    """RSS 엔트리에서 발행 시각을 UTC datetime으로 뽑는다."""
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)
    return None


# --- 중복 제거 (상태 관리) ---

def load_seen(path: str) -> set[str]:
    p = Path(path)
    if not p.exists():
        return set()
    try:
        return set(json.loads(p.read_text()))
    except Exception:  # noqa: BLE001
        return set()


def save_seen(path: str, seen: set[str], keep: int = 2000) -> None:
    """최근 항목 위주로 잘라서 저장한다 (파일 무한 증가 방지)."""
    Path(path).write_text(json.dumps(sorted(seen)[-keep:], ensure_ascii=False))


def collect_new_items() -> list[dict]:
    """모든 소스에서 수집 후, 이미 본 글을 제외한 새 글만 반환한다."""
    seen = load_seen(config.SEEN_FILE)
    raw = collect_hackernews() + collect_rss()

    # URL/제목 기준 + seen 기준으로 중복 제거
    fresh: list[dict] = []
    batch_ids: set[str] = set()
    for item in raw:
        if item["id"] in seen or item["id"] in batch_ids:
            continue
        batch_ids.add(item["id"])
        fresh.append(item)

    print(f"[collect] 수집 {len(raw)}건 → 새 글 {len(fresh)}건")
    return fresh


def mark_sent(items: list[dict]) -> None:
    """전송 완료한 항목을 seen에 기록한다."""
    seen = load_seen(config.SEEN_FILE)
    seen.update(i["id"] for i in items)
    save_seen(config.SEEN_FILE, seen)
