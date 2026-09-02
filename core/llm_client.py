"""Gemini client for JARVIS. Secrets are loaded from the environment or local api_key.txt."""
from __future__ import annotations
import os, re
from pathlib import Path

_DEFAULT_MODEL="gemini-2.5-flash"
_FALLBACK_MODELS=["gemini-2.0-flash","gemini-1.5-flash"]
_KEY_FILE=Path(__file__).resolve().parent.parent/"api_key.txt"
_ACTIVE_KEY=os.getenv("GEMINI_API_KEY","").strip()
if not _ACTIVE_KEY and _KEY_FILE.exists():
    try: _ACTIVE_KEY=_KEY_FILE.read_text(encoding="utf-8").strip()
    except Exception: pass

def get_api_key(): return _ACTIVE_KEY

def set_api_key(key: str):
    global _ACTIVE_KEY
    _ACTIVE_KEY=key.strip() if key else ""
    if _ACTIVE_KEY:
        try: _KEY_FILE.write_text(_ACTIVE_KEY,encoding="utf-8")
        except Exception: pass
    else:
        try:_KEY_FILE.unlink(missing_ok=True)
        except Exception:pass
    return bool(_ACTIVE_KEY)

def get_model(): return _DEFAULT_MODEL

def _make_client():
    from google import genai
    if not _ACTIVE_KEY: raise RuntimeError("GEMINI_API_KEY is not configured. Add it locally or set the GEMINI_API_KEY environment variable.")
    return genai.Client(api_key=_ACTIVE_KEY)

def _friendly_error(e):
    s=str(e)
    if "429" in s or "RESOURCE_EXHAUSTED" in s: return "Gemini quota exceeded. Try again later or configure your own API key."
    if "401" in s or "403" in s or "PERMISSION" in s: return "API key invalid or unavailable. Configure a valid GEMINI_API_KEY locally."
    if "connection" in s.lower() or "timeout" in s.lower(): return "Network error. Check your internet connection."
    return f"Gemini error: {s[:200]}"

def check_connection(log_fn=None):
    if not _ACTIVE_KEY: return False,"No Gemini API key configured."
    for model in [_DEFAULT_MODEL]+_FALLBACK_MODELS:
        try:
            r=_make_client().models.generate_content(model=model,contents="ping")
            if getattr(r,"text",None):
                if log_fn: log_fn(f"Model '{model}' is online.")
                return True,model
        except Exception as e:
            if log_fn: log_fn(f"Model '{model}' failed: {str(e)[:100]}")
    return False,"All models failed."

def call_stream(messages,system_prompt="",timeout=120):
    try:
        from google.genai import types
    except ImportError:
        yield {"type":"error","text":"google-genai package not installed."}; return
    contents=[]
    for msg in messages:
        role="model" if msg.get("role")=="assistant" else "user"
        contents.append(types.Content(role=role,parts=[types.Part.from_text(text=msg.get("content", ""))]))
    if not contents: yield {"type":"error","text":"No messages to send."}; return
    kwargs={"system_instruction":system_prompt} if system_prompt else {}
    try: kwargs["thinking_config"]=types.ThinkingConfig(thinking_budget=0)
    except Exception: pass
    config=types.GenerateContentConfig(**kwargs)
    try:
        response=_make_client().models.generate_content_stream(model=_DEFAULT_MODEL,contents=contents,config=config)
        full=""
        for chunk in response:
            text=getattr(chunk,"text","") or ""
            if text:
                full+=text; yield {"type":"chunk","text":text}
        yield {"type":"done","content":full}
    except Exception as e:
        yield {"type":"error","text":_friendly_error(e)}
