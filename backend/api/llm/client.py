"""
LLM client — provider-agnostic, OpenAI-compatible (configured for Groq).

Reads config from backend/.env. Rotates across multiple API keys on rate-limit /
auth failure. The LLM produces TEXT only — it never computes WFM numbers.
"""

import os
from pathlib import Path
import httpx


def _load_env():
    """Minimal .env loader (no extra dependency)."""
    env_path = Path(__file__).resolve().parents[2] / ".env"   # backend/.env
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_env()

BASE_URL = os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_FAST = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
MODEL_CHAT = os.environ.get("GROQ_MODEL_CHAT", "llama-3.3-70b-versatile")


def _keys() -> list[str]:
    keys = []
    for i in range(1, 10):
        v = os.environ.get(f"GROQ_API_KEY_{i}")
        if v:
            keys.append(v)
    single = os.environ.get("GROQ_API_KEY") or os.environ.get("LLM_API_KEY")
    if single:
        keys.append(single)
    return keys


def available() -> bool:
    return len(_keys()) > 0


def chat(messages: list, model: str | None = None, temperature: float = 0.3,
         max_tokens: int = 900) -> str:
    """Call the chat completions API, rotating keys on failure. Returns the text."""
    keys = _keys()
    if not keys:
        raise RuntimeError("No LLM API key configured (set GROQ_API_KEY_* in backend/.env).")

    model = model or MODEL_CHAT
    url = f"{BASE_URL}/chat/completions"
    last_err = "unknown"

    for key in keys:
        try:
            r = httpx.post(
                url,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages,
                      "temperature": temperature, "max_tokens": max_tokens},
                timeout=60,
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            # rotate on rate-limit / auth issues; otherwise surface the error
            if r.status_code in (401, 403, 429):
                last_err = f"{r.status_code}: {r.text[:200]}"
                continue
            r.raise_for_status()
        except httpx.HTTPError as e:
            last_err = str(e)
            continue

    raise RuntimeError(f"All LLM keys failed. Last error: {last_err}")
