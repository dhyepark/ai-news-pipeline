"""AI 뉴스 파이프라인 진입점.

수집 → 요약 → Slack 전송 → 전송한 글 기록(중복 방지) 순으로 실행한다.
GitHub Actions와 로컬에서 동일하게 동작한다.
"""
import sys

from src import collect, config, notify, summarize


def main() -> int:
    # 필수 환경변수 확인
    missing = [
        name
        for name, val in [
            ("GEMINI_API_KEY", config.GEMINI_API_KEY),
            ("SLACK_WEBHOOK_URL", config.SLACK_WEBHOOK_URL),
        ]
        if not val
    ]
    if missing:
        print(f"[main] 환경변수 누락: {', '.join(missing)}")
        return 1

    # 1. 수집 (+ 중복 제거)
    items = collect.collect_new_items()
    if not items:
        print("[main] 새로운 소식이 없습니다. 종료.")
        return 0

    # 2. AI 요약/선별
    summarized = summarize.summarize(items, config.MAX_ITEMS)
    if not summarized:
        print("[main] 요약 결과가 없습니다. 종료.")
        return 0

    # 3. Slack 전송
    ok = notify.send(summarized)

    # 4. 전송 성공 시에만 seen 기록 (실패하면 다음 실행에서 재시도)
    if ok:
        collect.mark_sent(items)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())