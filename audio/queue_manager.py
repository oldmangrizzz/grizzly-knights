"""
Queue manager — pre-generates scenes ahead of playback for seamless audio.
Worker thread: generate script → TTS → enqueue chunks
Main thread:   dequeue chunks → play sequentially via afplay (macOS)

No pygame, no pydub — works with Python 3.13+ on macOS.
"""

import io
import queue
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from engine.script_generator import Script
from audio.mixer import Mixer, AudioChunk


@dataclass
class QueuedScene:
    script: Script
    chunks: list[AudioChunk]
    label:  str


GenerateFn = Callable[[int], tuple[Script, str]]


class QueueManager:

    def __init__(self,
                 mixer:        Mixer,
                 generate_fn:  GenerateFn,
                 buffer_size:  int = 2):
        self.mixer        = mixer
        self.generate_fn  = generate_fn
        self.buffer_size  = buffer_size

        self._queue:       queue.Queue[Optional[QueuedScene]] = queue.Queue(maxsize=buffer_size + 1)
        self._stop_event:  threading.Event = threading.Event()
        self._worker:      Optional[threading.Thread] = None
        self._scene_index  = 0

    def start(self):
        self._stop_event.clear()
        self._worker = threading.Thread(target=self._generate_loop, daemon=True)
        self._worker.start()

    def stop(self):
        self._stop_event.set()
        self._queue.put(None)
        if self._worker:
            self._worker.join(timeout=5)

    def _generate_loop(self):
        while not self._stop_event.is_set():
            if self._queue.full():
                time.sleep(0.5)
                continue
            try:
                idx = self._scene_index
                self._scene_index += 1
                script, _ = self.generate_fn(idx)
                chunks    = self.mixer.mix_scene(script)
                label     = (
                    f"Episode {script.episode_number} · "
                    f"Act {script.act} · Scene {script.scene_number}"
                )
                self._queue.put(QueuedScene(script=script, chunks=chunks, label=label))
            except Exception as e:
                print(f"\n[Generator error: {e}]")
                time.sleep(2)

    def play_loop(self, on_scene_start: Optional[Callable[[QueuedScene], None]] = None):
        """Blocking playback loop — dequeues scenes and plays chunks via afplay."""
        while True:
            item = self._queue.get()
            if item is None:
                break
            if on_scene_start:
                on_scene_start(item)
            self._play_scene(item)

    def _play_scene(self, scene: QueuedScene):
        for chunk in scene.chunks:
            if self._stop_event.is_set():
                return
            try:
                _afplay(chunk.mp3_bytes)
            except Exception as e:
                print(f"[Playback error: {e}]")
            if chunk.gap_after > 0 and not self._stop_event.is_set():
                time.sleep(chunk.gap_after / 1000.0)


def _afplay(mp3_bytes: bytes):
    """Write MP3 bytes to a temp file and play via macOS afplay, blocking until done."""
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(mp3_bytes)
        tmp_path = f.name
    try:
        subprocess.run(["afplay", tmp_path], check=True, capture_output=True)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
