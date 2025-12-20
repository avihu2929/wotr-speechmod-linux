import time
import os
import numpy as np
import simpleaudio as sa # NEW IMPORT
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from supertonic import TTS

# --- CONFIGURATION ---
FILE_TO_MONITOR = "/home/avihu/.local/share/bottles/bottles/3/drive_c/tmp/speech_mod_queue.txt"
TTS_MODEL_VOICE = "F3"
# The playback rate that worked best on your system
PLAYBACK_RATE = 48000
# Supertonic returns float32, which is 4 bytes per sample
BYTES_PER_SAMPLE = 4

# Global state variables
tts_engine = None
tts_style = None
# Stores the last text spoken to prevent repetition on save
last_spoken_content = ""
# NEW: Global variable to store the currently active simpleaudio PlayObject
current_play_object = None

# --- TTS AND PLAYBACK FUNCTIONS ---

def init_tts():
    """Initializes the TTS engine and voice style."""
    global tts_engine, tts_style
    print("Initializing Supertonic TTS...")
    tts_engine = TTS(auto_download=True)
    tts_style = tts_engine.get_voice_style(voice_name=TTS_MODEL_VOICE)
    print("TTS Engine Ready.")

def play_text_with_tts(text_to_speak):
    """
    Generates and plays the audio for a given text using simpleaudio.
    Stops any currently playing audio cleanly before starting new playback.
    """
    global current_play_object

    # Clean text (BOM handled in get_new_content)
    cleaned_text = text_to_speak.strip()

    if not cleaned_text:
        return

    # --- NEW SIMPLEAUDIO INTERRUPT LOGIC ---
    if current_play_object and current_play_object.is_playing():
        # Use simpleaudio's stop() on the object itself for a cleaner interrupt
        current_play_object.stop()
        print("Interrupting current playback with simpleaudio.stop()...")
    # ----------------------------------------

    print(f"\n--- NEW MESSAGE DETECTED ---")
    print(f"Reading: {cleaned_text}")

    try:
        # 1. Generate speech
        wav, duration = tts_engine.synthesize(cleaned_text, voice_style=tts_style)
    except ValueError as e:
        print(f"TTS Error: Could not synthesize text: {e}")
        return

    duration_value = duration.item()

    # 2. Convert to raw bytes for simpleaudio
    audio_data = wav.tobytes()

    # 3. Play audio non-blocking and store the PlayObject reference
    print(f"Starting playback (Duration: {duration_value:.2f}s) at {PLAYBACK_RATE} Hz...")

    current_play_object = sa.play_buffer(
        audio_data,
        num_channels=1,
        bytes_per_sample=BYTES_PER_SAMPLE,
        sample_rate=PLAYBACK_RATE
    )


# --- FILE MONITORING LOGIC (Using the overwrite logic) ---

def get_new_content(filepath):
    """
    Reads the entire file content and returns it only if it is different
    from the last content read, assuming the file is being overwritten.
    """
    global last_spoken_content

    current_content = ""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            current_content = f.read().lstrip('\ufeff')

    except Exception as e:
        return ""

    # Normalize content: collapse all whitespace into single spaces
    normalized_content = ' '.join(current_content.split()).strip()

    if normalized_content and normalized_content != last_spoken_content:
        last_spoken_content = normalized_content
        return normalized_content
    else:
        return ""


class FileChangeHandler(FileSystemEventHandler):
    """Custom handler to process file modification events."""

    def on_modified(self, event):
        """Called when a file or directory is modified."""
        if not event.is_directory and os.path.abspath(event.src_path) == os.path.abspath(FILE_TO_MONITOR):
            time.sleep(0.1)
            new_content = get_new_content(event.src_path)
            if new_content:
                play_text_with_tts(new_content)


# --- MAIN EXECUTION ---

if __name__ == "__main__":

    init_tts()

    try:
        # Ensure directory exists
        path_dir = os.path.dirname(os.path.abspath(FILE_TO_MONITOR))
        if not os.path.exists(path_dir):
            os.makedirs(path_dir, exist_ok=True)

        # Create file if it doesn't exist
        if not os.path.exists(FILE_TO_MONITOR):
            open(FILE_TO_MONITOR, 'w', encoding='utf-8').close()
            print(f"Created initial file: {FILE_TO_MONITOR}")

        # Read initial content
        get_new_content(FILE_TO_MONITOR)
        print(f"Monitoring file: '{FILE_TO_MONITOR}' (Initial content read.)")

        # Set up Watchdog Observer
        path = os.path.dirname(os.path.abspath(FILE_TO_MONITOR)) or '.'
        event_handler = FileChangeHandler()
        observer = Observer()
        observer.schedule(event_handler, path, recursive=False)
        observer.start()

        print("Monitoring started. New text will interrupt and restart the speech.")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            print("Monitoring stopped.")

        observer.join()

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Final cleanup: Stop any currently playing audio before exiting
        if current_play_object and current_play_object.is_playing():
            current_play_object.stop()
