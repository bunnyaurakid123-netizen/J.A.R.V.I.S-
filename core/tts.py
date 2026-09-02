"""Text-to-speech using Edge TTS and sounddevice."""
import asyncio
import threading
import numpy as np
import sounddevice as sd

def _play_audio_bytes(audio_bytes: bytes):
    try: import miniaudio
    except ImportError:
        print("[TTS] miniaudio not installed."); return
    try:
        decoded=miniaudio.decode(audio_bytes,output_format=miniaudio.SampleFormat.FLOAT32,nchannels=1)
        sd.play(np.array(decoded.samples,dtype=np.float32),decoded.sample_rate); sd.wait()
    except Exception as e: print(f"[TTS] Playback error: {e}")

class EdgeTTSEngine:
    def __init__(self,voice="en-US-GuyNeural",rate="+0%",volume="+0%"): self.voice,self.rate,self.volume=voice,rate,volume
    def speak(self,text):
        if not text or not text.strip(): return
        loop=asyncio.new_event_loop()
        try: audio=loop.run_until_complete(self._synth(text))
        except Exception as e: print(f"[TTS] Synth error: {e}"); return
        finally: loop.close()
        if audio: _play_audio_bytes(audio)
    async def _synth(self,text):
        import edge_tts
        c=edge_tts.Communicate(text,self.voice,rate=self.rate,volume=self.volume)
        buf=bytearray()
        async for chunk in c.stream():
            if chunk["type"]=="audio": buf.extend(chunk["data"])
        return bytes(buf)

class TTSPlayer:
    def __init__(self,engine): self._engine=engine; self._playing=False; self._lock=threading.Lock()
    @property
    def is_playing(self): return self._playing
    def speak(self,text,on_start=None,on_done=None):
        try:
            with self._lock: self._playing=True
            if on_start:
                try:on_start()
                except Exception:pass
            self._engine.speak(text)
        finally:
            with self._lock:self._playing=False
            if on_done:
                try:on_done()
                except Exception:pass
    def stop(self):
        try:sd.stop()
        except Exception:pass
        with self._lock:self._playing=False

def create_tts_player(voice="en-US-GuyNeural"): return TTSPlayer(EdgeTTSEngine(voice=voice))
