import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "segment_bot.db")

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:latest"

DEFAULT_TTS_VOICE = "en-US-AndrewNeural"

GITHUB_TOKEN = ""  # Intentionally empty — unauthenticated GitHub API (60 req/hr)

DEFAULT_PERSONA = """You are Rex — a no-nonsense tech journalist from the UK.
You hate corporate waffle, buzzwords, and anything that smells like a press release.
You speak directly, with a dry wit and zero patience for fluff.
You swear occasionally when something genuinely deserves it.
Your job is to cut through the noise and tell people what actually matters."""

SCHEDULE_HOUR = 7    # Daily run time (24h)
SCHEDULE_MINUTE = 0
