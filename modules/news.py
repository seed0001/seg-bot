import feedparser
from datetime import datetime, timezone
from db import get_feeds, get_setting, get_source_scores, record_selections, save_report
from modules.llm import generate
from modules.voice import synthesize


def fetch_headlines(max_per_feed: int = 10) -> list[dict]:
    """Pull all headlines from active feeds, sorted by preference score."""
    feeds = [f for f in get_feeds() if f["active"]]
    scores = get_source_scores()
    headlines = []

    for feed in feeds:
        try:
            parsed = feedparser.parse(feed["url"])
            for entry in parsed.entries[:max_per_feed]:
                headlines.append({
                    "source": feed["name"],
                    "title": entry.get("title", "").strip(),
                    "summary": entry.get("summary", entry.get("description", "")).strip(),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "score": scores.get(feed["name"], 0.5),
                })
        except Exception as e:
            print(f"[RSS error] {feed['url']}: {e}")

    # Sort: sources the user picks most float to the top
    headlines.sort(key=lambda h: h["score"], reverse=True)
    return headlines


def compile_script(selected: list[dict], skipped: list[dict]) -> dict:
    """
    selected  — headlines the user checked
    skipped   — headlines shown but not checked (used for preference learning)
    Returns dict with script text and audio path.
    """
    if not selected:
        return {"error": "No headlines selected."}

    record_selections(selected, skipped)

    persona = get_setting("persona", "You are a direct, no-nonsense tech journalist from the UK.")
    today = datetime.now(timezone.utc).strftime("%A, %d %B %Y")

    bullet_list = "\n".join(
        f"- [{h['source']}] {h['title']}: {h['summary'][:200]}" for h in selected
    )

    prompt = f"""Today is {today}. The producer has selected these stories for today's segment:

{bullet_list}

Write the broadcast script. Spoken word only — no bullet points, no headers, no stage directions.
Cover every selected story. Your commentary, your take. Make it sound like a real broadcast, not a listicle."""

    script = generate(prompt, system=persona)

    if "[LLM error" in script:
        return {"error": script}

    tts_voice = get_setting("tts_voice", "en-US-AndrewNeural")
    audio_path = synthesize(script, voice=tts_voice)
    report_id = save_report("news", script, audio_path)

    return {"id": report_id, "script": script, "audio_path": audio_path}
