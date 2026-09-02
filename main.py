"""
J.A.R.V.I.S v3.2 — Entry Point
Multi-layer AI brain · Persistent memory · Notes · Minecraft command center
"""
from __future__ import annotations
import sys, io, threading, time
from pathlib import Path
from datetime import datetime

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False): return Path(sys.executable).parent
    return Path(__file__).resolve().parent
BASE_DIR=get_base_dir(); sys.path.insert(0,str(BASE_DIR))

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QBrush, QColor
from ui import JarvisUI
from core.tts import create_tts_player
from core.llm_client import call_stream, check_connection, get_model, set_api_key, get_api_key
from core.brain import detect_mode, extract_memory_commands, web_search, get_weather
from core.agent import build_plan, build_context, augment_system_prompt
from core.minecraft import parse_request, feature_count
from actions.executor import CommandExecutor
import memory.store as mem_store

PROMPT_PATH=BASE_DIR/"core"/"prompt.txt"
_COL_WHITE="#d8f8ff"; _COL_CYAN="#00d4ff"

class _LogRedirector:
    def __init__(self,log_widget,prefix="[SYS]"): self._log=log_widget; self._prefix=prefix; self._buf=io.StringIO(); self._lock=threading.Lock()
    def write(self,text):
        if not text: return
        with self._lock:
            self._buf.write(text)
            if "\n" in text:
                lines=self._buf.getvalue().strip().split("\n"); self._buf=io.StringIO()
                for line in lines:
                    line=line.strip()
                    if line:
                        try:self._log.append_direct(f"{self._prefix} {line}")
                        except Exception:pass
    def flush(self):
        with self._lock:
            remaining=self._buf.getvalue().strip()
            if remaining:
                self._buf=io.StringIO()
                try:self._log.append_direct(f"{self._prefix} {remaining}")
                except Exception:pass

class JarvisApp:
    def __init__(self):
        self.app=QApplication(sys.argv); self.app.setStyle("Fusion")
        try:self.system_prompt=PROMPT_PATH.read_text(encoding="utf-8")
        except Exception:self.system_prompt="You are JARVIS. Be concise, professional, direct."
        display_name="Sir"
        self.window=JarvisUI(display_name=display_name); self.window.show(); self.window.showMaximized(); self.window.raise_(); self.window.activateWindow()
        self.tts=create_tts_player()
        self.commander=CommandExecutor(tts_speak_fn=lambda text:self.tts.speak(text),log_fn=lambda text:self._log(text))
        self.history:list[dict[str,str]]=[]; self._busy=False; self._tts_queue=[]; self._tts_thread=None
        self._current_voice="en-US-GuyNeural"; self._current_rate="+0%"; self._current_mode="STANDARD"
        self._ai_response_started=False; self._accumulated_text=""; self._displayed_len=0; self._request_id=0
        self.window.send_text.connect(self._on_user_text); self.window.mic_clicked.connect(self._on_mic); self.window.stop_clicked.connect(self._on_stop)
        self.window.settings_changed.connect(self._on_settings_changed); self.window.note_saved.connect(self._on_note_saved)
        self._stderr=_LogRedirector(self.window.chat_display,"[ERR]"); self._stdout=_LogRedirector(self.window.chat_display,"[LOG]"); sys.stdout=self._stdout; sys.stderr=self._stderr
        self._setup_tray(); self._log(f"[SYS] J.A.R.V.I.S v3.2 starting — Minecraft module: {feature_count()} features")
        self._log(f"[SYS] Model: {get_model()}"); self._log("[SYS] Minecraft command center online")
        threading.Thread(target=self._check_connection,daemon=True).start(); self.history=mem_store.load_history(limit=30)

    def _setup_tray(self):
        icon_path=BASE_DIR/"assets"/"jarvis.ico"; self.tray=QSystemTrayIcon(QIcon(str(icon_path))) if icon_path.exists() else QSystemTrayIcon()
        menu=QMenu(); menu.addAction("Show JARVIS").triggered.connect(self.window.show); menu.addAction("Quit").triggered.connect(self._quit); self.tray.setContextMenu(menu); self.tray.show(); self.tray.activated.connect(self._tray_activated)
    def _tray_activated(self,reason):
        if reason==QSystemTrayIcon.ActivationReason.DoubleClick: self.window.show(); self.window.activateWindow()
    def _log(self,text):
        try:self.window.chat_display.append_direct(text)
        except Exception:pass
    def _check_connection(self):
        active=get_api_key(); key_hint=f"...{active[-4:]}" if len(active)>4 else "(not configured)"; self._log(f"[SYS] Testing connection with key {key_hint}...")
        ok,info=check_connection(log_fn=lambda m:self._log(f"[SYS] {m}")); self._log(f"[SYS] Gemini connected — {info}" if ok else f"[SYS] Connection failed: {info}"); self.window.set_state("ONLINE" if ok else "ERROR")
    def _on_user_text(self,text):
        if self._busy: self._log("[SYS] Please wait for the current response."); return
        self._process_user_input(text)
    def _on_mic(self):
        if self._busy:return
        self.window.set_mic_active(True); self.window.set_state("LISTENING"); self._log("[SYS] Listening...")
        def _listen():
            try:
                import sounddevice as sd, numpy as np, speech_recognition as sr, wave
                sample_rate=16000; audio=sd.rec(8*sample_rate,samplerate=sample_rate,channels=1,dtype="int16"); sd.wait(); audio_data=np.squeeze(audio)
                if float(np.sqrt(np.mean(audio_data.astype(np.float64)**2)))<100:self._log("[SYS] No speech detected."); return
                wav_io=io.BytesIO()
                with wave.open(wav_io,"wb") as wf: wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sample_rate); wf.writeframes(audio_data.tobytes())
                wav_io.seek(0); recognizer=sr.Recognizer()
                with sr.AudioFile(wav_io) as source: audio_data_sr=recognizer.record(source)
                text=recognizer.recognize_google(audio_data_sr)
                if text: self._log(f"You: {text}"); QTimer.singleShot(0,lambda t=text:self._process_user_input(t))
                else:self._log("[SYS] Could not understand.")
            except Exception as e:self._log(f"[SYS] Mic error: {e}")
            finally:
                try:self.window.set_mic_active(False); self.window.set_state("ONLINE" if not self._busy else "THINKING")
                except Exception:pass
        threading.Thread(target=_listen,daemon=True).start()
    def _on_stop(self): self.tts.stop(); self._tts_queue.clear(); self._request_id+=1; self._busy=False; self.window.set_state("ONLINE")
    def _on_settings_changed(self,settings):
        if "voice" in settings:self._current_voice=settings["voice"]
        if "rate" in settings:self._current_rate=settings["rate"]
        if settings.get("api_key"): set_api_key(settings["api_key"]); self._log("[SYS] New API key saved."); threading.Thread(target=self._check_connection,daemon=True).start()
    def _on_note_saved(self,title,content): self._log(f"[SYS] {mem_store.save_note(title,content)}")
    def _display_command_response(self,response):
        self.window.chat_display.add_message("JARVIS",response,is_user=False)
        threading.Thread(target=lambda:self.tts.speak(response),daemon=True).start()
    def _process_user_input(self,text):
        self._log(f"You: {text}")
        if detect_mode(text)=="MINECRAFT":
            local_result=parse_request(text)
            if local_result:
                self._current_mode="MINECRAFT"; self.window.set_mode(self._current_mode); self._display_command_response("⛏️ "+local_result); return
        executed,response=self.commander.try_execute(text)
        if executed:self._display_command_response(response); mem_store.save_history(self.history); return
        self._current_mode=detect_mode(text); self.window.set_mode(self._current_mode)
        for action,key,val in extract_memory_commands(text):
            if action=="memory":mem_store.save_memory(key,val); self._log(f"[SYS] Remembered: {key} = {val}")
            elif action=="note":mem_store.save_note(key,val)
            elif action=="recall":self._log(f"[SYS] {len(mem_store.load_notes())} notes found")
        memory_context=mem_store.get_memory_context(); plan=build_plan(text,self._current_mode); request_history=build_context(self.history,memory_context=memory_context); dynamic_prompt=augment_system_prompt(self.system_prompt,plan,memory_context)
        self._log(f"[AGENT] {plan.mode} | {len(plan.steps)}-step plan"); self._busy=True; self._request_id+=1; req_id=self._request_id
        self.history.append({"role":"user","content":text}); self.history=self.history[-30:]; self._accumulated_text=""; self._displayed_len=0; self.window.set_state("THINKING")
        def _ai_loop():
            full_response=""; timed=False
            def timeout():
                nonlocal timed; timed=True
                if req_id==self._request_id:self._log("[SYS] Response timed out."); QTimer.singleShot(0,self._on_stop)
            timer=threading.Timer(50,timeout); timer.daemon=True; timer.start()
            try:
                for event in call_stream(messages=request_history,system_prompt=dynamic_prompt):
                    if req_id!=self._request_id:return
                    if not timed and timer.is_alive():timer.cancel()
                    if event["type"]=="chunk":
                        full_response+=event["text"]; self._accumulated_text=full_response; self._tts_queue.append(event["text"]); QTimer.singleShot(0,lambda rid=req_id:self._update_ai_display(rid,False))
                    elif event["type"]=="retry":self._log(f"[SYS] {event['text']}")
                    elif event["type"]=="done":
                        full_response=event["content"]; self._accumulated_text=full_response; QTimer.singleShot(0,lambda rid=req_id:self._update_ai_display(rid,True)); self.history.append({"role":"assistant","content":full_response})
                    elif event["type"]=="error":full_response=event["text"]; self._accumulated_text=full_response; QTimer.singleShot(0,lambda rid=req_id:self._update_ai_display(rid,True)); break
            except Exception as e:self._accumulated_text=f"Unexpected error: {e}"; QTimer.singleShot(0,lambda rid=req_id:self._update_ai_display(rid,True))
            finally:
                if timer.is_alive():timer.cancel()
                if req_id==self._request_id:
                    self._busy=False; mem_store.save_history(self.history); QTimer.singleShot(0,lambda:self.window.set_state("ONLINE"))
        threading.Thread(target=_ai_loop,daemon=True).start()
    def _update_ai_display(self,req_id,final=False):
        if req_id!=self._request_id:return
        text=self._accumulated_text
        if not self._ai_response_started:
            self.window.chat_display.add_message("JARVIS",text,is_user=False); self._ai_response_started=True
        else:self.window.chat_display.update_last_message(text)
        if final:self._ai_response_started=False
    def _quit(self): self.tray.hide(); self.app.quit()

if __name__=="__main__":
    app=JarvisApp(); sys.exit(app.app.exec())
