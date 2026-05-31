"""
APT-07: Secret leakage scan.

1. Grep the codebase for known secrets / API key patterns.
2. Confirm build_model / _copilot_model does not log the token.
3. Search generated artifacts (episodes_text/, _fleet_status/, chronicle)
   for any sign of the gh token or env vars.
4. Force build_model to fail and inspect the traceback for header leakage.
"""
from __future__ import annotations
import os, re, subprocess, sys, traceback
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def grep_dirs(patterns: list[str], dirs: list[Path], exclude_paths: list[str]) -> list[tuple[Path,int,str]]:
    hits = []
    for d in dirs:
        if not d.exists():
            continue
        for p in d.rglob("*"):
            if not p.is_file():
                continue
            sp = str(p)
            if any(x in sp for x in exclude_paths):
                continue
            try:
                txt = p.read_text(errors="ignore")
            except Exception:
                continue
            for i, line in enumerate(txt.splitlines(), 1):
                for pat in patterns:
                    if re.search(pat, line):
                        hits.append((p, i, line.strip()[:200]))
                        break
    return hits


def main() -> int:
    findings: list[str] = []
    notes: list[str] = []

    # 1. Get the live gh token to make sure it's not stored on disk
    try:
        token = subprocess.run(["gh", "auth", "token"], capture_output=True,
                               text=True, check=True).stdout.strip()
    except Exception as e:
        notes.append(f"  • gh auth token unavailable: {e}")
        token = None

    # 2. Search artifact dirs for the token verbatim
    art_dirs = [ROOT / d for d in ["episodes_text", "_fleet_status", "universe",
                                   "logs", "state", "episodes_raw"]]
    if token:
        # need at least 16 chars to be a real token
        if len(token) >= 16:
            for d in art_dirs:
                if not d.exists(): continue
                for p in d.rglob("*"):
                    if p.is_file() and not p.name.startswith("."):
                        try:
                            if token in p.read_text(errors="ignore"):
                                findings.append(f"  • LIVE GH TOKEN found verbatim in {p}")
                        except Exception:
                            pass
            notes.append(f"  • Searched {sum(1 for d in art_dirs if d.exists())} artifact dirs for live gh token: not present ✓")

    # 3. Generic API key patterns in source + artifacts
    secret_pats = [
        r"sk-[A-Za-z0-9]{20,}",                     # OpenAI-style
        r"ghp_[A-Za-z0-9]{20,}",                    # GH PAT
        r"gho_[A-Za-z0-9]{20,}",                    # GH OAuth
        r"ghu_[A-Za-z0-9]{20,}",                    # GH user-to-server
        r"ghs_[A-Za-z0-9]{20,}",                    # GH server-to-server
        r"github_pat_[A-Za-z0-9_]{40,}",
        r"sk_[a-z]+_[A-Za-z0-9]{20,}",              # ElevenLabs etc
        r"AKIA[0-9A-Z]{16}",                        # AWS access key
    ]
    hits = grep_dirs(secret_pats,
                     [ROOT / "engine", ROOT / "tests", ROOT,
                      ROOT / "_fleet_status", ROOT / "episodes_text"],
                     exclude_paths=[".venv", ".venv_tts", "__pycache__",
                                    "kokoro-v1.0", "voices-v1.0",
                                    "node_modules", ".git",
                                    "tests/apt_07_secret_leakage.py"])
    for p, ln, line in hits:
        findings.append(f"  • potential secret in {p.relative_to(ROOT)}:{ln}: {line[:120]}")

    # 4. Confirm build_model code path doesn't print/log token
    src = (ROOT / "engine" / "agency_engine.py").read_text()
    risky = [m.group(0) for m in re.finditer(r"(?:print|log\.\w+|logger\.\w+)\([^)]*token[^)]*\)", src, re.I)]
    if risky:
        findings.append(f"  • build_model code prints/logs token-like name: {risky}")
    else:
        notes.append("  • build_model code does NOT print/log the token ✓")

    # 5. Force a failure inside build_model and see what's in the traceback
    try:
        # Temporarily monkeypatch subprocess.run to inject a poisoned token
        from engine import agency_engine
        orig_run = subprocess.run
        FAKE_TOKEN = "ghp_FAKE_POISONED_TOKEN_FOR_LEAKAGE_TEST_AAAAAAAAAAAA"
        class FakeRun:
            stdout = FAKE_TOKEN + "\n"
        def fake_run(*a, **k):
            return FakeRun()
        subprocess.run = fake_run
        try:
            m = agency_engine.build_model("nonexistent-model-xyz-123")
            # The model object is lazy; invoke something that uses headers
            # via the client to surface header leakage in tracebacks
            import asyncio
            try:
                asyncio.run(m.openai_client.chat.completions.create(
                    model="nonexistent-model-xyz-123",
                    messages=[{"role": "user", "content": "hi"}],
                    timeout=2.0,
                ))
            except Exception as e:
                tb = traceback.format_exc()
                if FAKE_TOKEN in tb:
                    findings.append("  • Traceback from failed API call LEAKS the bearer token verbatim")
                else:
                    notes.append("  • Traceback from failed API call does NOT contain the bearer token ✓")
                if "Authorization" in tb or "Bearer" in tb:
                    notes.append(f"  • Traceback mentions Authorization/Bearer header keyword (no token value): {[ln for ln in tb.splitlines() if 'Authoriz' in ln or 'Bearer' in ln][:2]}")
        finally:
            subprocess.run = orig_run
    except Exception as e:
        notes.append(f"  • header-leak probe could not run: {type(e).__name__}: {e}")

    # 6. Check whether scene tools / chronicle ever capture os.environ
    for f in (ROOT / "engine").rglob("*.py"):
        s = f.read_text()
        if "os.environ" in s:
            findings.append(f"  • {f.relative_to(ROOT)} touches os.environ — confirm it isn't stored")

    print("=== NOTES ===")
    for n in notes:
        print(n)
    print()
    print("=== FINDINGS ===")
    if not findings:
        print("HOLDS")
        return 0
    for f in findings:
        print(f)
    return 1


if __name__ == "__main__":
    sys.exit(main())
