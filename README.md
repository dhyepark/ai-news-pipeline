# 🤖 AI News Pipeline

매일 AI 최신 소식을 수집해 Gemini로 요약하고 Slack으로 보내주는 자동화 파이프라인.

## 동작 흐름

```
수집 (Hacker News + 기업/미디어 RSS)
  → AI 요약/선별 (Google Gemini, 무료 티어)
  → Slack 전송 (Incoming Webhook)
  → 전송한 글 기록 (seen.json, 중복 방지)
```

매일 **오전 8시(KST)** GitHub Actions가 자동 실행한다.

## 폴더 구조

```
.
├── main.py                     # 파이프라인 오케스트레이션
├── src/
│   ├── config.py               # 설정 + 수집 소스 목록
│   ├── collect.py              # 수집 + 중복 제거
│   ├── summarize.py            # Gemini 요약
│   └── notify.py               # Slack 전송
├── seen.json                   # 이미 보낸 글 ID (자동 갱신)
├── .github/workflows/daily.yml # 매일 8시 cron
├── requirements.txt
└── .env.example
```

## 로컬 실행

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # 값 채우기 (API 키, Webhook URL)
python main.py
```

## GitHub Actions 배포

1. 이 저장소를 GitHub에 push
2. **Settings → Secrets and variables → Actions** 에서 secret 2개 등록:
   - `GEMINI_API_KEY`
   - `SLACK_WEBHOOK_URL`
3. **Actions** 탭에서 `Daily AI News` → `Run workflow`로 수동 테스트
4. 이후 매일 08:00 KST 자동 실행

## 커스터마이징

- **수집 소스 추가/변경**: `src/config.py`의 `RSS_FEEDS`, `HN_KEYWORDS`
- **전송 개수**: `MAX_ITEMS` (기본 8)
- **수집 범위**: `LOOKBACK_HOURS` (기본 24시간)
- **모델 변경**: `GEMINI_MODEL` (기본 `gemini-2.5-flash`)

## 키 발급 안내

- **Gemini API Key**: https://aistudio.google.com/apikey → Create API key (무료, 카드 불필요)
- **Slack Webhook**: Slack 앱 생성 → Incoming Webhooks 활성화 → 채널 선택 후 URL 복사