#!/usr/bin/env python3
"""
Build FULL intelligence dossiers for the entire roster through the UATU engine.

For each character: independent evidence-first assessment -> 12 parallel dossier modules ->
assembled dossier (recovery_research/_dossiers/<stem>.md) + structured IC profile YAML
(for the sim runtime). Authorial constraints (_directives/<stem>.md) are applied where they
exist; the psychology is DERIVED. Expectations (_expectations/) are NEVER fed.

Characters run sequentially (modules parallelize within each) to stay under rate limits.
Resumable: pass --skip-existing to skip characters whose dossier already exists.

Run:  python3 scripts/build_all_dossiers.py [--only stemA,stemB] [--skip-existing]
"""
import sys, pathlib, yaml

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
CHARS = HERE / "universe" / "characters"
DOSS = HERE / "recovery_research" / "_dossiers"; DOSS.mkdir(parents=True, exist_ok=True)
EO = HERE / "recovery_research" / "_engine_out"; EO.mkdir(parents=True, exist_ok=True)
PRIOR = HERE / "recovery_research" / "_prior"; PRIOR.mkdir(parents=True, exist_ok=True)

from engine.uatu_compiler import compile_dossier, compile_profile


def display_alias(stem):
    yp = CHARS / f"{stem}.yaml"
    disp, al = stem.replace("_", " ").title(), ""
    if yp.exists() and yp.stat().st_size > 0:
        try:
            d = yaml.safe_load(yp.read_text(encoding="utf-8")) or {}
            disp = (d.get("name") or disp); al = (d.get("alias") or "")
        except Exception:
            pass
    return disp, al


def read_aux(stem):
    directives = ""
    dp = CHARS / "_directives" / f"{stem}.md"
    if dp.exists():
        directives = dp.read_text(encoding="utf-8")
    sources = ""
    sp = HERE / "recovery_research" / "_sources" / f"{stem}.txt"
    if sp.exists():
        sources = sp.read_text(encoding="utf-8")
    return directives, sources


def main():
    only = None
    skip_existing = "--skip-existing" in sys.argv
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))

    stems = [p.stem for p in sorted(CHARS.glob("*.yaml"))]
    if only:
        stems = [s for s in stems if s in only]

    log = lambda m: sys.stderr.write(m + "\n") or sys.stderr.flush()
    for i, stem in enumerate(stems, 1):
        if skip_existing and (DOSS / f"{stem}.md").exists():
            log(f">>> SKIP {stem} (dossier exists)"); continue
        disp, al = display_alias(stem)
        directives, sources = read_aux(stem)
        tag = " +directives" if directives else " (cold)"
        log(f">>> START {stem} [{i}/{len(stems)}] {disp}{tag}")
        try:
            dossier_md, analysis = compile_dossier(stem, disp, al, sources=sources,
                                                   directives=directives, log=log)
        except Exception as e:
            log(f">>> FAIL {stem}: {e}"); continue
        (DOSS / f"{stem}.md").write_text(dossier_md, encoding="utf-8")
        (EO / f"{stem}.analysis.md").write_text(analysis, encoding="utf-8")
        # structured profile for the runtime (reuse the shared assessment)
        try:
            # synthesis occasionally emits a profile with a single schema miss; it is
            # intermittent, so retry a few times until validation passes before giving up.
            y = rep = d = None
            for _try in range(1, 4):
                y, rep, d, _ = compile_profile(stem, disp, al, sources=sources,
                                               directives=directives, analysis=analysis)
                if rep.ok:
                    break
                log(f"    profile validation miss for {stem} ({rep.line().strip()}); retry {_try}/3")
            out = CHARS / f"{stem}.yaml"
            if rep.ok:
                if out.exists() and out.stat().st_size > 0:
                    (PRIOR / f"{stem}.yaml").write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
                out.write_text(y if y.endswith("\n") else y + "\n", encoding="utf-8")
            words = len(dossier_md.split())
            # rebuild the vault per-character so a note is NEVER stale mid-batch
            import subprocess as _sp
            _sp.run([sys.executable, str(HERE / "scripts" / "build_vault.py")], check=False,
                    stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
            log(f">>> DONE {stem} ({words} words; vault note refreshed; profile {rep.line().strip()})")
        except Exception as e:
            log(f">>> profile FAIL {stem}: {e}")

    # rebuild the vault once at the end
    import subprocess
    subprocess.run([sys.executable, str(HERE / "scripts" / "build_vault.py")], check=False)
    log(">>> ALL COMPLETE")


if __name__ == "__main__":
    main()
