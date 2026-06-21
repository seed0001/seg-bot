import requests
import json
import time
from db import (
    get_repos, get_latest_snapshot, save_snapshot, save_report, get_setting
)
from modules.llm import generate

HEADERS = {"Accept": "application/vnd.github+json"}
_rate_limited_until = 0


def _gh_get(url: str) -> dict | list | None:
    global _rate_limited_until
    if time.time() < _rate_limited_until:
        wait = int(_rate_limited_until - time.time())
        print(f"[GitHub] Rate limited, {wait}s remaining")
        return None
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            _rate_limited_until = reset
            print(f"[GitHub] Rate limit hit, resets at {time.ctime(reset)}")
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"[GitHub error] {url}: {e}")
        return None


def search_repos(query: str, per_page: int = 10) -> list[dict]:
    """Search public GitHub repos by keyword — no token needed."""
    data = _gh_get(
        f"https://api.github.com/search/repositories"
        f"?q={requests.utils.quote(query)}&sort=stars&order=desc&per_page={per_page}"
    )
    if not data or "items" not in data:
        return []
    return [
        {
            "full_name": r["full_name"],
            "owner": r["owner"]["login"],
            "name": r["name"],
            "description": r.get("description") or "",
            "stars": r["stargazers_count"],
            "language": r.get("language") or "",
            "url": r["html_url"],
        }
        for r in data["items"]
    ]


def fetch_repo_data(owner: str, name: str) -> dict | None:
    repo = _gh_get(f"https://api.github.com/repos/{owner}/{name}")
    if not repo:
        return None

    commits_data = _gh_get(f"https://api.github.com/repos/{owner}/{name}/commits?per_page=1")
    last_commit = {}
    if commits_data:
        c = commits_data[0]
        last_commit = {
            "sha": c["sha"][:7],
            "message": c["commit"]["message"].split("\n")[0],
            "date": c["commit"]["author"]["date"],
        }

    return {
        "stars": repo.get("stargazers_count", 0),
        "forks": repo.get("forks_count", 0),
        "open_issues": repo.get("open_issues_count", 0),
        "topics": repo.get("topics", []),
        "language": repo.get("language", ""),
        "description": repo.get("description", ""),
        **last_commit,
    }


def diff_snapshot(old: dict | None, new: dict) -> list[str]:
    if not old:
        return ["First time tracking this repo."]
    changes = []
    for key, label in [("stars", "Stars"), ("forks", "Forks"), ("open_issues", "Open issues")]:
        if old.get(key) != new.get(key):
            changes.append(f"{label}: {old.get(key)} → {new.get(key)}")
    if old.get("last_commit_sha") != new.get("last_commit_sha"):
        changes.append(f"New commit: {new.get('last_commit_message', '')} ({new.get('last_commit_sha', '')})")
    old_topics = set(json.loads(old.get("topics", "[]")))
    new_topics = set(new.get("topics", []))
    added = new_topics - old_topics
    removed = old_topics - new_topics
    if added:
        changes.append(f"Topics added: {', '.join(added)}")
    if removed:
        changes.append(f"Topics removed: {', '.join(removed)}")
    return changes or ["No significant changes since last check."]


def summarize_repo(owner: str, name: str, data: dict, changes: list[str]) -> str:
    persona = get_setting("persona", "You are a direct tech journalist.")
    changes_str = "\n".join(f"- {c}" for c in changes)
    topics_str = ", ".join(data.get("topics", [])) or "none"

    prompt = f"""Repo: {owner}/{name}
Description: {data.get('description', 'None provided')}
Language: {data.get('language', 'Unknown')}
Stars: {data.get('stars')} | Forks: {data.get('forks')} | Open Issues: {data.get('open_issues')}
Topics: {topics_str}
Latest commit: {data.get('last_commit_message', 'N/A')} on {data.get('last_commit_date', 'N/A')}

Changes since last check:
{changes_str}

Write a concise project status update (3-5 sentences). What's this project about, what's changed, and what direction does it seem to be heading?"""

    return generate(prompt, system=persona)


def run_github_analysis() -> dict:
    repos = [r for r in get_repos() if r["active"]]
    results = []

    for repo in repos:
        data = fetch_repo_data(repo["owner"], repo["name"])
        if not data:
            continue
        old_snapshot = get_latest_snapshot(repo["id"])
        changes = diff_snapshot(old_snapshot, data)
        summary = summarize_repo(repo["owner"], repo["name"], data, changes)
        data["summary"] = summary
        save_snapshot(repo["id"], data)
        results.append({
            "repo": f"{repo['owner']}/{repo['name']}",
            "summary": summary,
            "changes": changes,
        })

    if not results:
        full_report = "No active repos tracked or no data returned."
    else:
        sections = []
        for r in results:
            sections.append(f"## {r['repo']}\n{r['summary']}\n\nChanges:\n" + "\n".join(f"- {c}" for c in r["changes"]))
        full_report = "\n\n---\n\n".join(sections)

    report_id = save_report("github", full_report)
    return {"id": report_id, "repos_analyzed": len(results), "results": results}
