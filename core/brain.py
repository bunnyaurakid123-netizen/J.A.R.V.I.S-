"""
J.A.R.V.I.S Brain — Multi-layer reasoning system.
"""
from __future__ import annotations
import re
import threading
import time
from typing import Callable

_RESEARCH_TRIGGERS = re.compile(r"\b(research|find out|deep dive|explain|what is|who is|history of|tell me about|analyse|analyze|summarize|compare|difference between)\b", re.I)
_CODE_TRIGGERS = re.compile(r"\b(code|program|script|function|class|debug|fix|error|bug|build|implement|write a|generate|refactor|optimize|algorithm|python|javascript|typescript|html|css|sql|api|bash|powershell)\b", re.I)
_GAME_TRIGGERS = re.compile(r"\b(minecraft|roblox|valorant|fortnite|cs2|krunker|gaming|game|fps|strategy|build|redstone|mod|server|skin|rank|elo)\b", re.I)
_PROD_TRIGGERS = re.compile(r"\b(plan|schedule|task|goal|todo|remind|meeting|project|deadline|organize|priority|checklist)\b", re.I)
_CREATIVE_TRIGGERS = re.compile(r"\b(write|story|poem|song|lyrics|design|imagine|create|generate|describe|fiction|essay|draft)\b", re.I)
_MEMORY_SAVE = re.compile(r"(?:remember|save|note|store)\s+(?:that\s+)?(?:my\s+)?(.+?)(?:\s+is\s+|\s*=\s*|\s*:\s*)(.+)", re.I)
_NOTE_SAVE = re.compile(r"(?:save\s+note|note down|make\s+a\s+note)\s+[\"']?(.+?)[\"']?\s*:?\s*(.+)", re.I)
_NOTE_RECALL = re.compile(r"(?:show|recall|get|list|read)\s+(?:my\s+)?notes?", re.I)


def detect_mode(text: str) -> str:
    if _CODE_TRIGGERS.search(text): return "CODING"
    if re.search(r"\b(minecraft|mc|redstone|nether|overworld|ender|elytra|villager|crafting|smelting|/fill|/tp)\b", text, re.I): return "MINECRAFT"
    if _RESEARCH_TRIGGERS.search(text): return "RESEARCH"
    if _GAME_TRIGGERS.search(text): return "GAMING"
    if _PROD_TRIGGERS.search(text): return "PRODUCTIVITY"
    if _CREATIVE_TRIGGERS.search(text): return "CREATIVE"
    return "STANDARD"


def extract_memory_commands(text: str) -> list[tuple[str, str, str]]:
    results=[]
    m=_MEMORY_SAVE.search(text)
    if m: results.append(("memory",m.group(1).strip(),m.group(2).strip()))
    m=_NOTE_SAVE.search(text)
    if m: results.append(("note",m.group(1).strip(),m.group(2).strip()))
    if _NOTE_RECALL.search(text): results.append(("recall","",""))
    return results


def get_system_stats() -> dict:
    try:
        import psutil
        cpu=psutil.cpu_percent(interval=0.1); mem=psutil.virtual_memory(); disk=psutil.disk_usage("/")
        return {"cpu":cpu,"ram_used":mem.used//(1024**2),"ram_total":mem.total//(1024**2),"ram_pct":mem.percent,"disk_used":disk.used//(1024**3),"disk_total":disk.total//(1024**3),"disk_pct":disk.percent}
    except Exception:
        return {"cpu":0,"ram_used":0,"ram_total":8192,"ram_pct":0,"disk_used":0,"disk_total":500,"disk_pct":0}


def web_search(query: str, num_results: int = 5) -> str:
    try:
        import urllib.request, urllib.parse, json
        q=urllib.parse.quote(query); url=f"https://api.duckduckgo.com/?q={q}&format=json&no_html=1&skip_disambig=1"
        req=urllib.request.Request(url,headers={"User-Agent":"JARVIS/3.2"})
        with urllib.request.urlopen(req,timeout=8) as r: data=json.loads(r.read().decode())
        parts=[]
        if data.get("AbstractText"): parts.append(f"Summary: {data['AbstractText'][:500]}")
        for topic in data.get("RelatedTopics",[])[:num_results]:
            if isinstance(topic,dict) and topic.get("Text"): parts.append(f"• {topic['Text'][:200]}")
        return "\n".join(parts) if parts else "(no results found)"
    except Exception as e: return f"(web search unavailable: {e})"


def get_weather(city: str = "auto") -> str:
    try:
        import urllib.request, urllib.parse
        url=f"https://wttr.in/{urllib.parse.quote(city if city!='auto' else '')}?format=3"
        req=urllib.request.Request(url,headers={"User-Agent":"curl/7.0"})
        with urllib.request.urlopen(req,timeout=6) as r: return r.read().decode().strip()
    except Exception as e: return f"Weather unavailable: {e}"


class TaskQueue:
    def __init__(self):
        self._tasks=[]; self._lock=threading.Lock(); self._running=True
        self._worker=threading.Thread(target=self._run,daemon=True); self._worker.start()
    def submit(self,fn:Callable,*args,**kwargs):
        with self._lock: self._tasks.append((fn,args,kwargs))
    def _run(self):
        while self._running:
            task=None
            with self._lock:
                if self._tasks: task=self._tasks.pop(0)
            if task:
                fn,args,kwargs=task
                try: fn(*args,**kwargs)
                except Exception as e: print(f"[TASK] Error: {e}")
            else: time.sleep(0.05)
    def stop(self): self._running=False

_task_queue=TaskQueue()
def submit_task(fn:Callable,*args,**kwargs): _task_queue.submit(fn,*args,**kwargs)
