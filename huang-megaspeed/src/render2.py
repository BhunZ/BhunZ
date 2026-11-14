"""Render v2: stills (--stills), single frames (--at t ...), or the full video (--video)."""
import argparse, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comp import Comp, ROOT, W, H
import numpy as np

STILLS = {"01_hook": 6.4, "02_megaspeed": 29.6, "03_nyt_stack": 55.2, "04_denials": 79.0, "05_admission": 85.0, "06_resignation": 127.0}


def save(arr, path):
    from PIL import Image
    os.makedirs(os.path.dirname(path), exist_ok=True); Image.fromarray(arr).save(path)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--stills", action="store_true"); ap.add_argument("--video", action="store_true")
    ap.add_argument("--at", type=float, nargs="*"); ap.add_argument("--out", default=os.path.join(ROOT, "build", "video2.mp4"))
    a = ap.parse_args()
    plan = json.load(open(os.path.join(ROOT, "build", "plan2.json")))
    C = Comp(plan)
    for t in a.at or []:
        save(C.frame(t), os.path.join(ROOT, "build", f"f2_{t:.2f}.png")); print("frame", t)
    if a.stills:
        for k, t in STILLS.items():
            save(C.frame(t), os.path.join(ROOT, "out", "v2_checkpoint", f"{k}_t{t:.1f}.png")); print("still", k, t)
    if a.video:
        n = int(round(plan["duration"] * 30))
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30", "-i", "-",
               "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-threads", "4", "-pix_fmt", "yuv420p", a.out]
        pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        rects = []
        for i in range(n):
            pr.stdin.write(C.frame(i / 30).tobytes())
            if i % 30 == 0:
                rects.append({"t": i / 30, "rects": C.layer_rects})
            if i % 600 == 0:
                print(f"frame {i}/{n}", flush=True)
        pr.stdin.close(); pr.wait()
        json.dump(rects, open(os.path.join(ROOT, "build", "layer_rects.json"), "w"))
        print("done", a.out)


if __name__ == "__main__":
    main()
