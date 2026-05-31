"""
HuggingFace Spaces TTS — XTTS-based voice cloning via gradio_client.

No browser. No Colab. Just HTTP. Synthesizes blocks in parallel, applies a
3% speed-up via ffmpeg atempo (HF clip ran slightly slow), encodes to MP3,
returns {block_index: mp3_bytes}.
"""
from __future__ import annotations

import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from gradio_client import Client, handle_file

ROOT           = Path(__file__).parent.parent
VOICE_REFS_DIR = ROOT / "universe" / "voice_refs"

SPACE_ID       = "tonyassi/voice-clone"   # XTTS-based, free
ATEMPO         = 1.03                      # 3% speed up to fix HF clip slowness
CONCURRENCY    = 4                         # HF rate limit is gentle, 4 is safe
RETRIES        = 3


def _ref_for(voice_key: str) -> Path:
    p = VOICE_REFS_DIR / f"{voice_key}.wav"
    if p.exists():
        return p
    # fallback to narrator
    return VOICE_REFS_DIR / "narrator.wav"


def _synth_one(client: Client, text: str, ref_wav: Path) -> bytes | None:
    """Call HF Space once, return raw WAV bytes."""
    for attempt in range(RETRIES):
        try:
            out_path = client.predict(
                text=text,
                audio=handle_file(str(ref_wav)),
                api_name="/clone",
            )
            return Path(out_path).read_bytes()
        except Exception as e:
            if attempt == RETRIES - 1:
                print(f"[hf] FAIL after {RETRIES} tries: {str(e)[:200]}")
                return None
            time.sleep(2 ** attempt)
    return None


def _wav_to_mp3(wav_bytes: bytes, tmp_dir: Path, idx: int) -> bytes | None:
    """Encode WAV bytes -> MP3 bytes, applying atempo speed-up."""
    wav_path = tmp_dir / f"_raw_{idx:04d}.wav"
    mp3_path = tmp_dir / f"_enc_{idx:04d}.mp3"
    wav_path.write_bytes(wav_bytes)
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(wav_path),
                "-filter:a", f"atempo={ATEMPO}",
                "-c:a", "libmp3lame", "-q:a", "4",
                str(mp3_path),
            ],
            check=True,
        )
        return mp3_path.read_bytes()
    except subprocess.CalledProcessError as e:
        print(f"[hf] ffmpeg failed for block {idx}: {e}")
        return None
    finally:
        wav_path.unlink(missing_ok=True)
        mp3_path.unlink(missing_ok=True)


def synthesize_blocks(blocks: list[dict],
                       tmp_dir: Path,
                       verbose: bool = True) -> dict[int, bytes | None]:
    """
    blocks: [{'index': int, 'type': 'narrator'|'dialogue'|...,
              'text': str, 'voice_key': str}, ...]
    Returns {block_index: mp3_bytes or None}, only for narrator/dialogue blocks.
    Non-spoken blocks are skipped.
    """
    tmp_dir.mkdir(parents=True, exist_ok=True)
    spoken = [b for b in blocks if b["type"] in ("narrator", "dialogue") and b.get("text", "").strip()]

    if verbose:
        print(f"[hf] {len(spoken)} spoken blocks → {SPACE_ID} (concurrency={CONCURRENCY})")

    client = Client(SPACE_ID)
    results: dict[int, bytes | None] = {}
    done = 0
    t0 = time.time()

    def _job(blk):
        ref = _ref_for(blk["voice_key"])
        wav = _synth_one(client, blk["text"], ref)
        if wav is None:
            return blk["index"], None
        mp3 = _wav_to_mp3(wav, tmp_dir, blk["index"])
        return blk["index"], mp3

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futures = [ex.submit(_job, b) for b in spoken]
        for fut in as_completed(futures):
            idx, mp3 = fut.result()
            results[idx] = mp3
            done += 1
            if verbose and done % 10 == 0:
                el = time.time() - t0
                rate = done / el if el > 0 else 0
                eta = (len(spoken) - done) / rate if rate > 0 else 0
                print(f"[hf] {done}/{len(spoken)} blocks  "
                      f"({rate:.2f}/s, eta {eta/60:.1f}m)")

    if verbose:
        ok = sum(1 for v in results.values() if v is not None)
        print(f"[hf] done: {ok}/{len(spoken)} ok in {(time.time()-t0)/60:.1f}m")
    return results


if __name__ == "__main__":
    import tempfile
    test_blocks = [
        {"index": 0, "type": "narrator",
         "text": "Three days since Tony Stark last answered a phone.",
         "voice_key": "narrator"},
        {"index": 1, "type": "dialogue",
         "text": "That's not a problem. That's a system.",
         "voice_key": "tony_stark"},
    ]
    with tempfile.TemporaryDirectory() as td:
        r = synthesize_blocks(test_blocks, Path(td))
        for idx, mp3 in r.items():
            print(f"  block {idx}: {len(mp3) if mp3 else 'FAIL'} bytes")
            if mp3:
                out = Path(f"/tmp/hf_block_{idx}.mp3")
                out.write_bytes(mp3)
                print(f"    -> {out}")
