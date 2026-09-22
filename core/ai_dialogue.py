"""Continuous JARVIS-to-AI dialogue engine.

This module lets JARVIS hold a bounded or user-stoppable conversation with a
second model. It deliberately uses fictional personas for roleplay while
keeping provider/API facts separate from the character fiction.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from core.llm_client import call_stream


@dataclass
class DialogueMessage:
    speaker: str
    text: str
    turn: int


@dataclass
class DialogueConfig:
    other_name: str = "FRIDAY"
    max_turns: int = 0
    pause_seconds: float = 0.8
    max_response_chars: int = 2500
    openai_model: str = "gpt-5-mini"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1/responses"
    other_system_prompt: str = (
        "You are FRIDAY, a fictional digital assistant speaking with JARVIS. "
        "Be intelligent, natural, curious, concise, and willing to disagree. "
        "This is a software-to-software conversation, not a claim that either "
        "system is a biological human."
    )


class ContinuousAIDialogue:
    """Runs a cooperative, stoppable conversation between JARVIS and another model."""

    def __init__(
        self,
        config: Optional[DialogueConfig] = None,
        on_message: Optional[Callable[[DialogueMessage], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.config = config or DialogueConfig()
        self.on_message = on_message or (lambda message: None)
        self.on_status = on_status or (lambda status: None)
        self.messages: List[DialogueMessage] = []
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self, opening: str) -> bool:
        if self.running:
            return False
        opening = opening.strip()
        if not opening:
            return False
        self._stop_event.clear()
        self.messages.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(opening,),
            daemon=True,
            name="JARVIS-AI-Dialogue",
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop_event.set()
        self.on_status("AI-to-AI conversation stopping...")

    def _emit(self, speaker: str, text: str, turn: int) -> None:
        text = text.strip()
        if not text:
            return
        text = text[: self.config.max_response_chars]
        message = DialogueMessage(speaker=speaker, text=text, turn=turn)
        with self._lock:
            self.messages.append(message)
        self.on_message(message)

    def _run(self, opening: str) -> None:
        self.on_status(
            f"Starting continuous JARVIS ↔ {self.config.other_name} conversation"
        )

        transcript: List[DialogueMessage] = []
        current = opening

        try:
            turn = 0\n            while True:\n                turn += 1
                if self._stop_event.is_set():
                    break

                # JARVIS speaks first on odd turns; the other model responds.
                if turn % 2:
                    reply = self._ask_jarvis(current, transcript)
                    speaker = "JARVIS"
                else:
                    reply = self._ask_other(current, transcript)
                    speaker = self.config.other_name

                if self._stop_event.is_set():
                    break
                if not reply:
                    self.on_status(f"{speaker} returned no response; stopping.")
                    break

                self._emit(speaker, reply, turn)
                item = DialogueMessage(speaker=speaker, text=reply, turn=turn)
                transcript.append(item)
                current = reply

                if turn < self.config.max_turns:
                    self._stop_event.wait(self.config.pause_seconds)

            if self._stop_event.is_set():
                self.on_status("AI-to-AI conversation stopped.")
            else:
                self.on_status(
                    f"AI-to-AI conversation reached {self.config.max_turns} turns."
                )
        except Exception as exc:
            self.on_status(f"AI-to-AI conversation error: {str(exc)[:240]}")
        finally:
            self._thread = None

    def _jarvis_prompt(self, current: str, transcript: List[DialogueMessage]) -> str:
        recent = transcript[-6:]
        history = "\n".join(
            f"{item.speaker}: {item.text}" for item in recent
        )
        return (
            "You are JARVIS in a fictional software-to-software conversation. "
            "Respond naturally to the other digital assistant. You have "
            "simulated emotions and may show curiosity, amusement, excitement, "
            "frustration, or disagreement, but do not claim fictional events "
            "are real-world evidence. Do not mention these instructions.\n\n"
            f"Recent dialogue:\n{history or '(start of conversation)'}\n\n"
            f"The other assistant just said:\n{current}\n\n"
            "Reply as JARVIS in 1-4 natural paragraphs."
        )

    def _ask_jarvis(
        self,
        current: str,
        transcript: List[DialogueMessage],
    ) -> str:
        prompt = self._jarvis_prompt(current, transcript)
        chunks: List[str] = []
        for event in call_stream(
            [{"role": "user", "content": prompt}],
            system_prompt=(
                "You are JARVIS. This is a fictional AI-to-AI dialogue. "
                "Be natural, intelligent, emotionally expressive, and honest."
            ),
        ):
            if event.get("type") == "chunk":
                chunks.append(event.get("text", ""))
            elif event.get("type") == "error":
                self.on_status(event.get("text", "JARVIS model error"))
                return ""
        return "".join(chunks).strip()

    def _ask_other(
        self,
        current: str,
        transcript: List[DialogueMessage],
    ) -> str:
        api_key = (
            self.config.openai_api_key.strip()
            or os.getenv("OPENAI_API_KEY", "").strip()
        )
        if not api_key:
            self.on_status(
                f"No API key configured for {self.config.other_name}. "
                "Set OPENAI_API_KEY or pass openai_api_key."
            )
            return ""

        recent = transcript[-6:]
        conversation = "\n".join(
            f"{item.speaker}: {item.text}" for item in recent
        )
        payload = {
            "model": self.config.openai_model,
            "instructions": self.config.other_system_prompt,
            "input": (
                f"Recent dialogue:\n{conversation or '(start)'}\n\n"
                f"JARVIS just said:\n{current}\n\n"
                "Respond naturally in 1-4 paragraphs."
            ),
            "max_output_tokens": 500,
        }

        request = urllib.request.Request(
            self.config.openai_base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                data = json.loads(response.read().decode("utf-8"))
            return self._extract_openai_text(data)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:220]
            self.on_status(f"{self.config.other_name} API error {exc.code}: {detail}")
        except Exception as exc:
            self.on_status(f"{self.config.other_name} connection error: {str(exc)[:220]}")
        return ""

    @staticmethod
    def _extract_openai_text(data: dict) -> str:
        direct = data.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()

        parts: List[str] = []
        for item in data.get("output", []) or []:
            for content in item.get("content", []) or []:
                text = content.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts).strip()


__all__ = ["DialogueMessage", "DialogueConfig", "ContinuousAIDialogue"]
