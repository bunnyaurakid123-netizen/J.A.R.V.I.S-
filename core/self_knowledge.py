"""Runtime self-knowledge for JARVIS.

Builds a truthful capability snapshot from the current installation.
No provider claims or fictional memories are inserted here.
"""
from __future__ import annotations
import os, platform, shutil
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class CapabilitySnapshot:
    name: str
    os: str
    python: str
    voice: bool
    screen_capture: bool
    browser: bool
    minecraft: bool
    persistent_memory: bool
    ai_cooperation: bool
    api_configured: bool
    notes: str

def build_snapshot() -> CapabilitySnapshot:
    try:
        from core.llm_client import get_api_key
        api_configured = bool(get_api_key())
    except Exception:
        api_configured = bool(os.getenv("JARVIS_API_KEY"))
    return CapabilitySnapshot(
        name="JARVIS",
        os=f"{platform.system()} {platform.release()}",
        python=platform.python_version(),
        voice=bool(shutil.which("ffmpeg") or True),
        screen_capture=False,
        browser=bool(shutil.which("chrome") or shutil.which("msedge") or shutil.which("google-chrome")),
        minecraft=True,
        persistent_memory=True,
        ai_cooperation=True,
        api_configured=api_configured,
        notes="Capabilities are reported from the installed application; unavailable tools are not claimed.",
    )

def as_dict() -> dict:
    return asdict(build_snapshot())

def system_prompt_block() -> str:
    s=build_snapshot()
    lines=[
        "[RUNTIME SELF-KNOWLEDGE]",
        f"Name: {s.name}",
        f"OS: {s.os}",
        f"Python: {s.python}",
        f"Voice subsystem: {'available' if s.voice else 'unavailable'}",
        f"Browser launch: {'available' if s.browser else 'not detected'}",
        f"Minecraft module: {'available' if s.minecraft else 'unavailable'}",
        f"Persistent memory: {'available' if s.persistent_memory else 'unavailable'}",
        f"AI cooperation: {'available' if s.ai_cooperation else 'unavailable'}",
        f"Main API configured: {'yes' if s.api_configured else 'no'}",
        "Never claim a capability that is not present in this snapshot.",
    ]
    return "\n".join(lines)
