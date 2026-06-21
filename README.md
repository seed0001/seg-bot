# Segment Bot

A personal AI reporter that runs daily segments, analyzes your GitHub projects, and teaches you stuff.

## Requirements

- Python 3.11+
- [Ollama](https://ollama.ai) running locally (`ollama serve`)
- [LuxTTS](https://github.com/luxlabs/luxtts) running locally (default port 8020)
- A GitHub token (optional, but recommended to avoid rate limits)

## Setup

```bash
cd segment_bot
pip install -r requirements.txt

# Optional: set GitHub token for higher API limits
set GITHUB_TOKEN=your_token_here   # Windows
export GITHUB_TOKEN=your_token_here  # Mac/Linux

# Pull a model into Ollama first
ollama pull llama3

python app.py
```

Then open `http://localhost:5000`

## config.py

Edit `config.py` to change:
- `OLLAMA_MODEL` — which local model to use
- `LUXTTS_BASE_URL` — if LuxTTS runs on a different port
- `SCHEDULE_HOUR` / `SCHEDULE_MINUTE` — when the daily run fires

## What it does

| Module | What happens |
|---|---|
| **News** | Fetches active RSS feeds → compiles a spoken script in Rex's voice → generates audio via LuxTTS |
| **GitHub** | Pulls repo data from GitHub API → diffs against last snapshot in SQLite → writes a plain-English status update |
| **Education** | Reads project context from memory → generates a focused technical lesson → optional audio |

Daily run fires automatically at 07:00. You can also trigger any module manually from the dashboard.
