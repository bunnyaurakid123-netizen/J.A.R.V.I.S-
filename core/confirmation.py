"""Explicit confirmation gate for consequential local actions."""
from __future__ import annotations
from dataclasses import dataclass
import threading, time

@dataclass
class PendingAction:
    action_id: str
    description: str
    created_at: float
    expires_at: float

class ConfirmationGate:
    def __init__(self, ttl_seconds: float = 60.0):
        self.ttl_seconds=ttl_seconds
        self._pending: dict[str, PendingAction]={}
        self._lock=threading.Lock()

    def request(self, action_id: str, description: str) -> PendingAction:
        now=time.time()
        item=PendingAction(action_id,description,now,now+self.ttl_seconds)
        with self._lock:
            self._pending[action_id]=item
        return item

    def confirm(self, action_id: str) -> bool:
        with self._lock:
            item=self._pending.pop(action_id,None)
        return bool(item and item.expires_at >= time.time())

    def cancel(self, action_id: str) -> bool:
        with self._lock:
            return self._pending.pop(action_id,None) is not None

    def pending(self) -> list[PendingAction]:
        now=time.time()
        with self._lock:
            self._pending={k:v for k,v in self._pending.items() if v.expires_at >= now}
            return list(self._pending.values())
