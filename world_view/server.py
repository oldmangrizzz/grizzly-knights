#!/usr/bin/env python3
"""The Watcher's Station — a live view of the world populating in real time.

Serves a dashboard that shows each character's actual portrait dropping into their district
the moment the engine finishes building them. No placeholders — the real generated art.
Run: python3 world_view/server.py  ->  open http://localhost:8770
"""
import http.server, socketserver, json, os, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8770

def load_yaml_min(fp):
    """Tiny name/alias reader — avoids a yaml dep; grabs the top-level name/alias lines."""
    name = alias = ""
    try:
        with open(fp, encoding="utf-8") as f:
            for line in f:
                if line.startswith("name:") and not name:
                    name = line.split(":", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("alias:") and not alias:
                    alias = line.split(":", 1)[1].strip().strip('"').strip("'")
                if name and alias:
                    break
    except Exception:
        pass
    return name, alias

def stem_to_district():
    geo = json.load(open(f"{ROOT}/universe/world/geography.json"))
    m = {}
    for d in geo["districts"]:
        for s in d["characters"]:
            m[s] = d["name"]
    return m, [d["name"] for d in geo["districts"]]

def world_state():
    sd, districts = stem_to_district()
    chars = []
    for fp in sorted(glob.glob(f"{ROOT}/universe/characters/*.yaml")):
        if os.path.getsize(fp) == 0:
            continue
        stem = os.path.basename(fp)[:-5]
        name, alias = load_yaml_min(fp)
        if not name:
            continue
        doss = f"{ROOT}/recovery_research/_dossiers/{stem}.md"
        words = 0
        if os.path.exists(doss):
            try: words = len(open(doss, encoding="utf-8").read().split())
            except Exception: pass
        has_port = os.path.exists(f"{ROOT}/world_art/portraits/{stem}.png")
        chars.append({
            "stem": stem, "name": (alias or name),
            "district": sd.get(stem, "The Wider City"),
            "portrait": f"/portraits/{stem}.png" if has_port else None,
            "words": words,
            "tier": "principal" if words >= 50000 else ("supporting" if words > 0 else "profile"),
        })
    if "The Wider City" not in districts:
        districts.append("The Wider City")
    civ = len(glob.glob(f"{ROOT}/universe/civilians/*.json"))
    chars.sort(key=lambda c: (-c["words"], c["name"]))
    return {"characters": chars, "civilians": civ, "districts": districts,
            "built": len(chars)}

import urllib.request as _ur
CONVEX = "http://127.0.0.1:3210"
_WID = [None]

def _cq(path, args):
    body = json.dumps({"path": path, "args": args, "format": "json"}).encode()
    req = _ur.Request(f"{CONVEX}/api/query", data=body, headers={"Content-Type": "application/json"})
    with _ur.urlopen(req, timeout=8) as r:
        return json.load(r).get("value")

def _name_to_stem():
    m = {}
    for fp in glob.glob(f"{ROOT}/universe/characters/*.yaml"):
        if os.path.getsize(fp) == 0: continue
        stem = os.path.basename(fp)[:-5]
        name, alias = load_yaml_min(fp)
        for k in (name, alias):
            if k: m[k.split(" (")[0]] = stem
    return m

def _model_map():
    try:
        ts = open(f"{ROOT}/fanfic_town/data/characters.ts", encoding="utf-8").read()
        blk = ts.split("characterModels")[1].split("};")[0]
        import re
        return dict(re.findall(r'"([^"]+)":\s*"([^"]+)"', blk))
    except Exception:
        return {}

def activity():
    try:
        if not _WID[0]:
            _WID[0] = (_cq("world:defaultWorldStatus", {}) or {}).get("worldId")
        wid = _WID[0]
        if not wid:
            return {"feed": [], "talking": 0}
        w = (_cq("world:worldState", {"worldId": wid}) or {}).get("world", {})
        models = _model_map()
        ns = _name_to_stem()
        # gather conversation ids: active ones + recent ended ones (via players' previous convo)
        conv_ids, msgs_collected = [], []
        active = [c for c in w.get("conversations", []) if (c.get("numMessages") or 0) > 0]
        for c in active:
            conv_ids.append(c["id"])
        for p in w.get("players", [])[:14]:
            pc = _cq("world:previousConversation", {"worldId": wid, "playerId": p.get("id")})
            if pc and pc.get("id") and pc["id"] not in conv_ids:
                conv_ids.append(pc["id"])
        for cid in conv_ids[:18]:
            msgs = _cq("messages:listMessages", {"worldId": wid, "conversationId": cid}) or []
            for m in msgs[-2:]:
                t = (m.get("text") or "").strip()
                if not t:
                    continue
                nm = m.get("authorName", "?")
                mdl = next((v for k, v in models.items() if k.split(" (")[0] == nm.split(" (")[0]), "?")
                msgs_collected.append({"speaker": nm, "text": t[:240], "ts": m.get("_creationTime", 0),
                                       "stem": ns.get(nm.split(" (")[0], ""),
                                       "model": mdl.replace("openrouter/", "").replace("copilot/", "")})
        msgs_collected.sort(key=lambda m: m["ts"])
        return {"feed": [{k: v for k, v in m.items() if k != "ts"} for m in msgs_collected[-14:]],
                "talking": len(active)}
    except Exception:
        return {"feed": [], "talking": 0}

VOICE_MAP = f"{ROOT}/world_view/voice_map.json"
def _el_key():
    try:
        for line in open(f"{ROOT}/.env"):
            if line.startswith("elevenlabs="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception: pass
    return ""
EL_KEY = _el_key()
_DEFV = [None]

def _default_voice():
    if _DEFV[0]: return _DEFV[0]
    try:
        req = _ur.Request("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": EL_KEY})
        with _ur.urlopen(req, timeout=15) as r:
            _DEFV[0] = json.load(r)["voices"][0]["voice_id"]
    except Exception:
        _DEFV[0] = "21m00Tcm4TlvDq8ikWAM"  # Rachel fallback
    return _DEFV[0]

def speak(stem, text):
    vm = json.load(open(VOICE_MAP)) if os.path.exists(VOICE_MAP) else {}
    vid = (vm.get(stem) or {}).get("voice_id") or _default_voice()
    body = json.dumps({"text": text[:700], "model_id": "eleven_turbo_v2_5",
                       "voice_settings": {"stability": 0.45, "similarity_boost": 0.75}}).encode()
    req = _ur.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}", data=body,
        headers={"xi-api-key": EL_KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"})
    with _ur.urlopen(req, timeout=45) as r:
        return r.read()

def positions():
    try:
        if not _WID[0]:
            _WID[0] = (_cq("world:defaultWorldStatus", {}) or {}).get("worldId")
        wid = _WID[0]
        w = (_cq("world:worldState", {"worldId": wid}) or {}).get("world", {})
        gd = _cq("world:gameDescriptions", {"worldId": wid}) or {}
        pid_name = {p["playerId"]: p["name"] for p in gd.get("playerDescriptions", [])}
        ns = _name_to_stem(); models = _model_map()
        out = []
        for p in w.get("players", []):
            pid = p.get("id"); nm = pid_name.get(pid, pid)
            pos = p.get("position", {}) or {}
            stem = ns.get(nm.split(" (")[0], "")
            port = f"/portraits/{stem}.png" if stem and os.path.exists(f"{ROOT}/world_art/portraits/{stem}.png") else None
            mdl = next((v for k, v in models.items() if k.split(" (")[0] == nm.split(" (")[0]), "")
            act = p.get("activity", {}) or {}
            out.append({"id": pid, "stem": stem, "name": nm, "x": pos.get("x", 0), "y": pos.get("y", 0),
                        "portrait": port, "model": mdl.replace("openrouter/", "").replace("copilot/", ""),
                        "activity": act.get("description", "")})
        return {"players": out, "width": w.get("width", 64), "height": w.get("height", 48)}
    except Exception:
        return {"players": [], "width": 64, "height": 48}

class H(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/api/speak":
            try:
                n = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(n) or b"{}")
                audio = speak(req.get("stem", ""), req.get("text", ""))
                self._send(200, audio, "audio/mpeg")
            except Exception as e:
                self._send(500, json.dumps({"error": str(e)[:200]}))
        else:
            self._send(404, "{}")

    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else body.encode())

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._send(200, open(f"{ROOT}/world_view/index.html", "rb").read(), "text/html")
        elif self.path == "/api/world":
            self._send(200, json.dumps(world_state()))
        elif self.path == "/api/activity":
            self._send(200, json.dumps(activity()))
        elif self.path == "/api/positions":
            self._send(200, json.dumps(positions()))
        elif self.path == "/world" or self.path == "/world3d":
            self._send(200, open(f"{ROOT}/world_view/world3d.html", "rb").read(), "text/html")
        elif self.path.startswith("/viewer"):
            self._send(200, open(f"{ROOT}/world_view/viewer.html", "rb").read(), "text/html")
        elif self.path.startswith("/assets/"):
            p = f"{ROOT}/world_view/assets/{os.path.basename(self.path)}"
            ct = "model/gltf-binary" if p.endswith(".glb") else "application/octet-stream"
            if os.path.exists(p):
                self._send(200, open(p, "rb").read(), ct)
            else:
                self._send(404, b"", ct)
        elif self.path.startswith("/portraits/"):
            stem = os.path.basename(self.path)
            p = f"{ROOT}/world_art/portraits/{stem}"
            if os.path.exists(p):
                self._send(200, open(p, "rb").read(), "image/png")
            else:
                self._send(404, b"", "image/png")
        else:
            self._send(404, "{}")

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", PORT), H) as httpd:
        print(f"Watcher's Station live -> http://localhost:{PORT}")
        httpd.serve_forever()
