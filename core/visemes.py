"""Original transcript-driven viseme timing primitives for JARVIS."""
from __future__ import annotations
import re, unicodedata
from dataclasses import dataclass

@dataclass(frozen=True)
class Viseme:
    symbol: str
    duration_ms: int

_VOWELS={"a":"A","e":"E","i":"I","o":"O","u":"U","y":"I"}
_ROUND=set("ou")
_CLOSE=set("mbp")
_WIDE=set("ie")

def normalize_text(text: str) -> str:
    text=unicodedata.normalize("NFKD",text)
    return "".join(c.lower() for c in text if c.isalpha() or c.isspace())

def text_to_visemes(text: str, ms_per_char: int=65) -> list[Viseme]:
    out=[]
    for c in normalize_text(text):
        if c.isspace():
            out.append(Viseme("REST",max(35,ms_per_char)))
        elif c in _CLOSE:
            out.append(Viseme("CLOSE",max(35,ms_per_char)))
        elif c in _ROUND:
            out.append(Viseme("ROUND",ms_per_char))
        elif c in _WIDE:
            out.append(Viseme("WIDE",ms_per_char))
        elif c in _VOWELS:
            out.append(Viseme(_VOWELS[c],ms_per_char))
        else:
            out.append(Viseme("NEUTRAL",max(25,ms_per_char//2)))
    return out

def punctuation_pause(text: str) -> int:
    if re.search(r"[.!?]\s*$",text): return 220
    if re.search(r"[,;:]\s*$",text): return 100
    return 0
