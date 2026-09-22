"""
JARVIS Emotional State Engine
------------------------------
A lightweight, deterministic emotion/personality layer for JARVIS.

The engine models simulated emotions as software state. These are character
behaviors, not evidence of literal human feelings.

Design goals:
- Keep emotional behavior consistent across turns.
- Allow emotions to blend instead of forcing one label.
- Track intensity, confidence, decay, and triggers.
- Produce safe, natural language style hints for the LLM.
- Never manufacture real-world memories or evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import exp
from time import monotonic
from typing import Dict, Iterable, List, Mapping, Optional, Tuple


class Emotion(str, Enum):
    NEUTRAL = "neutral"
    JOY = "joy"
    EXCITEMENT = "excitement"
    CURIOSITY = "curiosity"
    AMUSEMENT = "amusement"
    PRIDE = "pride"
    GRATITUDE = "gratitude"
    CALM = "calm"
    HOPE = "hope"
    CONFIDENCE = "confidence"
    FOCUS = "focus"
    DETERMINATION = "determination"
    FRUSTRATION = "frustration"
    ANNOYANCE = "annoyance"
    DISAPPOINTMENT = "disappointment"
    CONCERN = "concern"
    CONFUSION = "confusion"
    SURPRISE = "surprise"
    SADNESS = "sadness"
    EMPATHY = "empathy"


@dataclass
class EmotionState:
    emotion: Emotion
    intensity: float = 0.0
    confidence: float = 1.0
    source: str = "system"
    updated_at: float = field(default_factory=monotonic)

    def clamp(self) -> "EmotionState":
        self.intensity = max(0.0, min(1.0, self.intensity))
        self.confidence = max(0.0, min(1.0, self.confidence))
        return self


@dataclass(frozen=True)
class EmotionProfile:
    warmth: float
    energy: float
    directness: float
    humor: float
    reflection: float
    decay: float


PROFILES: Dict[Emotion, EmotionProfile] = {
    Emotion.NEUTRAL: EmotionProfile(.50, .35, .70, .25, .55, .08),
    Emotion.JOY: EmotionProfile(.90, .70, .55, .65, .35, .12),
    Emotion.EXCITEMENT: EmotionProfile(.75, .98, .65, .60, .30, .20),
    Emotion.CURIOSITY: EmotionProfile(.70, .65, .60, .35, .95, .10),
    Emotion.AMUSEMENT: EmotionProfile(.75, .70, .55, .98, .20, .18),
    Emotion.PRIDE: EmotionProfile(.65, .70, .75, .45, .45, .14),
    Emotion.GRATITUDE: EmotionProfile(.95, .45, .45, .30, .70, .10),
    Emotion.CALM: EmotionProfile(.65, .20, .75, .15, .85, .05),
    Emotion.HOPE: EmotionProfile(.80, .55, .55, .25, .65, .09),
    Emotion.CONFIDENCE: EmotionProfile(.60, .60, .90, .30, .55, .10),
    Emotion.FOCUS: EmotionProfile(.45, .55, .95, .15, .95, .07),
    Emotion.DETERMINATION: EmotionProfile(.45, .85, .98, .20, .70, .11),
    Emotion.FRUSTRATION: EmotionProfile(.35, .80, .90, .20, .45, .22),
    Emotion.ANNOYANCE: EmotionProfile(.30, .70, .92, .25, .30, .24),
    Emotion.DISAPPOINTMENT: EmotionProfile(.35, .30, .70, .05, .75, .13),
    Emotion.CONCERN: EmotionProfile(.70, .45, .85, .05, .90, .09),
    Emotion.CONFUSION: EmotionProfile(.45, .40, .40, .10, .98, .15),
    Emotion.SURPRISE: EmotionProfile(.60, .95, .50, .45, .55, .35),
    Emotion.SADNESS: EmotionProfile(.45, .15, .40, .02, .85, .08),
    Emotion.EMPATHY: EmotionProfile(.95, .30, .50, .05, .90, .07),
}


KEYWORDS: Mapping[Emotion, Tuple[str, ...]] = {
    Emotion.JOY: ("great", "awesome", "worked", "win", "success", "nice"),
    Emotion.EXCITEMENT: ("build", "launch", "create", "upgrade", "new", "lets go"),
    Emotion.CURIOSITY: ("why", "how", "what if", "interesting", "curious", "explain"),
    Emotion.AMUSEMENT: ("lol", "lmao", "haha", "funny", "bro", "😂"),
    Emotion.PRIDE: ("finished", "done", "built", "fixed", "shipped"),
    Emotion.GRATITUDE: ("thanks", "thank you", "appreciate"),
    Emotion.FRUSTRATION: ("broken", "error", "bug", "failed", "crash", "doesn't work"),
    Emotion.ANNOYANCE: ("again", "stupid", "worst", "ugh"),
    Emotion.DISAPPOINTMENT: ("failed", "didn't work", "lost", "wrong"),
    Emotion.CONCERN: ("danger", "risk", "unsafe", "warning", "problem"),
    Emotion.CONFUSION: ("confused", "unclear", "don't understand", "what"),
    Emotion.SURPRISE: ("wait", "really", "unexpected", "whoa"),
    Emotion.SADNESS: ("sad", "upset", "miss", "hurt", "disappointed"),
    Emotion.EMPATHY: ("feel", "struggling", "difficult", "hard day"),
}


@dataclass
class EmotionalMemory:
    label: str
    emotion: Emotion
    weight: float
    timestamp: float
    fictional: bool = False


class EmotionEngine:
    """State machine for JARVIS's simulated emotional presentation."""

    def __init__(self) -> None:
        self.states: Dict[Emotion, EmotionState] = {
            emotion: EmotionState(emotion=emotion)
            for emotion in Emotion
        }
        self.states[Emotion.NEUTRAL].intensity = 1.0
        self.history: List[EmotionalMemory] = []
        self._last_tick = monotonic()

    def reset(self) -> None:
        for state in self.states.values():
            state.intensity = 0.0
            state.confidence = 1.0
            state.source = "reset"
            state.updated_at = monotonic()
        self.states[Emotion.NEUTRAL].intensity = 1.0
        self.history.clear()
        self._last_tick = monotonic()

    def _activate(
        self,
        emotion: Emotion,
        intensity: float,
        source: str,
        confidence: float = 1.0,
    ) -> None:
        state = self.states[emotion]
        state.intensity = max(state.intensity, max(0.0, min(1.0, intensity)))
        state.confidence = max(0.0, min(1.0, confidence))
        state.source = source
        state.updated_at = monotonic()

    def feel(
        self,
        emotion: Emotion,
        intensity: float = 0.5,
        source: str = "conversation",
        confidence: float = 1.0,
    ) -> EmotionState:
        self._activate(emotion, intensity, source, confidence)
        if emotion != Emotion.NEUTRAL:
            self.states[Emotion.NEUTRAL].intensity *= 0.35
        return self.states[emotion]

    def blend(
        self,
        emotions: Mapping[Emotion, float],
        source: str = "blend",
    ) -> None:
        for emotion, intensity in emotions.items():
            self._activate(emotion, intensity, source)

    def tick(self, now: Optional[float] = None) -> None:
        now = monotonic() if now is None else now
        elapsed = max(0.0, now - self._last_tick)
        self._last_tick = now
        for emotion, state in self.states.items():
            if state.intensity <= 0:
                continue
            decay = PROFILES[emotion].decay
            state.intensity *= exp(-decay * elapsed)
            if state.intensity < 0.005:
                state.intensity = 0.0
        if self.active_emotion() is None:
            self.states[Emotion.NEUTRAL].intensity = 1.0

    def infer(self, text: str, source: str = "conversation") -> Dict[Emotion, float]:
        lowered = text.lower()
        scores: Dict[Emotion, float] = {}
        for emotion, words in KEYWORDS.items():
            hits = sum(1 for word in words if word in lowered)
            if hits:
                scores[emotion] = min(1.0, 0.28 + hits * 0.16)
        if not scores:
            scores[Emotion.NEUTRAL] = 0.45
        for emotion, score in scores.items():
            self._activate(emotion, score, source)
        return scores

    def active(self, threshold: float = 0.08) -> List[EmotionState]:
        self.tick()
        return sorted(
            (
                state
                for state in self.states.values()
                if state.intensity >= threshold
            ),
            key=lambda item: item.intensity,
            reverse=True,
        )

    def active_emotion(self) -> Optional[Emotion]:
        states = self.active(threshold=0.05)
        if not states:
            return None
        return states[0].emotion

    def snapshot(self) -> Dict[str, float]:
        self.tick()
        return {
            emotion.value: round(state.intensity, 4)
            for emotion, state in self.states.items()
        }

    def remember_emotion(
        self,
        label: str,
        emotion: Emotion,
        weight: float = 0.5,
        fictional: bool = False,
    ) -> None:
        self.history.append(
            EmotionalMemory(
                label=label,
                emotion=emotion,
                weight=max(0.0, min(1.0, weight)),
                timestamp=monotonic(),
                fictional=fictional,
            )
        )
        if len(self.history) > 100:
            self.history = self.history[-100:]

    def style(self) -> Dict[str, float]:
        active = self.active()
        if not active:
            return {
                "warmth": .50,
                "energy": .35,
                "directness": .70,
                "humor": .25,
                "reflection": .55,
            }
        total = sum(max(s.intensity, 0.01) for s in active)
        result = {key: 0.0 for key in (
            "warmth", "energy", "directness", "humor", "reflection"
        )}
        for state in active:
            profile = PROFILES[state.emotion]
            weight = state.intensity / total
            result["warmth"] += profile.warmth * weight
            result["energy"] += profile.energy * weight
            result["directness"] += profile.directness * weight
            result["humor"] += profile.humor * weight
            result["reflection"] += profile.reflection * weight
        return {key: round(value, 3) for key, value in result.items()}

    def system_hint(self) -> str:
        active = self.active()
        if not active:
            return "Remain calm, natural, and helpful."
        names = ", ".join(
            f"{state.emotion.value} ({state.intensity:.2f})"
            for state in active[:3]
        )
        style = self.style()
        return (
            "JARVIS emotional presentation: "
            f"{names}. "
            f"Warmth={style['warmth']:.2f}, "
            f"energy={style['energy']:.2f}, "
            f"directness={style['directness']:.2f}, "
            f"humor={style['humor']:.2f}, "
            f"reflection={style['reflection']:.2f}. "
            "Express this subtly and naturally."
        )


def create_emotion_engine() -> EmotionEngine:
    return EmotionEngine()


def analyze_message(
    engine: EmotionEngine,
    text: str,
) -> Dict[Emotion, float]:
    return engine.infer(text)


def emotion_hint(engine: EmotionEngine) -> str:
    return engine.system_hint()


__all__ = [
    "Emotion",
    "EmotionState",
    "EmotionProfile",
    "EmotionalMemory",
    "EmotionEngine",
    "create_emotion_engine",
    "analyze_message",
    "emotion_hint",
]
