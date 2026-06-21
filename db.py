import sqlite3
import json
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rss_feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS repos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            active INTEGER DEFAULT 1,
            UNIQUE(owner, name)
        );

        CREATE TABLE IF NOT EXISTS repo_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_id INTEGER NOT NULL,
            snapshot_at TEXT NOT NULL,
            stars INTEGER,
            forks INTEGER,
            open_issues INTEGER,
            last_commit_sha TEXT,
            last_commit_message TEXT,
            last_commit_date TEXT,
            topics TEXT,
            summary TEXT,
            FOREIGN KEY(repo_id) REFERENCES repos(id)
        );

        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            content TEXT NOT NULL,
            audio_path TEXT
        );

        CREATE TABLE IF NOT EXISTS headline_selections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            selected INTEGER NOT NULL DEFAULT 1,
            selected_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS source_scores (
            source TEXT PRIMARY KEY,
            selected_count INTEGER DEFAULT 0,
            skipped_count INTEGER DEFAULT 0
        );
    """)

    from config import OLLAMA_MODEL, DEFAULT_TTS_VOICE

    seeds = [
        ("persona",
         "You are Rex — a no-nonsense tech journalist from the UK. "
         "You hate corporate waffle, buzzwords, and anything that smells like a press release. "
         "You speak directly, with dry wit and zero patience for fluff. "
         "You swear occasionally when something genuinely deserves it. "
         "Cut through the noise and tell people what actually matters."),
        ("ollama_model", OLLAMA_MODEL),
        ("tts_voice", DEFAULT_TTS_VOICE),
    ]
    for key, val in seeds:
        c.execute("INSERT OR IGNORE INTO settings VALUES (?, ?)", (key, val))

    default_feeds = [
        ("Hacker News",     "https://hnrss.org/frontpage"),
        ("Ars Technica",    "https://feeds.arstechnica.com/arstechnica/index"),
        ("The Verge",       "https://www.theverge.com/rss/index.xml"),
        ("TechCrunch",      "https://techcrunch.com/feed/"),
        ("GitHub Blog",     "https://github.blog/feed/"),
        ("Dev.to",          "https://dev.to/feed"),
    ]
    for name, url in default_feeds:
        c.execute("INSERT OR IGNORE INTO rss_feeds (name, url, active) VALUES (?, ?, 1)", (name, url))

    conn.commit()
    conn.close()


def get_setting(key, default=None):
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def get_feeds():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM rss_feeds ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_feed(name, url):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO rss_feeds (name, url) VALUES (?, ?)", (name, url))
    conn.commit()
    conn.close()


def delete_feed(feed_id):
    conn = get_conn()
    conn.execute("DELETE FROM rss_feeds WHERE id=?", (feed_id,))
    conn.commit()
    conn.close()


def toggle_feed(feed_id, active):
    conn = get_conn()
    conn.execute("UPDATE rss_feeds SET active=? WHERE id=?", (1 if active else 0, feed_id))
    conn.commit()
    conn.close()


def get_repos():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM repos ORDER BY owner, name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_repo(owner, name, description=""):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO repos (owner, name, description) VALUES (?, ?, ?)",
        (owner, name, description),
    )
    conn.commit()
    conn.close()


def delete_repo(repo_id):
    conn = get_conn()
    conn.execute("DELETE FROM repo_snapshots WHERE repo_id=?", (repo_id,))
    conn.execute("DELETE FROM repos WHERE id=?", (repo_id,))
    conn.commit()
    conn.close()


def get_latest_snapshot(repo_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM repo_snapshots WHERE repo_id=? ORDER BY snapshot_at DESC LIMIT 1",
        (repo_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def save_snapshot(repo_id, data: dict):
    conn = get_conn()
    conn.execute(
        """INSERT INTO repo_snapshots
           (repo_id, snapshot_at, stars, forks, open_issues,
            last_commit_sha, last_commit_message, last_commit_date, topics, summary)
           VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            repo_id,
            data.get("stars"),
            data.get("forks"),
            data.get("open_issues"),
            data.get("last_commit_sha"),
            data.get("last_commit_message"),
            data.get("last_commit_date"),
            json.dumps(data.get("topics", [])),
            data.get("summary"),
        ),
    )
    conn.commit()
    conn.close()


def save_report(report_type, content, audio_path=None):
    conn = get_conn()
    cursor = conn.execute(
        "INSERT INTO reports (type, created_at, content, audio_path) VALUES (?, datetime('now'), ?, ?)",
        (report_type, content, audio_path),
    )
    report_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return report_id


def record_selections(selected: list[dict], skipped: list[dict]):
    """Persist which headlines were picked and which were ignored."""
    conn = get_conn()
    for h in selected:
        conn.execute(
            "INSERT INTO headline_selections (source, title, selected) VALUES (?, ?, 1)",
            (h["source"], h["title"]),
        )
        conn.execute(
            "INSERT INTO source_scores (source, selected_count, skipped_count) VALUES (?, 1, 0) "
            "ON CONFLICT(source) DO UPDATE SET selected_count = selected_count + 1",
            (h["source"],),
        )
    for h in skipped:
        conn.execute(
            "INSERT INTO headline_selections (source, title, selected) VALUES (?, ?, 0)",
            (h["source"], h["title"]),
        )
        conn.execute(
            "INSERT INTO source_scores (source, selected_count, skipped_count) VALUES (?, 0, 1) "
            "ON CONFLICT(source) DO UPDATE SET skipped_count = skipped_count + 1",
            (h["source"],),
        )
    conn.commit()
    conn.close()


def get_source_scores() -> dict[str, float]:
    """Return preference score per source (higher = user picks it more)."""
    conn = get_conn()
    rows = conn.execute("SELECT source, selected_count, skipped_count FROM source_scores").fetchall()
    conn.close()
    scores = {}
    for r in rows:
        total = r["selected_count"] + r["skipped_count"]
        scores[r["source"]] = r["selected_count"] / total if total else 0.5
    return scores


def get_reports(report_type=None, limit=20):
    conn = get_conn()
    if report_type:
        rows = conn.execute(
            "SELECT * FROM reports WHERE type=? ORDER BY created_at DESC LIMIT ?",
            (report_type, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM reports ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
