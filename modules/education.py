import json
from db import get_repos, get_latest_snapshot, get_setting, save_report
from modules.llm import generate
from modules.voice import synthesize


def build_project_context() -> str:
    repos = [r for r in get_repos() if r["active"]]
    if not repos:
        return "No projects currently tracked."

    lines = []
    for repo in repos:
        snap = get_latest_snapshot(repo["id"])
        desc = repo.get("description") or "No description"
        if snap:
            topics = json.loads(snap.get("topics") or "[]")
            topics_str = ", ".join(topics) if topics else "none"
            summary = snap.get("summary") or "No summary yet"
            lines.append(
                f"- {repo['owner']}/{repo['name']}: {desc}\n"
                f"  Topics: {topics_str}\n"
                f"  Status: {summary}"
            )
        else:
            lines.append(f"- {repo['owner']}/{repo['name']}: {desc}")

    return "\n".join(lines)


def generate_lesson(topic: str = "", tts_voice: str = "default") -> dict:
    persona = get_setting("persona", "You are a direct, no-nonsense tech educator from the UK.")
    project_context = build_project_context()

    if topic:
        topic_instruction = f"The lesson topic requested is: {topic}"
    else:
        topic_instruction = (
            "Pick the most relevant educational topic based on the current projects. "
            "Choose something that would genuinely help someone working on these projects right now."
        )

    prompt = f"""You are delivering a technical lesson. Here are the current projects for context:

{project_context}

{topic_instruction}

Write a structured lesson as if you're teaching a class. Include:
1. What we're learning and why it matters (tie it to the projects if possible)
2. Core concepts — explained clearly, no hand-waving
3. A practical example or mini-exercise
4. Key takeaways

Keep it focused — one concept done well beats five done badly. Speak directly, no corporate waffle."""

    lesson = generate(prompt, system=persona)
    audio_path = synthesize(lesson, voice=tts_voice)
    report_id = save_report("education", lesson, audio_path)
    return {"id": report_id, "lesson": lesson, "audio_path": audio_path}
