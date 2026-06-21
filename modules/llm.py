import requests
from config import OLLAMA_BASE_URL, OLLAMA_MODEL


def generate(prompt: str, system: str = "", model: str = None) -> str:
    if model is None:
        from db import get_setting
        model = get_setting("ollama_model") or OLLAMA_MODEL
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    if system:
        payload["system"] = system

    try:
        resp = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=300)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.RequestException as e:
        return f"[LLM error: {e}]"


def list_models() -> list[str]:
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10)
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]
    except requests.RequestException:
        return []
