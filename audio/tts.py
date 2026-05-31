"""
TTS engine — XTTS v2 via parallel persistent subprocesses in .venv_tts (Python 3.11).

Voice assignment per character:
  - If universe/voice_refs/<character_key>.wav exists → zero-shot voice cloning
  - Otherwise → built-in XTTS speaker mapped in config.yaml under xtts.voices

A pool of N worker processes (audio/xtts_worker.py) are started on first use and
kept alive for the session. Synthesis calls are dispatched concurrently across the
pool — each caller grabs a free worker, synthesizes, returns the worker.

Set N via TTSEngine(n_workers=4). Each worker loads a full XTTS model (~1.8 GB RAM).
"""

import io
import json
import queue
import struct
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Optional

ROOT           = Path(__file__).parent.parent
VOICE_REFS_DIR = ROOT / "universe" / "voice_refs"
WORKER_SCRIPT  = Path(__file__).parent / "xtts_worker.py"
VENV_PYTHON    = ROOT / ".venv_tts" / "bin" / "python"

DEFAULT_SPEAKER = "Damien Black"


class TTSEngine:

    def __init__(self, api_key: str = "", voice_map: dict = None, n_workers: int = 4):
        self._voice_map = voice_map or {}
        self._n_workers = n_workers
        self._pool: queue.Queue = queue.Queue()
        self._workers: list = []
        self._started = False
        self._lock = threading.Lock()
        VOICE_REFS_DIR.mkdir(parents=True, exist_ok=True)

    # ── Worker pool lifecycle ──────────────────────────────────────────────────

    def _start_workers(self):
        for i in range(self._n_workers):
            proc = subprocess.Popen(
                [str(VENV_PYTHON), str(WORKER_SCRIPT)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            ready = proc.stdout.readline()
            if not ready.startswith(b"READY"):
                raise RuntimeError(f"XTTS worker {i} failed to start: {ready!r}")
            self._pool.put(proc)
            self._workers.append(proc)

    def _ensure_started(self):
        with self._lock:
            if not self._started:
                self._start_workers()
                self._started = True

    def shutdown(self):
        while not self._pool.empty():
            try:
                proc = self._pool.get_nowait()
                try:
                    proc.stdin.write(struct.pack(">I", 0))
                    proc.stdin.flush()
                except Exception:
                    pass
                proc.wait(timeout=5)
            except queue.Empty:
                break

    # ── Protocol helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _send_request(proc, req: dict) -> bytes:
        payload = json.dumps(req).encode("utf-8")
        proc.stdin.write(struct.pack(">I", len(payload)))
        proc.stdin.write(payload)
        proc.stdin.flush()

        raw_len = proc.stdout.read(4)
        if len(raw_len) < 4:
            raise RuntimeError("Worker closed unexpectedly")
        wav_len = struct.unpack(">I", raw_len)[0]

        if wav_len == 0:
            err_len = struct.unpack(">I", proc.stdout.read(4))[0]
            err_msg = proc.stdout.read(err_len).decode("utf-8", errors="replace")
            raise RuntimeError(f"XTTS worker error: {err_msg}")

        return proc.stdout.read(wav_len)

    # ── Public API ─────────────────────────────────────────────────────────────

    def synthesize(self, text: str, voice_key: str = "narrator") -> bytes:
        """Thread-safe. Grabs a free worker, synthesizes, returns worker to pool."""
        self._ensure_started()

        ref_path = VOICE_REFS_DIR / f"{voice_key}.wav"
        speaker  = self._voice_map.get(voice_key) or DEFAULT_SPEAKER
        req = {
            "text":    text,
            "speaker": speaker,
            "ref_wav": str(ref_path) if ref_path.exists() else None,
        }

        proc = self._pool.get()
        try:
            wav_data = self._send_request(proc, req)
            return _wav_to_mp3(wav_data)
        finally:
            self._pool.put(proc)

    def synthesize_with_direction(self, text: str, voice_key: str,
                                  direction: Optional[str] = None) -> bytes:
        return self.synthesize(text, voice_key)


# ── Audio conversion ───────────────────────────────────────────────────────────

def _wav_to_mp3(wav_data: bytes) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(wav_data)
        wav_path = Path(f.name)
    mp3_path = wav_path.with_suffix(".mp3")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav_path), "-q:a", "2", str(mp3_path)],
        capture_output=True, check=True,
    )
    data = mp3_path.read_bytes()
    wav_path.unlink(missing_ok=True)
    mp3_path.unlink(missing_ok=True)
    return data
