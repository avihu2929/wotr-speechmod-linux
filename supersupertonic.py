import re
import time
import os
import queue
import subprocess
import wave
import tempfile
import threading
import numpy as np
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from supertonic import TTS

FILE_TO_MONITOR = "/home/avihu/Games/gog/pathfinder-wrath-of-the-righteous/drive_c/tmp/speech_mod_queue.txt"
TTS_MODEL_VOICE = "F3"
PLAYBACK_RATE = 48000

tts_engine = None
tts_style = None
last_spoken_content = ""
current_process = None
synth_thread = None
sentence_queue = queue.Queue()
interrupt_flag = threading.Event()


def init_tts():
    global tts_engine, tts_style
    print("Initializing Supertonic TTS...")
    tts_engine = TTS(auto_download=True)
    tts_style = tts_engine.get_voice_style(voice_name=TTS_MODEL_VOICE)
    print("TTS Engine Ready.")


def split_into_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def synthesize_worker(sentences):
    for sentence in sentences:
        if interrupt_flag.is_set():
            return
        try:
            wav, _ = tts_engine.synthesize(sentence, voice_style=tts_style)
            audio_int16 = (wav.squeeze() * 32767).astype(np.int16)
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                tmp_path = tmp.name
                with wave.open(tmp_path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(PLAYBACK_RATE)
                    wf.writeframes(audio_int16.tobytes())
            
            sentence_queue.put((tmp_path, sentence))
        except Exception as e:
            print(f"Synthesis error: {e}")


def get_new_content(filepath):
    global last_spoken_content
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            current_content = f.read().lstrip('\ufeff')
    except Exception:
        return ""
    
    normalized = ' '.join(current_content.split()).strip()
    if normalized and normalized != last_spoken_content:
        last_spoken_content = normalized
        return normalized
    return ""


class FileChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.is_directory and os.path.abspath(event.src_path) == os.path.abspath(FILE_TO_MONITOR):
            time.sleep(0.1)
            new_content = get_new_content(event.src_path)
            if new_content:
                handle_new_text(new_content)


def handle_new_text(text):
    global synth_thread, current_process
    
    interrupt_flag.set()
    
    while not sentence_queue.empty():
        try:
            tmp_path, _ = sentence_queue.get_nowait()
            os.unlink(tmp_path)
        except queue.Empty:
            break
    
    if current_process and current_process.poll() is None:
        current_process.terminate()
        current_process.wait()
        print("Interrupting current playback...")
    
    interrupt_flag.clear()
    
    sentences = split_into_sentences(text)
    print(f"\n--- NEW MESSAGE DETECTED ---")
    print(f"Split into {len(sentences)} sentence(s)")
    
    synth_thread = threading.Thread(target=synthesize_worker, args=(sentences,))
    synth_thread.start()


if __name__ == "__main__":
    init_tts()
    
    try:
        path_dir = os.path.dirname(os.path.abspath(FILE_TO_MONITOR))
        if not os.path.exists(path_dir):
            os.makedirs(path_dir, exist_ok=True)
        
        if not os.path.exists(FILE_TO_MONITOR):
            open(FILE_TO_MONITOR, 'w', encoding='utf-8').close()
            print(f"Created initial file: {FILE_TO_MONITOR}")
        
        get_new_content(FILE_TO_MONITOR)
        print(f"Monitoring file: '{FILE_TO_MONITOR}'")
        
        path = os.path.dirname(os.path.abspath(FILE_TO_MONITOR)) or '.'
        event_handler = FileChangeHandler()
        observer = Observer()
        observer.schedule(event_handler, path, recursive=False)
        observer.start()
        
        print("Monitoring started. Press Ctrl+C to stop.")
        
        try:
            while True:
                try:
                    tmp_path, sentence = sentence_queue.get(timeout=0.1)
                    print(f"Playing: {sentence}")
                    current_process = subprocess.Popen(['aplay', '-q', tmp_path])
                    
                    while current_process.poll() is None:
                        if interrupt_flag.is_set():
                            current_process.terminate()
                            current_process.wait()
                            os.unlink(tmp_path)
                            break
                        time.sleep(0.05)
                    
                    if not interrupt_flag.is_set():
                        os.unlink(tmp_path)
                        
                except queue.Empty:
                    pass
                    
        except KeyboardInterrupt:
            observer.stop()
            print("Monitoring stopped.")
        
        observer.join()
        
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if current_process and current_process.poll() is None:
            current_process.terminate()
            current_process.wait()
