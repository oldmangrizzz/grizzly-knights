"""
Colab GPU TTS via Playwright + our own Chromium with a persistent profile.

First run: a Chromium window opens. You sign into Google ONCE. Profile is saved.
Every run after: zero interaction. Browser launches, uploads notebook, runs it,
downloads the zip. You can keep working in your other browser the whole time.

Profile lives at: ~/.fanfic/chromium_profile
Downloads land in: <project>/episodes_raw/
"""
import base64
import json
import os
import shutil
import threading
import time
import zipfile
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


ROOT             = Path(__file__).parent.parent
VOICE_REFS_DIR   = ROOT / "universe" / "voice_refs"
DOWNLOAD_DIR     = ROOT / "episodes_raw"
PROFILE_DIR      = Path.home() / ".fanfic" / "chromium_profile"
DEBUG_DIR        = ROOT / "episodes_raw" / "_debug"


def _snap(page, label: str, verbose: bool = True):
    """Save screenshot + page HTML for debugging."""
    try:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%H%M%S")
        png = DEBUG_DIR / f"{ts}_{label}.png"
        page.screenshot(path=str(png), full_page=False)
        if verbose:
            print(f"[snap] {png.name}")
    except Exception as e:
        if verbose:
            print(f"[snap] failed: {e}")


# ── Notebook construction ─────────────────────────────────────────────────────

def build_notebook(blocks: list[dict], output_name: str) -> dict:
    voice_b64 = {
        wav.stem: base64.b64encode(wav.read_bytes()).decode()
        for wav in VOICE_REFS_DIR.glob("*.wav")
    }

    def code(src: str) -> dict:
        return {"cell_type": "code", "execution_count": None, "metadata": {},
                "outputs": [], "source": src.splitlines(keepends=True)}

    cells = [
        code("""\
# 1. Install dependencies
import subprocess, sys
subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q',
    'TTS==0.22.0', 'transformers==4.46.3'])
print('deps OK')
"""),
        code(f"""\
# 2. Decode voice refs
import base64, os
from pathlib import Path
VOICE_B64 = {json.dumps(voice_b64)}
os.makedirs('/tmp/voice_refs', exist_ok=True)
for name, b64 in VOICE_B64.items():
    Path(f'/tmp/voice_refs/{{name}}.wav').write_bytes(base64.b64decode(b64))
print(f'voice_refs decoded: {{len(VOICE_B64)}}')
"""),
        code(f"""\
# 3. Load script
import json
SCRIPT_BLOCKS = {json.dumps(blocks, ensure_ascii=False)}
spoken = [b for b in SCRIPT_BLOCKS if b['type'] in ('narrator','dialogue')]
print(f'total={{len(SCRIPT_BLOCKS)}} spoken={{len(spoken)}}')
"""),
        code("""\
# 4. Load XTTS v2 on GPU
import os, torch
os.environ['COQUI_TOS_AGREED'] = '1'
_orig = torch.load
torch.load = lambda *a, **kw: _orig(*a, **{**kw, 'weights_only': False})
from TTS.api import TTS
tts = TTS('tts_models/multilingual/multi-dataset/xtts_v2', gpu=True)
print('xtts ready, gpu=', torch.cuda.is_available())
"""),
        code("""\
# 5. Synthesize all spoken blocks
import os, time
from pathlib import Path
os.makedirs('/tmp/audio_out', exist_ok=True)
REF = Path('/tmp/voice_refs')

results = {}
start = time.time()
n_spoken = sum(1 for b in SCRIPT_BLOCKS if b['type'] in ('narrator','dialogue'))
done = 0
for i, block in enumerate(SCRIPT_BLOCKS):
    if block['type'] not in ('narrator', 'dialogue'):
        continue
    voice = block.get('voice_key') or 'narrator'
    ref = REF / f'{voice}.wav'
    out = f'/tmp/audio_out/block_{i:04d}.wav'
    try:
        if ref.exists():
            tts.tts_to_file(text=block['text'], speaker_wav=str(ref),
                            language='en', file_path=out)
        else:
            tts.tts_to_file(text=block['text'], speaker='Claribel Dervla',
                            language='en', file_path=out)
        results[i] = out
    except Exception as e:
        print(f'  ERR i={i} voice={voice}: {e}')
        results[i] = None
    done += 1
    if done % 10 == 0 or done == n_spoken:
        el = time.time() - start
        print(f'  {done}/{n_spoken}  ({el:.0f}s, {el/done:.1f}s/block)')
ok = sum(1 for v in results.values() if v)
print(f'synthesis: {ok}/{n_spoken}')
"""),
        code("""\
# 6. Encode to mp3 + write manifest
import subprocess, json
manifest = []
for i, block in enumerate(SCRIPT_BLOCKS):
    if block['type'] not in ('narrator', 'dialogue'):
        manifest.append({'index': i, 'type': block['type'], 'audio': None})
        continue
    wav = results.get(i)
    if not wav:
        manifest.append({'index': i, 'type': block['type'], 'audio': None})
        continue
    mp3 = wav.replace('.wav', '.mp3')
    subprocess.run(['ffmpeg','-y','-i',wav,'-q:a','4',mp3], capture_output=True)
    manifest.append({'index': i, 'type': block['type'], 'audio': f'block_{i:04d}.mp3'})
with open('/tmp/audio_out/manifest.json', 'w') as f:
    json.dump(manifest, f)
print(f'mp3s ready: {sum(1 for m in manifest if m["audio"])}')
"""),
        code(f"""\
# 7. Zip and trigger download
import shutil
from google.colab import files
shutil.make_archive('/tmp/{output_name}', 'zip', '/tmp/audio_out')
files.download('/tmp/{output_name}.zip')
print('download triggered')
"""),
    ]

    return {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
            "accelerator": "GPU",
            "colab": {"provenance": [], "gpuType": "T4"},
        },
        "cells": cells,
    }


# ── Browser driver ────────────────────────────────────────────────────────────

def _signed_into_google(page) -> bool:
    """True iff Colab UI shows we are signed in (no 'Sign in' button)."""
    page.goto("https://colab.research.google.com/", wait_until="domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PWTimeout:
        pass
    time.sleep(2)
    body_text = page.evaluate("document.body.innerText.slice(0, 600)")
    # Top bar contains a visible "Sign in" link when signed out
    if "\nSign in\n" in body_text or body_text.strip().endswith("Sign in"):
        return False
    if "accounts.google.com" in page.url:
        return False
    return True


def _sign_in_interactive(page):
    """Pause until user signs into Google in the open Chromium window."""
    print("\n" + "="*70)
    print("  GOOGLE SIGN-IN REQUIRED — first run only.")
    print("  A Chromium window opened. Sign into your Google account in it.")
    print("  This script is waiting. Sign in, then leave the window open.")
    print("="*70 + "\n")

    page.goto("https://accounts.google.com/", wait_until="domcontentloaded")
    # Poll until we're signed in
    for _ in range(120):  # ~20 minutes
        time.sleep(10)
        # Check sign-in by navigating back to Colab
        try:
            page.goto("https://colab.research.google.com/", wait_until="domcontentloaded", timeout=20000)
        except PWTimeout:
            continue
        url = page.url
        if "/signin" not in url and "accounts.google.com" not in url:
            print("[colab] signed in ✓")
            return
    raise RuntimeError("Google sign-in not completed in time.")


def run_on_colab(blocks: list[dict], episode_name: str,
                 timeout_sec: int = 3600,
                 headless: bool = False,
                 verbose: bool = True) -> Path | None:
    """
    Build a notebook for these blocks, drive Chromium to upload + run on Colab,
    return path to downloaded zip in DOWNLOAD_DIR.
    """
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    output_name = f"{episode_name}_audio"

    # Clear any old artifact with the same name
    expected_zip = DOWNLOAD_DIR / f"{output_name}.zip"
    if expected_zip.exists():
        expected_zip.unlink()

    # Build notebook
    nb = build_notebook(blocks, output_name)
    nb_path = DOWNLOAD_DIR / f"{episode_name}.ipynb"
    nb_path.write_text(json.dumps(nb))
    if verbose:
        print(f"[colab] notebook: {nb_path.name} ({nb_path.stat().st_size/1024/1024:.1f} MB)")

    # Download handler — saves any download to DOWNLOAD_DIR
    downloaded_path = {"value": None}
    def on_download(download):
        target = DOWNLOAD_DIR / download.suggested_filename
        try:
            download.save_as(target)
            downloaded_path["value"] = target
            if verbose:
                print(f"[colab] download saved: {target.name}")
        except Exception as e:
            if verbose:
                print(f"[colab] download save error: {e}")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=headless,
            accept_downloads=True,
            viewport={"width": 1280, "height": 900},
            args=["--no-first-run", "--no-default-browser-check"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.on("download", on_download)

        try:
            # 1. Check sign-in
            if not _signed_into_google(page):
                _sign_in_interactive(page)

            # 2. Homepage
            page.goto("https://colab.research.google.com/", wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except PWTimeout:
                pass
            time.sleep(2)

            # 3. Open dialog → Upload tab → Browse → set file via filechooser
            if verbose:
                print("[colab] Ctrl+O → Upload tab → Browse...")
            page.keyboard.press("Control+o")
            time.sleep(3)
            page.mouse.click(240, 426)  # Upload tab
            time.sleep(2)
            with page.expect_file_chooser(timeout=10000) as fc_info:
                page.mouse.click(724, 426)  # Browse label
            fc_info.value.set_files(str(nb_path.resolve()))

            # 4. Set file
            if verbose:
                print("[colab] uploading notebook...")
            page.set_input_files("input[type=file]",
                                  str(nb_path.resolve()))

            # 5. Wait for redirect to /drive/{id}
            try:
                page.wait_for_url("**/colab.research.google.com/drive/**", timeout=30000)
            except PWTimeout:
                raise RuntimeError("notebook upload did not open in Colab")
            if verbose:
                print(f"[colab] notebook opened: {page.url.split('/')[-1]}")

            # 5b. Handle "Too many sessions" dialog
            time.sleep(4)
            handled = False
            for attempt in range(3):
                try:
                    # Try regular button selector first
                    btn = page.get_by_role("button", name="Manage sessions")
                    if btn.count() > 0:
                        btn.first.click(timeout=5000)
                        handled = True
                        break
                except Exception:
                    pass
                try:
                    # Shadow DOM walker fallback
                    clicked = page.evaluate("""() => {
                        function* walk(root) {
                            const w = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
                            let n; while ((n = w.nextNode())) { yield n; if (n.shadowRoot) yield* walk(n.shadowRoot); }
                        }
                        for (const el of walk(document)) {
                            const t = (el.textContent || '').trim();
                            if (t === 'Manage sessions') {
                                const tag = el.tagName;
                                if (tag === 'BUTTON' || tag.includes('BUTTON') || tag === 'SPAN' || tag === 'DIV') {
                                    const r = el.getBoundingClientRect();
                                    if (r.width > 0 && r.height > 0) {
                                        el.click(); return {tag, x: r.x, y: r.y};
                                    }
                                }
                            }
                        }
                        return null;
                    }""")
                    if clicked:
                        handled = True
                        if verbose:
                            print(f"[colab] clicked Manage sessions via walker ({clicked['tag']})")
                        break
                except Exception:
                    pass
                time.sleep(2)
            if handled:
                time.sleep(4)
                # Terminate all listed sessions
                for _ in range(15):
                    try:
                        n = page.evaluate("""() => {
                            function* walk(root) {
                                const w = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
                                let n; while ((n = w.nextNode())) { yield n; if (n.shadowRoot) yield* walk(n.shadowRoot); }
                            }
                            let count = 0;
                            for (const el of walk(document)) {
                                const lab = el.getAttribute && el.getAttribute('aria-label');
                                if (lab === 'Terminate' || lab === 'Terminate session') {
                                    el.click(); count++;
                                }
                            }
                            return count;
                        }""")
                    except Exception:
                        n = 0
                    if not n:
                        break
                    time.sleep(1)
                    try:
                        page.evaluate("""() => {
                            function* walk(root) {
                                const w = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
                                let n; while ((n = w.nextNode())) { yield n; if (n.shadowRoot) yield* walk(n.shadowRoot); }
                            }
                            for (const el of walk(document)) {
                                const t = (el.textContent || '').trim();
                                if (t === 'Yes' || t === 'Terminate') {
                                    const r = el.getBoundingClientRect();
                                    if (r.width > 0 && r.tagName !== 'BODY') el.click();
                                }
                            }
                        }""")
                    except Exception:
                        pass
                    time.sleep(1)
                if verbose:
                    print("[colab] runtimes terminated")
                page.keyboard.press("Escape")
                time.sleep(2)

            # 6. Let cells render + kernel allocate
            time.sleep(6)

            # 6a. Dismiss "Run anyway" via shadow-DOM walker
            def _dismiss_run_anyway():
                try:
                    return page.evaluate("""() => {
                        function* walk(root) {
                            const w = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
                            let n; while ((n = w.nextNode())) { yield n; if (n.shadowRoot) yield* walk(n.shadowRoot); }
                        }
                        for (const el of walk(document)) {
                            const t = (el.textContent || '').trim();
                            if (t === 'Run anyway') {
                                const r = el.getBoundingClientRect();
                                if (r.width > 0) { el.click(); return true; }
                            }
                        }
                        return false;
                    }""")
                except Exception:
                    return False
            if _dismiss_run_anyway() and verbose:
                print("[colab] dismissed 'Run anyway'")
            time.sleep(2)

            # 7. Focus a cell, then Ctrl+F9 = Run all
            try:
                page.locator(".cell, [data-type=code], .code-cell").first.click(timeout=5000)
            except Exception:
                pass
            time.sleep(1)
            page.keyboard.press("Control+F9")
            time.sleep(3)
            # Sometimes the first Ctrl+F9 triggers ANOTHER "Run anyway" dialog
            try:
                if _dismiss_run_anyway():
                    if verbose:
                        print("[colab] dismissed second 'Run anyway'")
            except Exception:
                pass
            if verbose:
                print("[colab] Ctrl+F9 sent — kernel installing deps + synthesizing...")

            # 8. Poll for download
            if verbose:
                print(f"[colab] waiting up to {timeout_sec//60} min for {output_name}.zip ...")
            start = time.time()
            last_status = 0
            while time.time() - start < timeout_sec:
                # Check if download handler captured the file
                if downloaded_path["value"] and downloaded_path["value"].exists():
                    return downloaded_path["value"]
                # Also check filesystem (some downloads bypass handler)
                if expected_zip.exists():
                    return expected_zip

                el = int(time.time() - start)
                if el - last_status >= 60:
                    if verbose:
                        try:
                            title = page.title()
                            print(f"[colab] {el}s — {title}")
                        except Exception:
                            print(f"[colab] {el}s elapsed")
                    last_status = el
                    # Opportunistically dismiss any blocking dialog
                    try:
                        _dismiss_run_anyway()
                    except Exception:
                        pass

                time.sleep(5)

            if verbose:
                print("[colab] timed out")
            return None

        finally:
            context.close()


# ── Output extraction ─────────────────────────────────────────────────────────

def extract_zip_to_blocks(zip_path: Path) -> dict[int, bytes | None]:
    """Unzip and return {block_index: mp3_bytes or None} via the manifest."""
    extract_dir = zip_path.parent / f"{zip_path.stem}_extracted"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir()

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_dir)

    manifest_path = extract_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"[colab] WARN: manifest.json missing in {zip_path.name}")
        return {}

    manifest = json.loads(manifest_path.read_text())
    results: dict[int, bytes | None] = {}
    for entry in manifest:
        idx = entry["index"]
        audio = entry.get("audio")
        if audio:
            p = extract_dir / audio
            results[idx] = p.read_bytes() if p.exists() else None
        else:
            results[idx] = None
    return results


if __name__ == "__main__":
    # Smoke test
    test_blocks = [
        {"index": 0, "type": "narrator",
         "text": "Three days since Tony Stark last answered a phone.",
         "voice_key": "narrator"},
        {"index": 1, "type": "dialogue",
         "text": "That's not a problem. That's a system.",
         "voice_key": "tony_stark"},
    ]
    zip_path = run_on_colab(test_blocks, "smoke_test", timeout_sec=1800)
    if zip_path:
        results = extract_zip_to_blocks(zip_path)
        print(f"\nResults:")
        for idx, mp3 in results.items():
            print(f"  block {idx}: {len(mp3) if mp3 else 'FAIL'} bytes")
    else:
        print("FAILED")
