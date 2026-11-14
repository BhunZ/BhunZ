"""Drawing helpers on top of skia-python. All coordinates are in 1080x1920 space."""
import math, os
import numpy as np
import skia

W, H, FPS = 1080, 1920, 30
# Text safe zone: keep text out of the bottom 18% and the right 12% (TikTok UI).
SAFE_X0, SAFE_X1 = 60, int(W * 0.88) - 10      # 60 .. 940
SAFE_Y1 = int(H * 0.82) - 10                    # 1564
CX = (SAFE_X0 + SAFE_X1) / 2                    # text column centre (500)
COL_W = SAFE_X1 - SAFE_X0

# Palette
BG = (0.043, 0.051, 0.059)
PANEL = (0.085, 0.095, 0.11)
INK = (0.95, 0.95, 0.94)
MUTED = (0.56, 0.59, 0.62)
GREEN = (0.463, 0.725, 0.0)       # #76B900
RED = (0.90, 0.22, 0.23)          # #E5383B
AMBER = (0.95, 0.65, 0.25)
PAPER = (0.925, 0.91, 0.875)
PAPER_INK = (0.12, 0.12, 0.13)

FONT_DIR = "/usr/share/fonts"
_TF = {}


def tf(name):
    files = {
        "black": "opentype/inter/Inter-Black.otf",
        "xbold": "opentype/inter/Inter-ExtraBold.otf",
        "bold": "opentype/inter/Inter-Bold.otf",
        "semi": "opentype/inter/Inter-SemiBold.otf",
        "med": "opentype/inter/Inter-Medium.otf",
        "reg": "opentype/inter/Inter-Regular.otf",
        "disp": "opentype/inter/InterDisplay-Black.otf",
        "mono": "truetype/jetbrains-mono/JetBrainsMono-Bold.ttf",
        "monor": "truetype/jetbrains-mono/JetBrainsMono-Regular.ttf",
        "serif": "truetype/dejavu/DejaVuSerif-Bold.ttf",
        "serifr": "truetype/dejavu/DejaVuSerif.ttf",
    }
    if name not in _TF:
        _TF[name] = skia.Typeface.MakeFromFile(os.path.join(FONT_DIR, files[name]))
    return _TF[name]


def font(name, size):
    f = skia.Font(tf(name), size)
    f.setSubpixel(True)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


def col(c, a=1.0):
    return skia.Color4f(c[0], c[1], c[2], a)


def paint(c=INK, a=1.0, stroke=None, blur=None, cap_round=False):
    p = skia.Paint(AntiAlias=True)
    p.setColor4f(col(c, a))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        if cap_round:
            p.setStrokeCap(skia.Paint.kRound_Cap)
            p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


# ---------- easing ----------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x):
    x = clamp(x); return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp(x); return 3 * x * x - 2 * x * x * x


def ease_back(x, s=1.70158):
    x = clamp(x) - 1; return x * x * ((s + 1) * x + s) + 1


def prog(t, t0, dur):
    return clamp((t - t0) / dur) if dur > 0 else 1.0


# ---------- text ----------
TEXT_LOG = None   # set to a list to record device-space bounding boxes of every visible text draw (QC)


def log_text(c, s, x, y, w, size, a):
    if TEXT_LOG is None or a <= 0.02 or not s.strip():
        return
    r = c.getTotalMatrix().mapRect(skia.Rect.MakeLTRB(x, y - size * 0.78, x + w, y + size * 0.22))
    TEXT_LOG.append((r.left(), r.top(), r.right(), r.bottom(), s))


def text_w(s, f):
    return f.measureText(s)


def draw_text(c, s, x, y, f, color=INK, a=1.0, align="left", shadow=False, max_w=None):
    """Draw single-line text with baseline y. Returns width."""
    if max_w is not None:
        w = text_w(s, f)
        if w > max_w:
            f = skia.Font(f.getTypeface(), f.getSize() * max_w / w)
    w = text_w(s, f)
    if align == "center":
        x = x - w / 2
    elif align == "right":
        x = x - w
    log_text(c, s, x, y, w, f.getSize(), a)
    if shadow:
        c.drawString(s, x, y + 4, f, paint((0, 0, 0), 0.55 * a, blur=10))
    c.drawString(s, x, y, f, paint(color, a))
    return w


def wrap(s, f, max_w):
    words, lines, cur = s.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if text_w(t, f) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur); cur = wd
    if cur:
        lines.append(cur)
    return lines


def draw_para(c, s, x, y, f, max_w, lh=1.25, color=INK, a=1.0, align="left"):
    """Draw wrapped paragraph; y is first baseline. Returns y after last line."""
    for ln in wrap(s, f, max_w):
        xx = x + (max_w / 2 if align == "center" else 0)
        draw_text(c, ln, xx, y, f, color, a, align=align)
        y += f.getSize() * lh
    return y


def rrect(c, x, y, w, h, r, color, a=1.0, stroke=None, blur=None):
    c.drawRoundRect(skia.Rect.MakeXYWH(x, y, w, h), r, r, paint(color, a, stroke=stroke, blur=blur))


def pill(c, s, x, y, f, fg, bg, a=1.0, pad=(18, 10), outline=False, align="left"):
    w = text_w(s, f)
    h = f.getSize() + pad[1] * 2
    if align == "center":
        x -= (w + pad[0] * 2) / 2
    if outline:
        rrect(c, x, y, w + pad[0] * 2, h, h / 2, bg, a, stroke=3)
    else:
        rrect(c, x, y, w + pad[0] * 2, h, h / 2, bg, a)
    log_text(c, s, x + pad[0], y + pad[1] + f.getSize() * 0.80, w, f.getSize(), a)
    c.drawString(s, x + pad[0], y + pad[1] + f.getSize() * 0.80, f, paint(fg, a))
    return w + pad[0] * 2, h


# ---------- images ----------
_IMG = {}


def load_image(path):
    if path not in _IMG:
        from PIL import Image
        im = Image.open(path).convert("RGBA")
        _IMG[path] = skia.Image.fromarray(np.asarray(im).copy(), colorType=skia.kRGBA_8888_ColorType)
    return _IMG[path]


def draw_cover(c, img, dst, src=None, scale=1.0, pan=(0.0, 0.0), a=1.0):
    """Draw img (optionally cropped to src rect) to fill dst rect (cover), with zoom/pan."""
    sx, sy, sw, sh = src if src else (0, 0, img.width(), img.height())
    dx, dy, dw, dh = dst
    r = max(dw / sw, dh / sh) * scale
    cw, ch = dw / r, dh / r
    cx = sx + sw / 2 + pan[0] * (sw - cw) / 2
    cy = sy + sh / 2 + pan[1] * (sh - ch) / 2
    srect = skia.Rect.MakeXYWH(cx - cw / 2, cy - ch / 2, cw, ch)
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(a)
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(dx, dy, dw, dh))
    c.drawImageRect(img, srect, skia.Rect.MakeXYWH(dx, dy, dw, dh),
                    skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear), p)
    c.restore()


def vgrad(c, x, y, w, h, c0, a0, c1, a1):
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeLinear(
        [skia.Point(x, y), skia.Point(x, y + h)], [col(c0, a0).toColor(), col(c1, a1).toColor()]))
    c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), p)


def radial_glow(c, x, y, r, color, a):
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeRadial(
        skia.Point(x, y), r, [col(color, a).toColor(), col(color, 0).toColor()]))
    c.drawCircle(x, y, r, p)


# ---------- stamp ----------
def stamp(c, s, x, y, size, color, t, rot=-8, a=1.0, under=None):
    """Animated rubber stamp centred at (x, y); t in [0,1] = slam progress."""
    if t <= 0:
        return
    al = a * clamp(t * 4)
    f = font("black", size)
    w = text_w(s, f)
    # slam from up to 1.9x, but never let the stamp leave the text-safe column
    room = 2 * min(x - SAFE_X0, SAFE_X1 - x) / ((w + size * 0.56) * 1.02)
    k = 1.0 + (min(1.9, max(room, 1.0)) - 1.0) * (1 - ease_out(t * 1.25))
    c.save()
    c.translate(x, y); c.rotate(rot); c.scale(k, k)
    pad = size * 0.28
    rrect(c, -w / 2 - pad, -size * 0.62 - pad * 0.6, w + 2 * pad, size * 1.24 + pad * 1.2, 14, color, al, stroke=size * 0.09)
    log_text(c, s, -w / 2, size * 0.36, w, size, al)
    c.drawString(s, -w / 2, size * 0.36, f, paint(color, al))
    # distressed specks (deterministic)
    rng = np.random.default_rng(len(s) * 7 + int(size))
    for _ in range(60):
        px, py = rng.uniform(-w / 2 - pad, w / 2 + pad), rng.uniform(-size * 0.7, size * 0.7)
        c.drawCircle(px, py, rng.uniform(1, 4), paint(under or PANEL, al * 0.6))
    c.restore()
