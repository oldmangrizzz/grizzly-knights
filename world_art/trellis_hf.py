#!/usr/bin/env python3
"""TRELLIS image-to-3D via the live community HF Space — reliable, free, GPU-backed.

The hosted NVIDIA NIM preview 500s on everything (even its own demo presets), and
self-hosting the NIM container needs a rented CUDA GPU. The trellis-community/TRELLIS
Space runs the real microsoft/TRELLIS-image-large on HF GPUs; our HF Pro token gives
it real quota. Pipeline: start_session -> preprocess_image -> generate_and_extract_glb.

Usage: python3 world_art/trellis_hf.py <input.png> <out_stem>
"""
import os, sys, shutil

ROOT = "/Users/rbhanson/fanfic"
SPACE = "trellis-community/TRELLIS"
OUT = f"{ROOT}/world_view/assets"


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else f"{ROOT}/world_art/_test/magneto_clean.png"
    stem = sys.argv[2] if len(sys.argv) > 2 else "erik_lehnsherr"
    from gradio_client import Client, handle_file

    c = Client(SPACE)
    print(f"connected {SPACE}; session...", flush=True)
    try:
        c.predict(api_name="/start_session")
    except Exception as e:
        print("start_session warn:", repr(e)[:120], flush=True)

    print(f"preprocess {src} ...", flush=True)
    pre = c.predict(image=handle_file(src), api_name="/preprocess_image")
    # pre is a dict with 'path' to the bg-removed prompt image
    pre_path = pre["path"] if isinstance(pre, dict) else pre
    print(f"  preprocessed -> {pre_path}", flush=True)

    print("generate + extract glb (TRELLIS on HF GPU)...", flush=True)
    res = c.predict(
        image=handle_file(pre_path),
        multiimages=[],
        seed=0,
        ss_guidance_strength=7.5,
        ss_sampling_steps=12,
        slat_guidance_strength=3.0,
        slat_sampling_steps=12,
        multiimage_algo="stochastic",
        mesh_simplify=0.95,
        texture_size=1024,
        api_name="/generate_and_extract_glb",
    )
    # res = (generated_3d_asset(video), extracted_glb(model3d), download_glb(file))
    glb = None
    for item in (res if isinstance(res, (list, tuple)) else [res]):
        p = item.get("path") if isinstance(item, dict) else item
        if isinstance(p, str) and p.endswith(".glb"):
            glb = p
    if not glb:
        print("no glb in result:", str(res)[:400], flush=True); sys.exit(1)
    os.makedirs(OUT, exist_ok=True)
    dst = f"{OUT}/{stem}.glb"
    shutil.copy(glb, dst)
    sz = os.path.getsize(dst)
    print(f"SUCCESS: {stem}.glb {sz}b  (real TRELLIS, HF GPU)", flush=True)


if __name__ == "__main__":
    main()
