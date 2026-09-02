"""J.A.R.V.I.S brain helpers: mode detection, memory commands and utilities."""
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
    if _RESEARCH_TRIGGERS.search(text): return "RESEARCH"
    if _GAME_TRIGGERS.search(text): return "GAMING"
    if _PROD_TRIGGERS.search(text): return "PRODUCTIVITY"
    if _CREATIVE_TRIGGERS.search(text): return "CREATIVE"
    return "STANDARD"

def extract_memory_commands(text: str):
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
        mem=psutil.virtual_memory(); disk=psutil.disk_usage("/")
        return {"cpu":psutil.cpu_percent(interval=0.1),"ram_used":mem.used//(1024**2),"ram_total":mem.total//(1024**2),"ram_pct":mem.percent,"disk_used":disk.used//(1024**3),"disk_total":disk.total//(1024**3),"disk_pct":disk.percent}
    except Exception:
        return {"cpu":0,"ram_used":0,"ram_total":0,"ram_pct":0,"disk_used":0,"disk_total":0,"disk_pct":0}

def web_search(query: str, num_results: int = 5) -> str:
    try:
        import urllib.request, urllib.parse, json
        q=urllib.parse.quote(query)
        req=urllib.request.Request(f"https://api.duckduckgo.com/?q={q}&format=json&no_html=1&skip_disambig=1",headers={"User-Agent":"JARVIS/3.0"})
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
        loc="" if city=="auto" else city
        req=urllib.request.Request(f"https://wttr.in/{urllib.parse.quote(loc)}?format=3",headers={"User-Agent":"curl/7.0"})
        with urllib.request.urlopen(req,timeout=6) as r: return r.read().decode().strip()
    except Exception as e: return f"Weather unavailable: {e}"

class TaskQueue:
    def __init__(self):
        self._tasks=[]; self._lock=threading.Lock(); self._running=True
        threading.Thread(target=self._run,daemon=True).start()
    def submit(self,fn:Callable,*args,**kwargs):
        with self._lock: self._tasks.append((fn,args,kwargs))
    def _run(self):
        while self._running:
            with self._lock: task=self._tasks.pop(0) if self._tasks else None
            if task:
                try: task[0](*task[1],**task[2])
                except Exception as e: print(f"[TASK] Error: {e}")
            else: time.sleep(.05)
    def stop(self): self._running=False

_task_queue=TaskQueue()
def submit_task(fn:Callable,*args,**kwargs): _task_queue.submit(fn,*args,**kwargs)
