"""JARVIS Gemini client with safe local key configuration and streaming retries."""
from __future__ import annotations
import os, re, time, threading
from pathlib import Path
from typing import Any, Generator

_DEFAULT_MODEL="gemini-2.5-flash"
_FALLBACK_MODELS=["gemini-2.0-flash","gemini-1.5-flash"]
_KEY_FILE=Path(__file__).resolve().parent.parent/"api_key.txt"
_ACTIVE_KEY=os.getenv("JARVIS_API_KEY","").strip()
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
        try: _KEY_FILE.unlink(missing_ok=True)
        except Exception: pass
    return bool(_ACTIVE_KEY)

def get_model(): return _DEFAULT_MODEL

def _make_client():
    from google import genai
    if not _ACTIVE_KEY: raise RuntimeError("GEMINI_API_KEY is not configured. Add it locally or set the JARVIS_API_KEY environment variable.")
    return genai.Client(api_key=_ACTIVE_KEY)

def _friendly_error(e: Exception) -> str:
    s=str(e)
    if "429" in s or "RESOURCE_EXHAUSTED" in s: return "Gemini quota exceeded. Try again later or configure your own API key."
    if "400" in s and "location" in s.lower(): return "Gemini is not available in this region/network configuration."
    if "401" in s or "403" in s or "PERMISSION" in s: return "API key invalid or unavailable. Configure a valid JARVIS_API_KEY locally."
    if "404" in s: return "The configured Gemini model was not found."
    if "connection" in s.lower() or "timeout" in s.lower(): return "Network error. Check your internet connection."
    return f"Gemini error: {s[:200]}"

def check_connection(log_fn=None):
    def log(m):
        if log_fn:
            try: log_fn(m)
            except Exception: pass
    if not _ACTIVE_KEY: return False,"API key not configured."
    for model in dict.fromkeys([_DEFAULT_MODEL]+_FALLBACK_MODELS):
        try:
            r=_make_client().models.generate_content(model=model,contents="ping")
            if getattr(r,"text",None): log(f"Model '{model}' is online."); return True,model
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e): return False,"Quota exceeded."
            log(f"Model '{model}' failed: {str(e)[:100]}")
    return False,"All configured models failed."

_CHUNK_RE=re.compile(r"(?<=[.!?]\s)|(.{30,50}?\s)")

def call_stream(messages: list[dict[str,str]], system_prompt: str="", timeout: float=120) -> Generator[dict,None,None]:
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        yield {"type":"error","text":"google-genai package is not installed."}; return
    if not _ACTIVE_KEY:
        yield {"type":"error","text":"No Gemini API key is configured. Set JARVIS_API_KEY or enter a key in Settings."}; return
    contents=[]
    for msg in messages:
        role=msg.get("role","user"); content=msg.get("content","")
        if not content: continue
        if role=="assistant": contents.append(types.Content(role="model",parts=[types.Part.from_text(text=content)]))
        elif role!="system": contents.append(types.Content(role="user",parts=[types.Part.from_text(text=content)]))
    if not contents: yield {"type":"error","text":"No messages to send."}; return
    config_kwargs: dict[str,Any]={}
    if system_prompt: config_kwargs["system_instruction"]=system_prompt
    try: config_kwargs["thinking_config"]=types.ThinkingConfig(thinking_budget=0)
    except Exception: pass
    config=types.GenerateContentConfig(**config_kwargs)
    last_error=""
    for model in dict.fromkeys([_DEFAULT_MODEL]+_FALLBACK_MODELS):
        for attempt in range(3):
            try:
                client=_make_client(); response=client.models.generate_content_stream(model=model,contents=contents,config=config)
                full=""; buffer=""; got=False
                for chunk in response:
                    text=getattr(chunk,"text","") or ""
                    if not text: continue
                    got=True; full+=text; buffer+=text
                    while True:
                        m=_CHUNK_RE.search(buffer)
                        if not m: break
                        end=m.end(); part=buffer[:end].lstrip(); buffer=buffer[end:]
                        if part: yield {"type":"chunk","text":part}
                if buffer.strip(): yield {"type":"chunk","text":buffer.strip()}
                if not got: raise RuntimeError("Empty response from Gemini")
                yield {"type":"done","content":full}; return
            except Exception as e:
                last_error=str(e); is_quota="429" in last_error or "RESOURCE_EXHAUSTED" in last_error
                if is_quota and attempt<2:
                    wait=3*(attempt+1); yield {"type":"retry","text":f"Quota hit — retrying in {wait}s..."}; time.sleep(wait); continue
                break
    yield {"type":"error","text":_friendly_error(Exception(last_error or "Unknown error"))}
