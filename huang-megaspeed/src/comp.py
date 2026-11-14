"""v2 compositor: full-bleed real footage + printed photo cards + real document screenshots.

Tracks (all times in seconds, resolved from word indices by plan2.py):
  BG    : full-bleed video/photo segments (cut every 2-4 s), slow push/drift, warm grade, -15% brightness
  MID   : real photo as a printed card (white border, shadow, rotated) sliding in
  FRONT : groups of real document cuts that slam in on keywords; camera zooms 1.0->1.8x onto the
          quoted phrase; highlighter swipe (8 frames, left->right). Groups are separated by transitions
          (whip pan with motion blur / 2-frame flash / zoom-through / paper slide-over / hard cut).
  CARD  : the only drawn cards allowed: Alice Huang silhouette, alleged-vs-proven summary, end card.
Deterministic: fixed seeds, frame-indexed sources, no wall-clock dependence.
"""
import json, math, os, subprocess, sys
import numpy as np
import skia
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gfx import *            # noqa: F401,F403  (fonts, easing, paint helpers, stamp)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A2 = os.path.join(ROOT, "assets2")
CAP_Y = int(H * 0.55)        # captions centred at ~55% height
CAP_OFFSET = 0.06            # measured in v1: Kokoro word starts lead audible onsets by ~60 ms
BG_OVERSCAN = 1.12


def sk_from_np(arr):
    if arr.shape[2] == 3:
        arr = np.dstack([arr, np.full(arr.shape[:2], 255, np.uint8)])
    return skia.Image.fromarray(np.ascontiguousarray(arr), colorType=skia.kRGBA_8888_ColorType)


# ------------------------------------------------------------------ background sources
class VideoBG:
    """Sequential frame reader (ffmpeg pipe) producing cover-cropped overscan frames."""
    W0, H0 = int(W * BG_OVERSCAN) // 2 * 2, int(H * BG_OVERSCAN) // 2 * 2

    def __init__(self, path, start=0.0):
        self.path, self.start, self.idx, self.proc, self.last = path, start, -1, None, None

    def _open(self, frame0):
        if self.proc:
            self.proc.kill()
        vf = (f"scale={self.W0}:{self.H0}:force_original_aspect_ratio=increase:flags=bicubic,"
              f"crop={self.W0}:{self.H0},fps=30")
        self.proc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-stream_loop", "-1", "-ss", f"{self.start + frame0 / 30:.3f}",
                                      "-i", self.path, "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
                                     stdout=subprocess.PIPE)
        self.idx = frame0 - 1

    def frame(self, fi):
        if self.proc is None or fi < self.idx or fi > self.idx + 30:
            self._open(fi)
        n = self.W0 * self.H0 * 4
        while self.idx < fi:
            buf = self.proc.stdout.read(n)
            if len(buf) < n:
                break
            self.last = np.frombuffer(buf, np.uint8).reshape(self.H0, self.W0, 4)
            self.idx += 1
        return self.last

    def close(self):
        if self.proc:
            self.proc.kill(); self.proc = None


_IMGS = {}


def img(path):
    if path not in _IMGS:
        from PIL import Image
        _IMGS[path] = skia.Image.fromarray(np.asarray(Image.open(path).convert("RGBA")).copy(),
                                           colorType=skia.kRGBA_8888_ColorType)
    return _IMGS[path]


# ------------------------------------------------------------------ the compositor
class Comp:
    def __init__(self, plan):
        self.plan = plan
        self.surface = skia.Surface(W, H)
        self.videos = {}
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / np.sqrt(2)
        self.vign = (1.0 - 0.45 * np.clip(r, 0, 1) ** 2.0)[..., None]
        rng = np.random.default_rng(1234)
        self.grain = [rng.normal(0, 5.0, (H // 2, W // 2)).astype(np.float32) for _ in range(8)]
        self.cuts = {c["id"]: c for c in json.load(open(os.path.join(A2, "cuts.json")))}
        self.layer_rects = []

    # ---------- BG
    def seg_at(self, t):
        segs = self.plan["bg"]
        for s in segs:
            if s["start"] <= t < s["end"]:
                return s
        return segs[-1]

    def draw_bg(self, c, t):
        s = self.seg_at(t)
        lt = t - s["start"]
        drift = s.get("drift", (0.0, -1.0))
        k = 1.0 + 0.045 * lt / max(s["end"] - s["start"], 0.1)
        dx, dy = drift[0] * 18 * lt, drift[1] * 12 * lt
        self.cam_drift = (dx, dy)
        if s["kind"] == "video":
            v = self.videos.setdefault(s["id"], VideoBG(os.path.join(ROOT, s["file"]), s.get("clip_start", 0.0)))
            fr = v.frame(int(round(lt * 30)))
            if fr is None:
                c.clear(col(BG)); return
            im = sk_from_np(fr)
            c.save(); c.translate(W / 2 + dx, H / 2 + dy); c.scale(k, k)
            c.drawImage(im, -im.width() / 2, -im.height() / 2, skia.SamplingOptions(skia.FilterMode.kLinear))
            c.restore()
        else:
            im = img(os.path.join(ROOT, s["file"]))
            crop = s.get("crop")
            draw_cover(c, im, (0, 0, W, H), src=crop, scale=BG_OVERSCAN * k, pan=(drift[0] * 0.4 * lt / 3, 0))
        if s.get("desat"):
            p = skia.Paint(); p.setColor4f(col((0.5, 0.5, 0.5), s["desat"])); p.setBlendMode(skia.BlendMode.kSaturation)
            c.drawRect(skia.Rect.MakeWH(W, H), p)
        # -15% brightness on the back layer + slight extra darkening where documents sit
        c.drawRect(skia.Rect.MakeWH(W, H), paint((0, 0, 0), 0.15 + s.get("dim", 0.0)))

    # ---------- MID (printed photo cards)
    def draw_mid(self, c, t):
        for m in self.plan["mid"]:
            if not (m["start"] <= t < m["end"]):
                continue
            lt = t - m["start"]
            e = ease_out(prog(lt, 0, 0.45))
            out = ease_out(prog(t, m["end"] - 0.25, 0.25))
            im = img(os.path.join(ROOT, m["file"]))
            w = m.get("w", 640); h = w * im.height() / im.width() if not m.get("crop") else w * m["crop"][3] / m["crop"][2]
            cx, cy = m.get("pos", (540, 760))
            px, py = self.cam_drift
            sx = (1 - e) * m.get("from_x", -900) + out * 1100
            c.save()
            c.translate(cx + sx + 1.5 * px, cy + 1.5 * py); c.rotate(m.get("rot", -3.5) * (1 - 0.3 * e))
            bw = 18
            rrect(c, -w / 2 - bw + 14, -h / 2 - bw + 22, w + 2 * bw, h + 2 * bw + 36, 4, (0, 0, 0), 0.55, blur=22)
            rrect(c, -w / 2 - bw, -h / 2 - bw, w + 2 * bw, h + 2 * bw + 36, 4, (0.97, 0.96, 0.93))
            draw_cover(c, im, (-w / 2, -h / 2, w, h), src=m.get("crop"))
            if m.get("caption"):
                draw_text(c, m["caption"], -w / 2, h / 2 + 30, font("monor", 22), (0.25, 0.25, 0.25))
            c.restore()
            self.layer_rects.append((cx - w / 2 - bw, cy - h / 2 - bw, w + 2 * bw, h + 2 * bw + 36))

    # ---------- FRONT (document stacks)
    def group_at(self, t):
        for g in self.plan["front"]:
            if g["start"] <= t < g["end"]:
                return g
        return None

    def draw_front(self, c, t, g=None, k_override=None):
        g = g or self.group_at(t)
        if not g:
            return
        items = [it for it in g["items"] if it["at"] <= t]
        if not items:
            return
        stamps = [it for it in items if it["cut"] == "__stamp__"]
        items = [it for it in items if it["cut"] != "__stamp__"]
        for it in stamps:                                   # stamp-only beat (e.g. ALLEGED over port footage)
            colr = {"green": GREEN, "amber": AMBER}.get(it.get("stamp_color"), RED)
            stamp(c, it["stamp"], 540, 700, 150, colr, prog(t - it["at"], 0, 0.3), rot=-8, under=(0.1, 0.1, 0.1))
        if not items:
            return
        for it in items:
            if "_rect" not in it:
                self._place(it)
        cur = items[-1]
        lt = t - cur["at"]
        # camera: zoom 1.0 -> zmax onto the current item's focus phrase
        zmax = cur.get("zoom", 1.8) if cur.get("focus_px") else 1.0
        fl = self.cuts[cur["cut"]].get("focus_lines_px") or []
        if len(fl) > 1:
            zmax = min(zmax, 0.95 * W / max(1.0, cur["_s"] * (max(l[0] + l[2] for l in fl) - min(l[0] for l in fl))))
        zk = ease_in_out(prog(lt, 0.30, max(0.6, min(1.4, cur.get("hold", 1.6) - 0.35))))
        z = 1.0 + (zmax - 1.0) * zk
        px, py = self.cam_drift
        c.save()
        anchor = cur["_anchor"]
        fx, fy = cur["_focus_xy"] if cur.get("focus_px") else anchor
        tx, ty = anchor[0] + (fx - anchor[0]) * zk, anchor[1] + (fy - anchor[1]) * zk
        c.translate(540 + 2 * px, 700 + 2 * py); c.scale(z, z); c.translate(-tx, -ty)
        for it in items:
            self._draw_doc(c, t, it, it is cur)
        c.restore()

    def _place(self, it):
        """Precompute layout for a document item (display size and anchor point)."""
        cut = self.cuts[it["cut"]]
        im = img(os.path.join(ROOT, cut["file"]))
        dw = it.get("w", 0.90) * W
        s = dw / im.width()
        dh = im.height() * s
        maxh = 1020
        if dh > maxh:
            s *= maxh / dh; dw, dh = im.width() * s, maxh
        cx, cy = it.get("pos", (540, 700))
        it["_s"], it["_rect"] = s, (cx - dw / 2, cy - dh / 2, dw, dh)
        it["_anchor"] = (cx, cy)
        if cut.get("focus_px"):
            fx, fy, fw, fh = cut["focus_px"]
            it["focus_px"] = cut["focus_px"]
            it["_focus_xy"] = (cx - dw / 2 + (fx + fw / 2) * s, cy - dh / 2 + (fy + fh / 2) * s)

    def _draw_doc(self, c, t, it, is_cur):
        if "_rect" not in it:
            self._place(it)
        cut = self.cuts[it["cut"]]
        im = img(os.path.join(ROOT, cut["file"]))
        x, y, dw, dh = it["_rect"]
        lt = t - it["at"]
        land = prog(lt, 0, 8 / 30)                       # slam in over 8 frames
        sc = 1.0 + 0.35 * (1 - ease_out(land))
        rot = it.get("rot", 0.0)
        c.save()
        c.translate(x + dw / 2, y + dh / 2); c.rotate(rot); c.scale(sc, sc)
        if lt < 0.12:
            c.translate(0, -60 * (1 - land))
        c.drawRect(skia.Rect.MakeXYWH(-dw / 2 + 12, -dh / 2 + 20, dw, dh), paint((0, 0, 0), 0.6 * land, blur=26))
        c.drawImageRect(im, skia.Rect.MakeXYWH(-dw / 2, -dh / 2, dw, dh),
                        skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear))
        # highlighter swipe (8 frames, mask left->right) once the camera starts moving
        if is_cur and cut.get("focus_px") and it.get("highlight", True):
            hk = prog(lt, 0.45, 8 / 30)
            if hk > 0:
                s = it["_s"]
                hp = skia.Paint(AntiAlias=True); hp.setColor4f(col((1.0, 0.86, 0.15), 0.55)); hp.setBlendMode(skia.BlendMode.kMultiply)
                lines = cut.get("focus_lines_px") or [cut["focus_px"]]
                tot = sum(l[2] for l in lines); done = ease_out(hk) * tot
                for fx, fy, fw, fh in lines:                    # swipe line by line, left -> right
                    wv = max(0.0, min(fw, done)); done -= fw
                    if wv > 0:
                        c.drawRect(skia.Rect.MakeXYWH(-dw / 2 + fx * s - 4, -dh / 2 + fy * s - 3, wv * s + 8, fh * s + 6), hp)
        if it.get("stamp"):
            colr = {"green": GREEN, "amber": AMBER}.get(it.get("stamp_color"), RED)
            stamp(c, it["stamp"], dw * 0.36, dh * 0.5 + 6, 70, colr, prog(lt, it.get("stamp_at", 0.25), 0.3), rot=-9, under=(0.95, 0.95, 0.93))
        c.restore()
        self.layer_rects.append((x, y, dw, dh))

    # ---------- allowed drawn cards
    def draw_cards(self, c, t):
        for cd in self.plan["cards"]:
            if not (cd["start"] <= t < cd["end"]):
                continue
            lt = t - cd["start"]
            fn = getattr(self, "card_" + cd["type"])
            fn(c, lt, cd["end"] - cd["start"], cd)

    def card_silhouette(self, c, lt, d, cd):
        e = ease_out(prog(lt, 0, 0.35))
        x0, y0, w, h = 150, 300, 780, 720
        c.save(); c.translate(0, (1 - e) * 60)
        rrect(c, x0, y0, w, h, 26, (0.08, 0.09, 0.1), 0.86 * e)
        rrect(c, x0, y0, w, h, 26, (0.4, 0.42, 0.45), e, stroke=2)
        sc = (0.36, 0.38, 0.41)
        c.drawCircle(540, 540, 110, paint(sc, e))
        sh = skia.Path(); sh.moveTo(300, 1020); sh.cubicTo(300, 800, 420, 690, 540, 690); sh.cubicTo(660, 690, 780, 800, 780, 1020); sh.close()
        c.save(); c.clipRect(skia.Rect.MakeXYWH(x0, y0, w, h)); c.drawPath(sh, paint(sc, e)); c.restore()
        c.restore()
        el = ease_out(prog(lt, 0.25, 0.35))
        rrect(c, 110, 1160, 860, 150, 18, (0.05, 0.05, 0.06), 0.8 * el)
        draw_text(c, "Alice Huang", 540, 1225, font("xbold", 60), INK, el, align="center")
        draw_text(c, "former Megaspeed executive (no relation)", 540, 1282, font("med", 36), MUTED, el, align="center")
        self.layer_rects.append((x0, y0, w, h))

    def card_summary(self, c, lt, d, cd):
        e1 = ease_out(prog(lt, 0, 0.3)); e2 = ease_out(prog(lt, 0.45, 0.3))
        hw = 470
        for j, (ttl, colr, items, e) in enumerate([
                ("ALLEGED", AMBER, ["Intelligence-asset claim: anonymous U.S. officials, via NYT", "Chip-diversion suspicions: U.S. probe"], e1),
                ("NOT PROVEN", GREEN, ["No charges reported", "Board: no reason to believe secrets were compromised", "China, Megaspeed deny"], e2)]):
            x = 60 + j * (hw + 20)
            c.save(); c.translate(0, (1 - e) * 60)
            rrect(c, x, 260, hw, 860, 22, (0.06, 0.065, 0.075), 0.86 * e)
            rrect(c, x, 260, hw, 12, 6, colr, e)
            draw_text(c, ttl, x + hw / 2, 380, font("disp", 64), colr, e, align="center", max_w=hw - 40)
            y = 480
            for s in items:
                y = draw_para(c, s, x + 30, y, font("semi", 38), hw - 60, 1.22, INK, e) + 44
            c.restore()
        self.layer_rects.append((60, 260, 960, 860))

    def card_end(self, c, lt, d, cd):
        c.clear(col(BG))
        e = ease_out(prog(lt, 0, 0.35))
        draw_text(c, "AS OF NOV 14, 2026", 60, 280, font("mono", 40), GREEN, e)
        draw_para(c, "Allegations are unproven. Nvidia, Megaspeed and China deny wrongdoing. Story developing.",
                  60, 360, font("xbold", 50), 880, 1.18, INK, e)
        y = draw_text(c, "SOURCES", 60, 620, font("mono", 28), MUTED, e) and 670
        y = draw_para(c, cd["sources"], 60, y, font("med", 30), 880, 1.3, INK, e) + 30
        draw_text(c, "FOOTAGE & PHOTOS", 60, y, font("mono", 28), MUTED, e); y += 50
        y = draw_para(c, cd["credits"], 60, y, font("med", 24), 880, 1.3, INK, e) + 24
        draw_para(c, "AI-generated narration. Full credits and source links in the description.", 60, y, font("med", 26), 880, 1.3, MUTED, e)
        self.layer_rects.append((0, 0, W, H))

    # ---------- captions / overlays
    def draw_caption(self, c, t):
        f_ = round(t * 30)
        ev = None
        for e in self.plan["captions"]:
            if round((e["s"] + CAP_OFFSET) * 30) <= f_ < round((e["hide"] + CAP_OFFSET) * 30):
                ev = e; break
        if not ev:
            return
        lt = t - (ev["s"] + CAP_OFFSET)
        size = 96 * (1.4 if ev["style"] else 1.0)
        f = font("black", size); w = text_w(ev["text"], f)
        if w > 900:
            size *= 900 / w; f = font("black", size); w = text_w(ev["text"], f)
        k = 0.86 + 0.14 * ease_out(prog(lt, 0, 0.12))
        colr = {"green": GREEN, "red": RED}.get(ev["style"], INK)
        c.save(); c.translate(540, CAP_Y); c.scale(k, k)
        x, y = -w / 2, size * 0.36
        c.drawString(ev["text"], x, y + 6, f, paint((0, 0, 0), 0.8, blur=16))
        st = paint((0, 0, 0), 0.85, stroke=size * 0.10); st.setStrokeJoin(skia.Paint.kRound_Join)
        c.drawString(ev["text"], x, y, f, st)
        c.drawString(ev["text"], x, y, f, paint(colr, 1))
        log_text(c, ev["text"], x, y, w, size, 1)
        c.restore()

    def draw_overlays(self, c, t):
        for o in self.plan["labels"]:
            if o["start"] <= t < o["end"]:
                f = font("mono", 30)
                pill(c, o["text"], 540, 150, f, AMBER, (0.04, 0.04, 0.04), 0.9, pad=(24, 12), align="center")
                pill(c, o["text"], 540, 150, f, AMBER, AMBER, 1, pad=(24, 12), outline=True, align="center")
        g = self.group_at(t)
        if g:
            items = [it for it in g["items"] if it["at"] <= t]
            if items:
                cut = self.cuts[items[-1]["cut"]]
                tag = f"{cut['outlet']} · {cut['date']}"
                pill(c, tag, 60, 1430, font("mono", 26), INK, (0.04, 0.04, 0.04), 0.82, pad=(18, 10))

    # ---------- frame
    def compose(self, t, group=None):
        self.layer_rects = []
        c = self.surface.getCanvas()
        c.save()
        self.draw_bg(c, t)
        self.draw_mid(c, t)
        self.draw_front(c, t, g=group)
        self.draw_cards(c, t)
        c.restore()
        return self.surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3].copy()

    def frame(self, t, post=True):
        fi = int(round(t * 30))
        g = self.group_at(t)
        base = self.compose(t)
        rects = list(self.layer_rects)
        # transitions into the current front group
        if g and g.get("trans") and t - g["start"] < g.get("trans_d", 0.2) and g.get("prev") is not None:
            prev = self.plan["front"][g["prev"]]
            k = (t - g["start"]) / g.get("trans_d", 0.2)
            old = self.compose(t, group=prev)
            base = transition(g["trans"], old, base, k)
        # captions + overlays on top
        im = sk_from_np(base)
        c = self.surface.getCanvas(); c.clear(col(BG)); c.drawImage(im, 0, 0)
        self.draw_overlays(c, t)
        self.draw_caption(c, t)
        arr = self.surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3]
        self.layer_rects = rects
        if not post:
            return arr
        out = arr.astype(np.float32)
        out = out * np.array([1.04, 1.0, 0.93], np.float32) + np.array([5.0, 3.0, 0.0], np.float32)
        for lk in self.plan.get("leaks", []):              # light leaks (max 4)
            if lk["t"] <= t < lk["t"] + lk["d"]:
                out = light_leak(out, (t - lk["t"]) / lk["d"], lk.get("side", 0))
        out = out * self.vign
        g2 = self.grain[fi % len(self.grain)]
        out += np.repeat(np.repeat(g2, 2, 0), 2, 1)[..., None]
        if fi in self.plan.get("glitch_frames", []):       # 1-frame RGB glitch
            out[..., 0] = np.roll(out[..., 0], 14, axis=1); out[..., 2] = np.roll(out[..., 2], -14, axis=1)
        return np.clip(out, 0, 255).astype(np.uint8)


def transition(kind, a, b, k):
    k = clamp(k)
    if kind == "flash":
        w = 1 - abs(2 * k - 1)
        return np.clip((b if k > 0.5 else a).astype(np.float32) * (1 - w) + 255 * w, 0, 255).astype(np.uint8)
    if kind == "whip":
        e = ease_in_out(k)
        idx = np.arange(W) + int(e * W)
        strip = np.where((idx < W)[None, :, None], a[:, np.clip(idx, 0, W - 1)], b[:, np.clip(idx - W, 0, W - 1)])
        amp = 40 * math.sin(math.pi * k)                # horizontal motion blur, strongest mid-whip
        out = np.zeros_like(strip, np.float32)
        for i in range(6):
            out += np.roll(strip, int((i - 2.5) * amp / 2.5), axis=1)
        return np.clip(out / 6, 0, 255).astype(np.uint8)
    if kind == "zoom":
        e = ease_in_out(k)
        im = sk_from_np(a); s = skia.Surface(W, H); c = s.getCanvas()
        c.translate(W / 2, H / 2); c.scale(1 + 0.6 * e, 1 + 0.6 * e); c.drawImage(im, -W / 2, -H / 2)
        za = s.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3].astype(np.float32)
        return np.clip(za * (1 - e) + b.astype(np.float32) * e, 0, 255).astype(np.uint8)
    if kind == "slide":
        e = ease_out(k)
        off = int((1 - e) * H)
        out = a.copy()
        if off < H:
            out[off:] = b[:H - off]
            out[max(0, off - 24):off] = (out[max(0, off - 24):off] * 0.55).astype(np.uint8)   # paper edge shadow
        return out
    return b


def light_leak(out, k, side):
    yy, xx = np.ogrid[0:H:8, 0:W:8]
    cx = (0.1 + 0.8 * k) * W if side == 0 else (0.9 - 0.8 * k) * W
    cy = 0.25 * H + 0.3 * H * k
    r = np.exp(-(((xx - cx) / (W * 0.55)) ** 2 + ((yy - cy) / (H * 0.4)) ** 2))
    a = (math.sin(math.pi * k) * 0.55) * r
    a = np.repeat(np.repeat(a, 8, 0), 8, 1)[:H, :W, None].astype(np.float32)
    return out + a * np.array([255, 150, 60], np.float32)
