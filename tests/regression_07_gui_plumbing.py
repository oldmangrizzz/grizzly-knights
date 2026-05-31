"""
Regression item 7 — GUI plumbing for the Next→ continuation path.

Streamlit is a UI; we don't launch it. We verify, in order:
  1. `gui` module imports without raising.
  2. The `_cook` helper accepts the `continuation_from` keyword.
  3. `_cook` calls `plan_episode` and forwards `continuation_from`
     unchanged (source-level inspection — we don't want to incur a
     full live episode run for a plumbing assert).
  4. `plan_episode` itself accepts `continuation_from` (signature check).
  5. The Next→ button branch in gui.py sets
     `st.session_state.continuation_from` and `trigger_cook = True`.
"""
from __future__ import annotations
from pathlib import Path as _ShimPath
import sys as _shim_sys
_shim_sys.path.insert(0, str(_ShimPath(__file__).parent.parent))
import sys, inspect
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    failures = []

    # 1. Import
    try:
        import gui
    except Exception as e:
        print(f"ITEM 7: FAIL — gui import: {type(e).__name__}: {e}")
        return 1

    # 2. _cook signature
    sig = inspect.signature(gui._cook)
    if "continuation_from" not in sig.parameters:
        failures.append(("_cook signature",
                        f"missing continuation_from kwarg; params={list(sig.parameters)}"))
    else:
        print(f"  PASS _cook signature has continuation_from "
              f"(default={sig.parameters['continuation_from'].default})")

    # 3. Source-level inspection: _cook forwards continuation_from to plan_episode
    src = inspect.getsource(gui._cook)
    if "continuation_from = continuation_from" not in src and \
       "continuation_from=continuation_from" not in src:
        failures.append(("_cook forwarding",
                        "_cook does not appear to pass continuation_from "
                        "through to plan_episode"))
    else:
        print("  PASS _cook forwards continuation_from to plan_episode")

    if "plan_episode(" not in src:
        failures.append(("_cook calls plan_episode", "no plan_episode( call found"))
    else:
        print("  PASS _cook calls plan_episode")

    if "run_episode_sync(" not in src:
        failures.append(("_cook calls run_episode_sync", "missing"))
    else:
        print("  PASS _cook calls run_episode_sync")

    # 4. plan_episode signature
    from engine.uatu import plan_episode
    psig = inspect.signature(plan_episode)
    if "continuation_from" not in psig.parameters:
        failures.append(("plan_episode signature",
                        f"missing continuation_from; params={list(psig.parameters)}"))
    else:
        print(f"  PASS plan_episode signature has continuation_from "
              f"(default={psig.parameters['continuation_from'].default})")

    # 5. Next→ button source-level branch
    gui_src = Path(gui.__file__).read_text()
    needed_in_gui = [
        "continuation_from",      # session_state key
        "trigger_cook",           # rerun trigger
        "Next →",                 # button label
    ]
    for s in needed_in_gui:
        if s not in gui_src:
            failures.append((f"gui.py contains {s!r}", "not found"))
        else:
            print(f"  PASS gui.py contains {s!r}")

    # 6. Behavioral smoke: instantiate the worker via direct call with
    #    a no-op queue stub — but DON'T run it (would trigger a full
    #    live episode). Just confirm callability with the kwarg.
    from queue import Queue
    log_q, result_q = Queue(), Queue()
    try:
        # Confirm the call binds without executing — wrap in a lambda
        bound = inspect.signature(gui._cook).bind(
            premise="test",
            cast=["wade_wilson"],
            ep_num=999,
            log_q=log_q,
            result_q=result_q,
            continuation_from=Path("/nonexistent/episode.txt"),
        )
        bound.apply_defaults()
        print("  PASS _cook can be bound with continuation_from kwarg")
    except Exception as e:
        failures.append(("_cook bind", f"{type(e).__name__}: {e}"))

    if failures:
        print("\nFAILURES:")
        for n, err in failures:
            print(f"  ✗ {n}: {err}")
        return 1
    print("\nITEM 7: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
