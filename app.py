import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
from db import (
    init_db, get_setting, set_setting, get_feeds, add_feed, delete_feed, toggle_feed,
    get_repos, add_repo, delete_repo, get_reports,
)
from modules.voice import list_voices
from modules.llm import list_models
from scheduler import start_scheduler

app = Flask(__name__)
app.secret_key = os.urandom(24)

init_db()
scheduler = start_scheduler()


# ── Dashboard ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    news = get_reports("news", limit=5)
    github = get_reports("github", limit=5)
    education = get_reports("education", limit=5)
    return render_template("index.html", news=news, github=github, education=education)


# ── Settings ───────────────────────────────────────────────────────────────────

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        set_setting("persona", request.form["persona"])
        set_setting("tts_voice", request.form["tts_voice"])
        set_setting("ollama_model", request.form["ollama_model"])
        return redirect(url_for("settings"))
    persona = get_setting("persona", "")
    tts_voice = get_setting("tts_voice", "en-US-AndrewNeural")
    ollama_model = get_setting("ollama_model", "llama3")
    voices = list_voices()
    models = list_models()
    return render_template("settings.html", persona=persona, tts_voice=tts_voice,
                           ollama_model=ollama_model, voices=voices, models=models)


# ── RSS Feeds ──────────────────────────────────────────────────────────────────

@app.route("/feeds", methods=["GET", "POST"])
def feeds():
    if request.method == "POST":
        add_feed(request.form["name"], request.form["url"])
        return redirect(url_for("feeds"))
    return render_template("feeds.html", feeds=get_feeds())


@app.route("/feeds/delete/<int:feed_id>", methods=["POST"])
def delete_feed_route(feed_id):
    delete_feed(feed_id)
    return redirect(url_for("feeds"))


@app.route("/feeds/toggle/<int:feed_id>", methods=["POST"])
def toggle_feed_route(feed_id):
    active = request.form.get("active") == "1"
    toggle_feed(feed_id, active)
    return redirect(url_for("feeds"))


# ── Repos ──────────────────────────────────────────────────────────────────────

@app.route("/repos", methods=["GET", "POST"])
def repos():
    if request.method == "POST":
        raw = request.form["repo"].strip()
        for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
            if raw.startswith(prefix):
                raw = raw[len(prefix):]
                break
        parts = raw.strip("/").split("/")
        if len(parts) >= 2:
            add_repo(parts[0], parts[1])
    return render_template("repos.html", repos=get_repos())


@app.route("/repos/delete/<int:repo_id>", methods=["POST"])
def delete_repo_route(repo_id):
    delete_repo(repo_id)
    return redirect(url_for("repos"))


@app.route("/repos/search")
def search_repos_route():
    from modules.github_analyzer import search_repos
    q = request.args.get("q", "").strip()
    results = search_repos(q) if q else []
    return jsonify(results)


# ── Reports ────────────────────────────────────────────────────────────────────

@app.route("/reports/<report_type>")
def report_list(report_type):
    reports = get_reports(report_type, limit=20)
    return render_template("reports.html", reports=reports, report_type=report_type)


@app.route("/report/<int:report_id>")
def report_detail(report_id):
    from db import get_conn
    conn = get_conn()
    row = conn.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    conn.close()
    if not row:
        return "Report not found", 404
    return render_template("report_detail.html", report=dict(row))


# ── Manual Triggers (AJAX) ─────────────────────────────────────────────────────

@app.route("/news")
def news_page():
    return render_template("news.html")


@app.route("/news/headlines")
def news_headlines():
    from modules.news import fetch_headlines
    return jsonify(fetch_headlines())


@app.route("/news/compile", methods=["POST"])
def news_compile():
    from modules.news import compile_script
    data = request.get_json()
    selected = data.get("selected", [])
    skipped = data.get("skipped", [])
    result = compile_script(selected, skipped)
    return jsonify(result)


@app.route("/run/github", methods=["POST"])
def run_github():
    from modules.github_analyzer import run_github_analysis
    result = run_github_analysis()
    return jsonify(result)


@app.route("/run/education", methods=["POST"])
def run_education():
    from modules.education import generate_lesson
    topic = request.json.get("topic", "") if request.is_json else request.form.get("topic", "")
    voice = get_setting("tts_voice", "default")
    result = generate_lesson(topic=topic, tts_voice=voice)
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
