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

class H(http.server.SimpleHTTPRequestHandler):
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
