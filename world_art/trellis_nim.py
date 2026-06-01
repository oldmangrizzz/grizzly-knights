#!/usr/bin/env python3
"""TRELLIS image-to-3D via NVIDIA NIM — the reliable, GPU-backed path.

Microsoft TRELLIS hosted as a managed NIM endpoint on NVIDIA's own CUDA infra
(not a flaky community Space). Takes a clean single-figure image, returns a GLB.

Handles: inline-base64 small images, NVCF asset-upload for big ones, sync (200)
and async (202 + NVCF status polling). Prints the API's own error feedback so we
learn the exact schema from the source if a field name is off.

Usage: python3 world_art/trellis_nim.py <input.png> <out_stem>
"""
import os, sys, json, base64, time, urllib.request, urllib.error

ROOT = "/Users/rbhanson/fanfic"
INVOKE = "https://ai.api.nvidia.com/v1/genai/microsoft/trellis"
STATUS = "https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/"
ASSETS = "https://api.nvcf.nvidia.com/v2/nvcf/assets"


def key():
    for line in open(f"{ROOT}/.env"):
        if line.strip().startswith("nvidia_key="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("nvidia_key not in .env")


KEY = key()
H = {"Authorization": f"Bearer {KEY}"}


def post(url, body, headers, timeout=300):
    data = json.dumps(body).encode()
    hd = {"Content-Type": "application/json", "Accept": "application/json", **headers}
    req = urllib.request.Request(url, data=data, headers=hd, method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, dict(r.getheaders()), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.getheaders()), e.read()


def upload_asset(path, ctype="image/png"):
    """NVCF asset upload. The presigned PUT must echo EXACTLY the registered
    content-type and description, or S3 403s and the asset lands empty."""
    desc = "trellis-input"
    st, hd, raw = post(ASSETS, {"contentType": ctype, "description": desc}, H)
    if st >= 300:
        raise SystemExit(f"asset register {st}: {raw[:200]}")
    j = json.loads(raw)
    up_url, asset_id = j["uploadUrl"], j["assetId"]
    put = urllib.request.Request(up_url, data=open(path, "rb").read(),
        headers={"Content-Type": ctype, "x-amz-meta-nvcf-asset-description": desc},
        method="PUT")
    try:
        pr = urllib.request.urlopen(put, timeout=120)
        print(f"  asset PUT {pr.status}", flush=True)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"asset PUT FAILED {e.code}: {e.read()[:300].decode('utf-8','replace')}")
    return asset_id


def poll(reqid, timeout=600):
    deadline = time.time() + timeout
    while time.time() < deadline:
        req = urllib.request.Request(STATUS + reqid, headers={**H, "Accept": "application/json"})
        try:
            r = urllib.request.urlopen(req, timeout=60)
            if r.status == 200:
                return r.read()
            time.sleep(4)
        except urllib.error.HTTPError as e:
            if e.code == 202:
                time.sleep(4); continue
            return e.read()
    raise SystemExit("poll timeout")


def save_glb(raw, out_stem):
    """Response is JSON with base64 GLB somewhere — dig it out robustly."""
    try:
        j = json.loads(raw)
    except Exception:
        # maybe raw bytes are the glb
        if raw[:4] == b"glTF":
            open(f"{ROOT}/world_view/assets/{out_stem}.glb", "wb").write(raw)
            return len(raw)
        raise
    # walk for a base64 string that decodes to glTF
    cand = []
    def walk(o):
        if isinstance(o, str) and len(o) > 100:
            cand.append(o)
        elif isinstance(o, dict):
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(j)
    for c in cand:
        try:
            b = base64.b64decode(c)
            if b[:4] == b"glTF":
                p = f"{ROOT}/world_view/assets/{out_stem}.glb"
                open(p, "wb").write(b)
                return len(b)
        except Exception:
            continue
    raise SystemExit("no GLB found in response: " + json.dumps(j)[:800])


def detect_mime(b):
    if b[:3] == b"\xff\xd8\xff": return "image/jpeg"
    if b[:4] == b"\x89PNG": return "image/png"
    return "image/png"


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else f"{ROOT}/world_art/_test/magneto_tpose.png"
    stem = sys.argv[2] if len(sys.argv) > 2 else "erik_lehnsherr_nim"
    raw_img = open(src, "rb").read()
    mime = detect_mime(raw_img)
    ext = "jpeg" if mime == "image/jpeg" else "png"
    print(f"input {src} ({len(raw_img)}b, {mime})  ->  {stem}.glb", flush=True)

    # NVIDIA image-to-3D wants an NVCF asset reference, not inline base64.
    asset_id = upload_asset(src, mime)
    print(f"uploaded asset {asset_id}", flush=True)
    # let it go fully async (no long poll-hold that can gateway-500)
    ref = {**H, "NVCF-INPUT-ASSET-REFERENCES": asset_id}

    # validated scheme: data:<mime>;example_id,<asset_id>. mode MUST be "image"
    # (defaults to text -> empty prompt -> 500). Full image-mode body:
    body = {
        "mode": "image",
        "image": f"data:{mime};example_id,{asset_id}",
        "no_texture": False,
        "output_format": "glb",
        "samples": 1,
        "seed": 0,
        "ss_cfg_scale": 7.5,
        "ss_sampling_steps": 25,
        "slat_cfg_scale": 3,
        "slat_sampling_steps": 25,
    }
    for attempt in range(1, 6):
        st, hd, out = post(INVOKE, body, ref)
        print(f"[attempt {attempt}] HTTP {st}", flush=True)
        if st == 202:
            reqid = hd.get("NVCF-REQID") or hd.get("nvcf-reqid")
            print(f"  async reqid={reqid}, polling...", flush=True)
            out = poll(reqid); st = 200
        if st == 200:
            sz = save_glb(out, stem)
            print(f"SUCCESS: {stem}.glb {sz}b on NVIDIA infra", flush=True)
            return
        print("  resp:", out[:400].decode("utf-8", "replace"), flush=True)
        print("  hdrs:", {k: v for k, v in hd.items() if k.lower().startswith("nvcf") or k.lower() in ("x-request-id",)}, flush=True)
        if st == 500:
            print("  500 (cold start / processing) — retry in 15s", flush=True)
            time.sleep(15)
        else:
            break
    print("Did not complete — see resp above.", flush=True)


if __name__ == "__main__":
    main()
