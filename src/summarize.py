"""AI 요약 단계.

수집한 기사 목록을 Gemini에게 한 번에 보내,
'오늘 주목할 소식'을 골라 한국어로 요약/정렬하게 한다.
"""
import json
import time

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from . import config

_MAX_RETRIES = 3
_SERVER_ERROR_BASE_DELAY = 5.0   # 5xx: 5 → 10 → 20s
_RATE_LIMIT_BASE_DELAY = 30.0    # 429: 30 → 60s (Gemini 무료 티어 RPM 제한 고려)

SYSTEM_PROMPT = """당신은 AI 분야 뉴스 큐레이터입니다.
주어진 기사 목록에서 가장 중요하고 흥미로운 소식을 선별해 한국어로 요약합니다.

규칙:
- 중요도(영향력, 신규성, 화제성) 순으로 정렬한다.
- 광고성/중복/사소한 글은 제외한다.
- 각 항목은 한두 문장으로 핵심만, 왜 중요한지 한 줄 덧붙인다.
- 반드시 아래 JSON 스키마로만 응답한다 (그 외 텍스트 금지).

{
  "items": [
    {
      "title": "한국어로 다듬은 제목",
      "summary": "핵심 요약 1~2문장",
      "why": "왜 중요한지 한 줄",
      "url": "원문 링크",
      "source": "출처"
    }
  ]
}"""


def summarize(items: list[dict], max_items: int) -> list[dict]:
    """기사 목록을 받아 선별·요약된 항목 리스트를 반환한다."""
    if not items:
        return []

    client = genai.Client(api_key=config.GEMINI_API_KEY)

    # 토큰 절약을 위해 모델에 필요한 필드만 추려서 전달
    compact = [
        {
            "title": i["title"],
            "url": i["url"],
            "source": i["source"],
            "points": i.get("points"),
        }
        for i in items
    ]

    user_msg = (
        f"다음은 최근 수집한 AI 관련 기사 {len(compact)}건입니다. "
        f"이 중 가장 중요한 최대 {max_items}건을 선별해 요약하세요.\n\n"
        f"{json.dumps(compact, ensure_ascii=False, indent=2)}"
    )

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            resp = client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=user_msg,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    # JSON만 반환하도록 강제해 파싱 안정성을 높인다.
                    response_mime_type="application/json",
                    temperature=0.3,
                ),
            )
            text = (resp.text or "").strip()
            return _parse_response(text)
        except genai_errors.ServerError as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES - 1:
                delay = _SERVER_ERROR_BASE_DELAY * (2 ** attempt)
                print(f"[summarize] 서버 오류 {exc.code} (시도 {attempt + 1}/{_MAX_RETRIES}) — {delay:.0f}초 후 재시도")
                time.sleep(delay)
        except genai_errors.ClientError as exc:
            if exc.code != 429:
                raise  # 400·401·403 등은 재시도해도 무의미
            last_exc = exc
            if attempt < _MAX_RETRIES - 1:
                delay = _RATE_LIMIT_BASE_DELAY * (2 ** attempt)
                print(f"[summarize] rate limit (시도 {attempt + 1}/{_MAX_RETRIES}) — {delay:.0f}초 후 재시도")
                time.sleep(delay)

    raise RuntimeError(f"[summarize] {_MAX_RETRIES}회 재시도 후 실패") from last_exc


def _parse_response(text: str) -> list[dict]:
    """모델 응답에서 JSON을 안전하게 파싱한다."""
    # response_mime_type을 지정해도 혹시 코드펜스가 붙어 오면 제거
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    try:
        data = json.loads(text)
        return data.get("items", [])
    except json.JSONDecodeError as e:
        print(f"[summarize] JSON 파싱 실패: {e}\n원문:\n{text[:500]}")
        return []