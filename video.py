"""
video.py - scene registry, frame loop and ffmpeg encoding for "The Blind Quick".
Usage:
    python3 video.py list
    python3 video.py still <scene> <t> [out.png]
    python3 video.py render <scene> [<scene> ...]      -> segs/<scene>.mp4
    python3 video.py all                               -> renders every scene (2 workers) + concat
"""
import sys, os, json, math, subprocess, time
import numpy as np
from engine import *

from registry import SCENES, EVENTS, scene
SEG_DIR = "/home/claude/fq/segs"


def get_scene(name):
    for n, d, f in SCENES:
        if n == name:
            return n, d, f
    raise KeyError(name)


NO_WIPE_IN = {"01_cold_open", "02_title"}


def draw_scene(fr, name, fn, t):
    fn(fr, t)
    if name not in NO_WIPE_IN and t < 0.4:
        from common import wipe_in
        wipe_in(fr, t)


def render_frame(name, t):
    _, dur, fn = get_scene(name)
    fr = Frame()
    draw_scene(fr, name, fn, t)
    return fr


def still(name, t, out):
    from PIL import Image
    fr = render_frame(name, float(t))
    Image.fromarray(fr.array()[..., [2, 1, 0]].copy()).save(out)


VF = "vignette=angle=0.62:mode=forward,format=yuv420p"


def render_scene(name):
    n, dur, fn = get_scene(name)
    os.makedirs(SEG_DIR, exist_ok=True)
    out = os.path.join(SEG_DIR, f"{name}.mp4")
    nf = int(round(dur * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-vf", VF, "-c:v", "libx264", "-preset", "fast", "-crf", "16",
           "-pix_fmt", "yuv420p", "-threads", "1", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for i in range(nf):
        fr = Frame()
        draw_scene(fr, name, fn, i / FPS)
        p.stdin.write(fr.array().tobytes())
    p.stdin.close()
    p.wait()
    print(f"[{name}] {nf} frames in {time.time() - t0:.0f}s", flush=True)
    return out


def import_scenes():
    import scenes_a  # noqa: F401  (registers via decorator)
    import scenes_b  # noqa: F401


if __name__ == "__main__":
    import_scenes()
    cmd = sys.argv[1]
    if cmd == "list":
        tot = 0
        for n, d, _ in SCENES:
            print(f"{n:18s} {d:6.1f}s  @ {tot:6.1f}s")
            tot += d
        print("total", tot)
    elif cmd == "still":
        still(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else f"/tmp/claude-0/{sys.argv[2]}_{sys.argv[3]}.png")
    elif cmd == "render":
        for n in sys.argv[2:]:
            render_scene(n)
