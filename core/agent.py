from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class AgentPlan:
    mode: str
    goal: str
    steps: tuple[str, ...]
    needs_web: bool = False
    needs_memory: bool = True

def build_plan(text: str, mode: str) -> AgentPlan:
    t = text.strip()
    lower = t.lower()
    steps: list[str] = []
    needs_web = mode == "RESEARCH" or any(k in lower for k in ("latest", "today", "current", "news", "price"))
    if mode == "CODING":
        steps = ["understand the requested behavior", "identify the smallest safe change", "verify edge cases and compatibility"]
    elif mode == "RESEARCH":
        steps = ["identify the exact question", "separate known facts from uncertain claims", "synthesize the answer and flag freshness requirements"]
    elif mode == "PRODUCTIVITY":
        steps = ["clarify the desired outcome", "prioritize the next actions", "produce a practical sequence"]
    elif mode == "GAMING":
        steps = ["identify the game/context", "optimize for the stated objective", "give actionable steps without unnecessary filler"]
    elif mode == "CREATIVE":
        steps = ["identify the requested style", "create a coherent first draft", "polish for consistency and impact"]
    else:
        steps = ["understand intent", "answer directly", "add detail only when useful"]
    return AgentPlan(mode=mode, goal=re.sub(r"\s+", " ", t)[:500], steps=tuple(steps), needs_web=needs_web)

def build_context(history: Iterable[dict], memory_context: str = "", max_messages: int = 12, max_chars: int = 12000) -> list[dict[str, str]]:
    items = list(history)[-max_messages:]
    result: list[dict[str, str]] = []
    used = 0
    if memory_context:
        result.append({"role": "user", "content": f"[Persistent memory context]\n{memory_context[:4000]}"})
        used += len(result[-1]["content"])
    for item in items:
        content = str(item.get("content", ""))[-3500:]
        if not content or used + len(content) > max_chars:
            continue
        result.append({"role": item.get("role", "user"), "content": content})
        used += len(content)
    return result

def augment_system_prompt(base: str, plan: AgentPlan, memory_context: str = "") -> str:
    plan_text = "\n".join(f"- {s}" for s in plan.steps)
    return base.rstrip() + f"""

[ACTIVE AGENT CONTEXT]
Mode: {plan.mode}
Goal: {plan.goal}
Planning sequence:
{plan_text}

Reasoning policy:
- Do the planning internally; do not expose hidden chain-of-thought.
- Prefer concrete conclusions over generic filler.
- Distinguish facts, estimates, and assumptions.
- Never invent tool results, citations, files, or completed actions.
- If fresh information is required, say that a live lookup is needed rather than pretending.
- For coding, prioritize correctness, security, backwards compatibility, and testability.
"""
