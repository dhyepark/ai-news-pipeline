"""파이프라인 전역 설정. 수집 소스와 환경변수를 한곳에서 관리한다."""
import os

from dotenv import load_dotenv

load_dotenv()

# --- 비밀값 (GitHub Actions에서는 Secrets로 주입) ---
# Gemini API 키는 Google AI Studio(https://aistudio.google.com/apikey)에서 무료 발급.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

# --- 모델 ---
# 무료 티어로 충분한 경량 모델. 모델명 오류가 나면 다른 flash 계열로 바꾸면 된다.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# --- 수집 동작 설정 ---
# 최근 N시간 안의 글만 다룬다. 기업 블로그는 매일 글이 없어 48h가 적당.
# (중복은 seen.json으로 막으므로 창을 넓혀도 같은 글이 재전송되지 않는다.)
LOOKBACK_HOURS = int(os.environ.get("LOOKBACK_HOURS", "48"))
# Slack으로 보낼 최대 항목 수.
MAX_ITEMS = int(os.environ.get("MAX_ITEMS", "8"))
# 본 기사 ID를 저장해 중복 전송을 막는 파일.
SEEN_FILE = os.environ.get("SEEN_FILE", "seen.json")

# Hacker News에서 이 키워드들이 제목에 있으면 AI 관련으로 본다.
HN_KEYWORDS = [
    "ai", "llm", "gpt", "claude", "gemini", "openai", "anthropic",
    "machine learning", "deep learning", "neural", "transformer",
    "diffusion", "agent", "rag", "mistral", "llama", "deepseek",
]

# 기업/미디어 RSS 피드 목록. 자유롭게 추가/삭제하면 된다.
RSS_FEEDS = [
    # --- 기업/연구소 블로그 ---
    "https://openai.com/blog/rss.xml",
    "https://deepmind.google/blog/rss.xml",
    "https://blog.google/technology/ai/rss/",
    "https://huggingface.co/blog/feed.xml",
    # Anthropic은 공식 RSS가 없어 Google News 검색 피드로 대체
    "https://news.google.com/rss/search?q=Anthropic%20Claude%20AI&hl=en-US&gl=US&ceid=US:en",
    # --- 미디어 ---
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "https://www.technologyreview.com/topic/artificial-intelligence/feed",
    "https://arstechnica.com/ai/feed/",
]
