"""JARVIS second-AI bridge UI.

Provides a separate window for FRIDAY/ChatGPT, an OpenAI API-key field,
continuous cooperation mode, and explicit stop control.
"""
from __future__ import annotations
import os, threading, webbrowser
from typing import Optional
from PyQt6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QPlainTextEdit,QComboBox
from PyQt6.QtCore import pyqtSignal, QObject

from core.ai_dialogue import ContinuousAIDialogue, DialogueConfig, DialogueMessage


class _Signals(QObject):
    message=pyqtSignal(str,str)
    status=pyqtSignal(str)


class AIBridgeWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("JARVIS — AI Cooperation Center")
        self.resize(760,620)
        self.signals=_Signals()
        self.signals.message.connect(self._show_message)
        self.signals.status.connect(self._show_status)
        self.dialogue: Optional[ContinuousAIDialogue]=None
        self._build()

    def _build(self):
        layout=QVBoxLayout(self)
        title=QLabel("JARVIS ↔ OTHER AI")
        title.setStyleSheet("font-size:20px;font-weight:700;padding:8px;")
        layout.addWidget(title)

        row=QHBoxLayout()
        row.addWidget(QLabel("Other AI:"))
        self.name=QComboBox()
        self.name.addItems(["FRIDAY","ChatGPT"])
        row.addWidget(self.name)
        row.addWidget(QLabel("OpenAI model:"))
        self.model=QLineEdit("gpt-5-mini")
        row.addWidget(self.model)
        layout.addLayout(row)

        keyrow=QHBoxLayout()
        keyrow.addWidget(QLabel("OpenAI API key:"))
        self.key=QLineEdit()
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText("Paste your OpenAI API key here")
        keyrow.addWidget(self.key,1)
        self.open_button=QPushButton("Open ChatGPT in Chrome")
        self.open_button.clicked.connect(lambda: webbrowser.open("https://chatgpt.com/"))
        keyrow.addWidget(self.open_button)
        layout.addLayout(keyrow)

        promptrow=QHBoxLayout()
        promptrow.addWidget(QLabel("Opening message:"))
        self.prompt=QLineEdit("JARVIS wants to cooperate on a project.")
        promptrow.addWidget(self.prompt,1)
        layout.addLayout(promptrow)

        controls=QHBoxLayout()
        self.start=QPushButton("Start Cooperation")
        self.stop=QPushButton("STOP")
        self.stop.setEnabled(False)
        self.start.clicked.connect(self.start_dialogue)
        self.stop.clicked.connect(self.stop_dialogue)
        controls.addWidget(self.start)
        controls.addWidget(self.stop)
        layout.addLayout(controls)

        self.output=QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output,1)
        self.status=QLabel("Ready")
        layout.addWidget(self.status)

    def start_dialogue(self):
        if self.dialogue and self.dialogue.running:
            return
        key=self.key.text().strip() or os.getenv("OPENAI_API_KEY","").strip()
        if not key:
            self._show_status("Paste an OpenAI API key first.")
            return
        other=self.name.currentText()
        self.dialogue=ContinuousAIDialogue(
            DialogueConfig(
                other_name=other,
                openai_model=self.model.text().strip() or "gpt-5-mini",
                openai_api_key=key,
                max_turns=1000,
                pause_seconds=0.6,
            ),
            on_message=lambda m:self.signals.message.emit(m.speaker,m.text),
            on_status=lambda s:self.signals.status.emit(s),
        )
        self.start.setEnabled(False)
        self.stop.setEnabled(True)
        self.dialogue.start(self.prompt.text().strip() or "Let's cooperate.")

    def stop_dialogue(self):
        if self.dialogue:
            self.dialogue.stop()
        self.start.setEnabled(True)
        self.stop.setEnabled(False)

    def _show_message(self,speaker,text):
        self.output.appendPlainText(f"{speaker}: {text}\n")

    def _show_status(self,text):
        self.status.setText(text)
        if "stopped" in text.lower() or "reached" in text.lower():
            self.start.setEnabled(True)
            self.stop.setEnabled(False)

    def closeEvent(self,event):
        self.stop_dialogue()
        super().closeEvent(event)


__all__=["AIBridgeWindow"]
