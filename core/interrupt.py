"""Shared interruption token used by voice, TTS and long-running tasks."""
from __future__ import annotations
import threading

class InterruptController:
    def __init__(self):
        self._event=threading.Event()
    def interrupt(self):
        self._event.set()
    def reset(self):
        self._event.clear()
    def stopped(self) -> bool:
        return self._event.is_set()
    def wait(self, timeout: float|None=None) -> bool:
        return self._event.wait(timeout)
