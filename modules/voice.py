import asyncio
import os
import uuid
import edge_tts

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "audio")
DEFAULT_VOICE = "en-US-AndrewNeural"


async def _synthesize_async(text: str, voice: str, out_path: str):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)


def synthesize(text: str, voice: str = DEFAULT_VOICE) -> str | None:
    os.makedirs(AUDIO_DIR, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.mp3"
    out_path = os.path.join(AUDIO_DIR, filename)
    try:
        asyncio.run(_synthesize_async(text, voice or DEFAULT_VOICE, out_path))
        return f"audio/{filename}"
    except Exception as e:
        print(f"[Edge TTS error] {e}")
        return None


def list_voices(lang_filter: str = "") -> list[dict]:
    """Return list of Edge TTS voices. Optionally filter by language prefix e.g. 'en-'."""
    async def _list():
        return await edge_tts.list_voices()
    try:
        voices = asyncio.run(_list())
        if lang_filter:
            voices = [v for v in voices if v["Locale"].startswith(lang_filter)]
        return sorted(voices, key=lambda v: v["ShortName"])
    except Exception as e:
        print(f"[Edge TTS list_voices error] {e}")
        return []
