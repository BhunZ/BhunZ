"""Deterministic frame renderer.

  python src/render.py --stills          # 5 key stills -> out/stills/*.png
  python src/render.py --video           # full video (no audio) -> build/video.mp4
  python src/render.py --frame 12.3      # single frame -> build/frame.png
"""
import argparse, json, os, subprocess, sys
import numpy as np
import skia
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gfx import *
import visuals as V
import mapviz
import beats as BT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLORS = {"green": GREEN, "red": RED, "amber": AMBER, "muted": MUTED}
VIS = {"gpu": V.v_gpu, "doc8k": V.v_doc8k, "photo": V.v_photo, "card": V.v_card, "map": mapviz.v_map,
       "counter": V.v_counter, "denied": V.v_denied, "headline": V.v_headline, "silhouette": V.v_silhouette,
       "letter": V.v_letter, "board": V.v_board, "boardquote": V.v_boardquote, "status": V.v_status,
       "orgchart": V.v_orgchart, "alleged": V.v_alleged, "watch": V.v_watch, "end": V.v_end}
CAP_Y = 1185            # caption centre: inside the middle third (640..1280)
CAP_BASE = 100


def colorize(v):
    if isinstance(v, str) and v in COLORS:
        return COLORS[v]
    if isinstance(v, list):
        return [colorize(x) for x in v]
    if isinstance(v, dict):
        return {k: colorize(x) for k, x in v.items()}
    return v


class Renderer:
    def __init__(self):
        W_ = json.load(open(os.path.join(ROOT, "build", "words.json")))
        self.words = W_["words"]
        self.duration = W_["duration"]
        self.beats = BT.resolve(self.words, None)
        self.caps = BT.captions(self.words)
        self.surface = skia.Surface(W, H)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / np.sqrt(2)
        self.vign = (1.0 - 0.42 * np.clip(r, 0, 1) ** 2.2)[..., None]
        rng = np.random.default_rng(1234)
        self.grain = [rng.normal(0, 4.2, (H // 2, W // 2)).astype(np.float32) for _ in range(8)]
        self.grade_mul = np.array([1.035, 1.0, 0.935], np.float32)
        self.grade_add = np.array([4.0, 2.5, 0.0], np.float32)

    def beat_at(self, t):
        for b in self.beats:
            if b["start"] <= t < b["end"]:
                return b
        return self.beats[-1]

    def caption_at(self, t):
        f = round(t * FPS)
        for ev in self.caps:
            if round(ev["s"] * FPS) <= f < round(ev["hide"] * FPS):
                return ev
        return None

    def draw_caption(self, c, t):
        ev = self.caption_at(t)
        if not ev:
            return
        lt = t - ev["s"]
        emph = ev["style"] is not None
        size = CAP_BASE * (1.4 if emph else 1.0)
        f = font("black", size)
        w = text_w(ev["text"], f)
        if w > COL_W - 20:
            size *= (COL_W - 20) / w; f = font("black", size); w = text_w(ev["text"], f)
        k = 0.86 + 0.14 * ease_out(prog(lt, 0, 0.12))
        colr = {BT.G: GREEN, BT.R: RED}.get(ev["style"], INK)
        c.save(); c.translate(CX, CAP_Y); c.scale(k, k)
        x, y = -w / 2, size * 0.36
        c.drawString(ev["text"], x, y + 6, f, paint((0, 0, 0), 0.75, blur=14))
        c.drawString(ev["text"], x, y + 2, f, paint((0, 0, 0), 0.5, blur=3))
        if ev.get("glitch") and lt < 0.22:
            off = 9 * (1 - lt / 0.22)
            c.drawString(ev["text"], x - off, y, f, paint((1, 0.1, 0.2), 0.7))
            c.drawString(ev["text"], x + off, y, f, paint((0.1, 0.9, 1.0), 0.7))
        log_text(c, ev["text"], x, y, w, size, 1)
        c.drawString(ev["text"], x, y, f, paint(colr, 1))
        c.restore()

    def draw_alleged(self, c, b, t):
        if not b["overlay"]:
            return
        f = font("mono", 30)
        pill(c, b["overlay"], CX, 170, f, AMBER, (0.05, 0.05, 0.05), 1, pad=(24, 12), align="center")
        pill(c, b["overlay"], CX, 170, f, AMBER, AMBER, 1, pad=(24, 12), outline=True, align="center")

    def frame(self, t, post=True):
        b = self.beat_at(t)
        lt = t - b["start"]
        c = self.surface.getCanvas()
        c.save()
        p = colorize(dict(b["asset_path_or_spec"]))
        z = p.get("zoom", 1.0)
        if z != 1.0:
            c.translate(CX, 640); c.scale(z, z); c.translate(-CX, -640)
        VIS[b["visual_type"]](c, lt, b["dur"], p)
        c.restore()
        self.draw_alleged(c, b, t)
        self.draw_caption(c, t)
        arr = self.surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3]
        if not post:
            return arr
        fi = int(round(t * FPS))
        g = self.grain[fi % len(self.grain)]
        g = np.repeat(np.repeat(g, 2, 0), 2, 1)[..., None]
        out = arr.astype(np.float32) * self.grade_mul + self.grade_add
        out = out * self.vign + g
        return np.clip(out, 0, 255).astype(np.uint8)


def save_png(arr, path):
    from PIL import Image
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(arr).save(path)


STILLS = [("01_hook", "b02", 1.0), ("02_map", "b09", 1.9), ("03_denials", "b19", 2.2),
          ("04_quote", "b21", 1.85), ("05_8k", "b32", 1.25)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--video", action="store_true")
    ap.add_argument("--frame", type=float)
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "video.mp4"))
    a = ap.parse_args()
    R = Renderer()
    if a.frame is not None:
        save_png(R.frame(a.frame), os.path.join(ROOT, "build", "frame.png"))
    if a.stills:
        for name, bid, lt in STILLS:
            b = next(x for x in R.beats if x["id"] == bid)
            t = b["start"] + lt
            save_png(R.frame(t), os.path.join(ROOT, "out", "stills", f"{name}_{bid}_t{t:.2f}.png"))
            print("still", name, bid, round(t, 2))
    if a.video:
        n = int(round(R.duration * FPS))
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-threads", "4",
               "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out]
        pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for i in range(n):
            pr.stdin.write(R.frame(i / FPS).tobytes())
            if i % 300 == 0:
                print(f"frame {i}/{n}", flush=True)
        pr.stdin.close(); pr.wait()
        print("video written", a.out, n, "frames")


if __name__ == "__main__":
    main()
