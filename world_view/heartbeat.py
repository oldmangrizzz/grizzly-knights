#!/usr/bin/env python3
"""Keep the AI Town engine awake so the characters actually LIVE.

The stock AI Town frontend heartbeats the world; our custom Watcher's Station doesn't,
so the engine drops to 'inactive' and everyone freezes in place. This pings
world:heartbeatWorld on a steady cadence — which restarts inactive worlds and refreshes
lastViewed — so agents keep pathfinding, wandering, and meeting. Run in the background.
"""
import urllib.request, json, time, sys

CONVEX = "http://127.0.0.1:3210"
INTERVAL = 20  # well under the idle cutoff


def call(kind, path, args):
    body = json.dumps({"path": path, "args": args, "format": "json"}).encode()
    req = urllib.request.Request(f"{CONVEX}/api/{kind}", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def main():
    wid = None
    beats = 0
    while True:
        try:
            if not wid:
                wid = (call("query", "world:defaultWorldStatus", {}).get("value") or {}).get("worldId")
            if wid:
                r = call("mutation", "world:heartbeatWorld", {"worldId": wid})
                beats += 1
                if beats % 15 == 1:  # occasional log
                    st = (call("query", "world:defaultWorldStatus", {}).get("value") or {}).get("status")
                    print(f"[heartbeat {beats}] world {st}", flush=True)
        except Exception as e:
            print(f"heartbeat err: {repr(e)[:120]}", flush=True)
            wid = None
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
