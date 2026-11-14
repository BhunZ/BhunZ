"""Visual generators. Each takes (canvas, lt, d, p): local time, beat duration, params."""
import json, math, os
import numpy as np
import skia
from gfx import *

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET = lambda *a: os.path.join(ROOT, "assets", *a)
STAGE_CY = 640          # visual centre of the stage area (caption sits below, ~1185)


def bg(c, tint=None, glow=None):
    c.clear(col(BG))
    if glow:
        radial_glow(c, glow[0], glow[1], glow[2], glow[3], glow[4])


def push(c, lt, d, amount=0.045, cx=CX, cy=STAGE_CY):
    k = 1 + amount * clamp(lt / max(d, 0.01))
    c.translate(cx, cy); c.scale(k, k); c.translate(-cx, -cy)


def enter(c, lt, dur=0.35, dy=70):
    e = ease_out(prog(lt, 0, dur))
    c.translate(0, (1 - e) * dy)
    return e


def kicker(c, s, y, color=GREEN, a=1.0, x=SAFE_X0):
    f = font("mono", 30)
    rrect(c, x, y - 30, 8, 36, 2, color, a)
    draw_text(c, s, x + 24, y, f, color, a)


def src_tag(c, s, a=1.0):
    """Small source line under the caption band, inside the safe zone."""
    f = font("monor", 26)
    draw_text(c, s, CX, 1405, f, MUTED, 0.9 * a, align="center", max_w=COL_W)


# ------------------------------------------------------------------ GPU hook
def draw_gpu(c, cx, cy, s, desat=0.0):
    g = tuple(GREEN[i] * (1 - desat) + 0.45 * desat for i in range(3))
    c.save(); c.translate(cx, cy); c.scale(s, s)
    # card body
    rrect(c, -380, -210, 760, 420, 26, (0.11, 0.12, 0.13))
    rrect(c, -380, -210, 760, 420, 26, (0.25, 0.27, 0.29), stroke=3)
    # heatsink fins
    for i in range(22):
        x = -350 + i * 20
        c.drawRect(skia.Rect.MakeXYWH(x, -180, 8, 250), paint((0.20, 0.21, 0.23)))
    # fan rings
    for fx in (-190, 150):
        c.drawCircle(fx, -55, 118, paint((0.07, 0.075, 0.08)))
        c.drawCircle(fx, -55, 118, paint((0.3, 0.32, 0.34), stroke=4))
        for k in range(9):
            a = math.radians(k * 40)
            p = skia.Path(); p.moveTo(fx, -55)
            p.quadTo(fx + 90 * math.cos(a + 0.5), -55 + 90 * math.sin(a + 0.5), fx + 110 * math.cos(a), -55 + 110 * math.sin(a))
            c.drawPath(p, paint((0.24, 0.25, 0.27), stroke=7, cap_round=True))
        c.drawCircle(fx, -55, 26, paint((0.16, 0.17, 0.18)))
    # accent stripe + die window
    rrect(c, -380, 95, 760, 14, 4, g, 0.95)
    rrect(c, -60, 125, 120, 60, 6, (0.05, 0.05, 0.06))
    for i in range(6):
        for j in range(3):
            c.drawRect(skia.Rect.MakeXYWH(-52 + i * 18, 133 + j * 16, 12, 10), paint(g, 0.8))
    # PCIe contacts
    for i in range(34):
        c.drawRect(skia.Rect.MakeXYWH(-250 + i * 14, 212, 9, 34), paint((0.80, 0.63, 0.25)))
    c.restore()
    radial_glow(c, cx, cy + 40 * s, 520 * s, g, 0.16 * (1 - desat))


def v_gpu(c, lt, d, p):
    bg(c)
    stamp_at = p.get("stamp_at")
    desat = ease_out(prog(lt, stamp_at, 0.4)) * 0.85 if stamp_at is not None else 0
    c.save(); push(c, lt + p.get("t_off", 0), p.get("push_d", d), 0.05)
    draw_gpu(c, 540, STAGE_CY, 1.05, desat)
    c.restore()
    if p.get("label"):
        e = ease_out(prog(lt, 0.15, 0.4))
        draw_text(c, p["label"], CX, 330, font("mono", 32), MUTED, e, align="center")
    if stamp_at is not None:
        stamp(c, "RESIGNED", CX, STAGE_CY, 128, RED, prog(lt, stamp_at, 0.35))


# ------------------------------------------------------------------ 8-K document (recreated)
DOC_LINE = ("On November 11, 2026, the Board of Directors, or the Board, of NVIDIA Corporation "
            "accepted the resignation of Jen-Hsun Huang")


def v_doc8k(c, lt, d, p):
    bg(c, glow=(540, 700, 900, GREEN, 0.05))
    c.save(); push(c, lt, d, 0.05, cy=700)
    e = enter(c, lt, 0.35, 90)
    x0, y0, w = SAFE_X0 + 10, 250, COL_W - 20
    rrect(c, x0 + 10, y0 + 18, w, 800, 10, (0, 0, 0), 0.5 * e, blur=24)
    rrect(c, x0, y0, w, 800, 10, PAPER, e)
    fi = PAPER_INK
    draw_text(c, "UNITED STATES", x0 + w / 2, y0 + 70, font("serif", 28), fi, e, align="center")
    draw_text(c, "SECURITIES AND EXCHANGE COMMISSION", x0 + w / 2, y0 + 108, font("serif", 26), fi, e, align="center")
    c.drawRect(skia.Rect.MakeXYWH(x0 + 60, y0 + 135, w - 120, 3), paint(fi, e))
    draw_text(c, "FORM 8-K", x0 + w / 2, y0 + 215, font("serif", 64), fi, e, align="center")
    draw_text(c, "CURRENT REPORT", x0 + w / 2, y0 + 262, font("serifr", 28), fi, e, align="center")
    draw_text(c, "NVIDIA CORPORATION", x0 + w / 2, y0 + 320, font("serif", 30), fi, e, align="center")
    draw_text(c, "Item 5.02  Departure of Directors or Certain Officers", x0 + 50, y0 + 400,
              font("serif", 25), fi, e, max_w=w - 100)
    # body: verified sentence + highlight swipe
    fb = font("serifr", 31)
    lines = wrap(DOC_LINE, fb, w - 100)
    y = y0 + 465
    hl = p.get("highlight_at")
    for i, ln in enumerate(lines):
        if hl is not None and ("resignation" in ln or "Jen-Hsun" in ln or "accepted" in ln):
            k = ease_out(prog(lt, hl + 0.12 * i, 0.4))
            pre = ln[:ln.index("accepted")] if "accepted" in ln else ""
            hx = text_w(pre, fb)
            tw = text_w(ln, fb) - hx
            c.drawRect(skia.Rect.MakeXYWH(x0 + 46 + hx, y - 30, (tw + 8) * k, 42), paint((1.0, 0.86, 0.2), 0.75 * e))
        draw_text(c, ln, x0 + 50, y, fb, fi, e)
        y += 44
    # abstract placeholder lines (not text) for the rest of the filing
    for i in range(5):
        ww = (w - 100) * (0.95 if i % 3 else 0.72)
        rrect(c, x0 + 50, y + 10 + i * 40, ww, 14, 7, (0.6, 0.6, 0.58), 0.6 * e)
    c.restore()
    if p.get("reason_at") is not None:
        k = ease_back(prog(lt, p["reason_at"], 0.35))
        if k > 0:
            c.save(); c.translate(CX, 1000); c.scale(k, k)
            pill(c, "REASON GIVEN IN FILING:  NONE", 0, -30, font("mono", 34), INK, RED, 1, pad=(26, 16), align="center")
            c.restore()
    if p.get("stamp_at") is not None:
        stamp(c, "RESIGNED", CX, 955, 110, RED, prog(lt, p["stamp_at"], 0.35), rot=-10, under=PAPER)
    if p.get("date_at") is not None:
        k = ease_back(prog(lt, p["date_at"], 0.35))
        if k > 0:
            c.save(); c.translate(CX, 1000); c.scale(k, k)
            pill(c, "BOARD ACCEPTED RESIGNATION · NOV 11, 2026", 0, -30, font("mono", 30), BG, GREEN, 1, pad=(24, 14), align="center")
            c.restore()
    draw_text(c, "RECREATED FROM NVIDIA FORM 8-K (SEC), FILED NOV 12, 2026", CX, 205, font("mono", 24), MUTED, 1, align="center", max_w=COL_W)


# ------------------------------------------------------------------ photo with titles
def v_photo(c, lt, d, p):
    bg(c)
    img = load_image(ASSET("commons", p["img"]))
    k = 1.04 + 0.05 * clamp(lt / d)
    panx = p.get("pan", 0.0) * (clamp(lt / d) - 0.5) * 2
    draw_cover(c, img, (0, 0, W, H), src=p.get("crop"), scale=k, pan=(panx, 0), a=1.0)
    vgrad(c, 0, 0, W, 700, BG, 0.75, BG, 0.0)
    vgrad(c, 0, 900, W, 1020, BG, 0.0, BG, 0.92)
    c.drawRect(skia.Rect.MakeXYWH(0, 0, W, H), paint(BG, p.get("dim", 0.25)))
    if p.get("kicker"):
        e = ease_out(prog(lt, 0.1, 0.35))
        kicker(c, p["kicker"], 300, p.get("kcolor", GREEN), e)
    if p.get("title"):
        e = ease_out(prog(lt, 0.15, 0.4))
        c.save(); c.translate(0, (1 - e) * 40)
        y = 420
        for ln in wrap(p["title"], font("disp", p.get("tsize", 104)), COL_W):
            draw_text(c, ln, SAFE_X0, y, font("disp", p.get("tsize", 104)), INK, e, shadow=True)
            y += p.get("tsize", 104) * 1.02
        c.restore()
    if p.get("chips"):
        y = p.get("chip_y", 880)
        for i, s in enumerate(p["chips"]):
            e = ease_back(prog(lt, 0.35 + 0.18 * i, 0.35))
            if e > 0:
                c.save(); c.translate(SAFE_X0, y); c.scale(e, e)
                pill(c, s, 0, 0, font("mono", 32), INK, PANEL, 0.92, pad=(22, 14))
                c.restore()
            y += 78
    if p.get("credit"):
        draw_text(c, p["credit"], SAFE_X0, 1500, font("monor", 20), MUTED, 0.85, max_w=COL_W)


# ------------------------------------------------------------------ generic title / statement card
def v_card(c, lt, d, p):
    bg(c, glow=(540, 640, 800, p.get("glow", GREEN), 0.07))
    c.save(); push(c, lt, d, 0.03)
    e = enter(c, lt, 0.32, 60)
    y = p.get("y", 380)
    if p.get("kicker"):
        kicker(c, p["kicker"], y, p.get("kcolor", GREEN), e); y += 90
    if p.get("title"):
        f = font("disp", p.get("tsize", 96))
        for ln in wrap(p["title"], f, COL_W):
            draw_text(c, ln, SAFE_X0, y + f.getSize() * 0.8, f, p.get("tcolor", INK), e)
            y += f.getSize() * 1.05
        y += 30
    for i, item in enumerate(p.get("lines", [])):
        txt, style = item if isinstance(item, (list, tuple)) else (item, "body")
        ei = ease_out(prog(lt, 0.25 + 0.22 * i, 0.35)) * e
        if style == "body":
            f = font("semi", 44); y = draw_para(c, txt, SAFE_X0, y + 44, f, COL_W, 1.25, INK, ei) + 6
        elif style == "muted":
            f = font("med", 36); y = draw_para(c, txt, SAFE_X0, y + 36, f, COL_W, 1.25, MUTED, ei) + 6
        elif style == "quote":
            f = font("xbold", 56); y = draw_para(c, txt, SAFE_X0, y + 56, f, COL_W, 1.18, INK, ei) + 10
        elif style.startswith("pill"):
            colr = {"pill_red": RED, "pill_amber": AMBER, "pill_green": GREEN}.get(style, PANEL)
            fg = BG if style in ("pill_amber", "pill_green") else INK
            pill(c, txt, SAFE_X0, y + 20, font("mono", 32), fg, colr, ei, pad=(22, 14)); y += 90
    c.restore()
    if p.get("stamp"):
        s, sx, sy, sat, scol = p["stamp"]
        stamp(c, s, sx, sy, 110, {"red": RED, "green": GREEN, "amber": AMBER}[scol], prog(lt, sat, 0.35))


# ------------------------------------------------------------------ headline card (recreated, typographic)
def v_headline(c, lt, d, p):
    bg(c)
    if p.get("bgimg"):
        img = load_image(ASSET("commons", p["bgimg"]))
        draw_cover(c, img, (0, 0, W, H), src=p.get("crop"), scale=1.1 + 0.03 * lt / d, a=0.35)
        c.drawRect(skia.Rect.MakeXYWH(0, 0, W, H), paint(BG, 0.55))
    e = ease_out(prog(lt, 0, 0.28))
    c.save()
    c.translate(CX, 640); c.rotate(-2.5 * (1 - e) - 1.2); c.scale(0.9 + 0.1 * e + 0.03 * lt / d, 0.9 + 0.1 * e + 0.03 * lt / d)
    c.translate(-CX, -640 + (1 - e) * 220)
    x0, y0, w, h = SAFE_X0, 330, COL_W, 640
    rrect(c, x0 + 12, y0 + 20, w, h, 6, (0, 0, 0), 0.55 * e, blur=26)
    rrect(c, x0, y0, w, h, 6, PAPER, e)
    draw_text(c, p["outlet"], x0 + 50, y0 + 95, font("serif", 50), PAPER_INK, e, max_w=w - 100)
    draw_text(c, p["date"], x0 + 50, y0 + 145, font("monor", 28), (0.35, 0.35, 0.36), e)
    c.drawRect(skia.Rect.MakeXYWH(x0 + 50, y0 + 175, w - 100, 3), paint(PAPER_INK, e))
    f = font("serif", 50)
    y = draw_para(c, p["text"], x0 + 50, y0 + 255, f, w - 100, 1.22, PAPER_INK, e)
    draw_text(c, p["foot"], x0 + 50, y0 + h - 40, font("monor", 22), (0.38, 0.38, 0.4), e, max_w=w - 100)
    c.restore()


# ------------------------------------------------------------------ silhouette card (no face)
def v_silhouette(c, lt, d, p):
    bg(c, glow=(CX, 560, 600, (0.6, 0.62, 0.66), 0.06))
    c.save(); push(c, lt, d, 0.035)
    e = enter(c, lt, 0.35, 50)
    rrect(c, SAFE_X0 + 80, 260, COL_W - 160, 640, 24, PANEL, e)
    rrect(c, SAFE_X0 + 80, 260, COL_W - 160, 640, 24, (0.3, 0.32, 0.35), e, stroke=2)
    # neutral generic silhouette: head + shoulders, flat grey, no features
    sc = (0.34, 0.36, 0.39)
    c.drawCircle(CX, 500, 105, paint(sc, e))
    sh = skia.Path(); sh.moveTo(CX - 230, 900); sh.cubicTo(CX - 230, 700, CX - 120, 640, CX, 640)
    sh.cubicTo(CX + 120, 640, CX + 230, 700, CX + 230, 900); sh.close()
    c.save(); c.clipRect(skia.Rect.MakeXYWH(SAFE_X0 + 80, 260, COL_W - 160, 640)); c.drawPath(sh, paint(sc, e)); c.restore()
    c.restore()
    el = ease_out(prog(lt, p.get("label_at", 0.25), 0.35))
    draw_text(c, "Alice Huang", CX, 1010, font("xbold", 62), INK, el, align="center")
    draw_text(c, "former Megaspeed executive (no relation)", CX, 1068, font("med", 38), MUTED, el, align="center", max_w=COL_W)


# ------------------------------------------------------------------ DENIED card
def v_denied(c, lt, d, p):
    bg(c, glow=(CX, 640, 700, RED, 0.06))
    c.save(); push(c, lt, d, 0.03)
    e = enter(c, lt, 0.3, 60)
    x0, y0, w, h = SAFE_X0, 300, COL_W, 720
    rrect(c, x0, y0, w, h, 22, PANEL, e)
    rrect(c, x0, y0, w, 12, 6, RED, e)
    draw_text(c, p["who"], x0 + 50, y0 + 120, font("disp", 72), INK, e, max_w=w - 100)
    draw_text(c, p["when"], x0 + 50, y0 + 175, font("monor", 30), MUTED, e)
    y = y0 + 270
    for i, q in enumerate(p["quotes"]):
        ei = ease_out(prog(lt, 0.2 + 0.25 * i, 0.35)) * e
        y = draw_para(c, q, x0 + 50, y, font("xbold" if i == 0 else "semi", 52 if i == 0 else 38), w - 100,
                      1.2, INK if i == 0 else MUTED, ei) + 26
    c.restore()
    stamp(c, p.get("stamp", "DENIED"), CX + 150, 870, 104, RED, prog(lt, p.get("stamp_at", 0.3), 0.33), rot=-9)


# ------------------------------------------------------------------ $4.8B counter + server racks
def v_counter(c, lt, d, p):
    bg(c, glow=(CX, 560, 700, GREEN, 0.08))
    k = ease_out(prog(lt, 0.05, 1.5))
    val = 4.8 * k
    draw_text(c, "AT LEAST", CX, 330, font("mono", 36), MUTED, 1, align="center")
    draw_text(c, f"${val:0.1f}B", CX, 540, font("disp", 230), GREEN, 1, align="center")
    # server racks stacking in
    n = 12
    for i in range(n):
        ti = prog(lt, 0.1 + i * 0.09, 0.3)
        if ti <= 0:
            continue
        col_i, row = i % 6, i // 6
        x = SAFE_X0 + 15 + col_i * 146
        y = 640 + row * 210 - (1 - ease_out(ti)) * 120
        a = ease_out(ti)
        rrect(c, x, y, 124, 190, 8, (0.13, 0.14, 0.16), a)
        rrect(c, x, y, 124, 190, 8, (0.3, 0.32, 0.35), a, stroke=2)
        for u in range(6):
            c.drawRect(skia.Rect.MakeXYWH(x + 12, y + 14 + u * 29, 100, 20), paint((0.07, 0.07, 0.08), a))
            c.drawCircle(x + 100, y + 24 + u * 29, 3.5, paint(GREEN if (u + i) % 3 else AMBER, a))
    src_tag(c, "Jun 2024 – Feb 2026 · trade records cited by The New York Times", ease_out(prog(lt, 0.6, 0.4)))


# ------------------------------------------------------------------ letter / email card with typed quote
def v_letter(c, lt, d, p):
    bg(c, glow=(CX, 640, 700, (0.9, 0.85, 0.7), 0.05))
    c.save(); push(c, lt, d, 0.03)
    e = enter(c, lt, 0.3, 50) if p.get("enter", True) else 1
    x0, y0, w, h = SAFE_X0, 280, COL_W, 760
    rrect(c, x0 + 10, y0 + 16, w, h, 8, (0, 0, 0), 0.5 * e, blur=22)
    rrect(c, x0, y0, w, h, 8, PAPER, e)
    fm = font("monor", 28)
    for i, (k_, v_) in enumerate([("From:", "Jensen Huang"), ("To:", "NVIDIA employees"), ("Date:", "Nov 8, 2026")]):
        draw_text(c, k_, x0 + 50, y0 + 80 + i * 44, fm, (0.4, 0.4, 0.42), e)
        draw_text(c, v_, x0 + 170, y0 + 80 + i * 44, fm, PAPER_INK, e)
    c.drawRect(skia.Rect.MakeXYWH(x0 + 50, y0 + 200, w - 100, 2), paint((0.6, 0.6, 0.6), e))
    q = "“I was unfaithful to my wife.”"
    t0, t1 = p.get("type_from", 0), p.get("type_to", 0)
    n = len(q) if p.get("typed", False) else int(len(q) * clamp((lt - t0) / max(t1 - t0, 0.01)))
    fq = font("serif", 60)
    shown = q[:n]
    lines = wrap(q, fq, w - 100)
    y, used = y0 + 320, 0
    for ln in lines:
        part = shown[used:used + len(ln)]
        draw_text(c, part, x0 + 50, y, fq, PAPER_INK, e)
        if 0 < n < len(q) and used <= n <= used + len(ln):
            cx_ = x0 + 50 + text_w(part, fq) + 4
            if int(lt * 4) % 2 == 0:
                c.drawRect(skia.Rect.MakeXYWH(cx_, y - 50, 5, 60), paint(PAPER_INK, e))
        used += len(ln) + 1; y += 76
    draw_text(c, "— Jensen Huang, email to employees (excerpt)", x0 + 50, y0 + h - 60, font("monor", 24),
              (0.38, 0.38, 0.4), e, max_w=w - 100)
    c.restore()
    if p.get("note"):
        k = ease_back(prog(lt, p.get("note_at", 0.1), 0.35))
        if k > 0:
            c.save(); c.translate(CX, 860); c.scale(k, k)
            pill(c, p["note"], 0, -30, font("mono", 34), INK, (0.18, 0.2, 0.23), 1, pad=(26, 16), align="center")
            c.restore()


# ------------------------------------------------------------------ board quote with progressive highlight
BOARD_Q = ("“has no reason to believe that either national security or NVIDIA secrets were compromised”")


def v_boardquote(c, lt, d, p):
    bg(c, glow=(CX, 640, 700, GREEN, 0.07))
    c.save(); push(c, lt + p.get("t_off", 0), p.get("push_d", d), 0.05)
    e = enter(c, lt, 0.3, 50) if p.get("enter", True) else 1
    kicker(c, "NVIDIA BOARD STATEMENT · NOV 8, 2026", 360, GREEN, e)
    f = font("xbold", 74)
    lines = wrap(BOARD_Q, f, COL_W)
    y = 480
    hl = p.get("hl", [])
    for ln in lines:
        x = SAFE_X0
        for wd in ln.split():
            ww = text_w(wd + " ", f)
            key = wd.strip("“”.,").lower()
            on = key in hl
            if on:
                c.drawRect(skia.Rect.MakeXYWH(x - 4, y - 62, text_w(wd, f) + 8, 78), paint(GREEN, 0.9 * e))
            draw_text(c, wd, x, y, f, BG if on else INK, e)
            x += ww
        y += 92
    c.restore()
    draw_text(c, "Board's inquiry \"will examine all available information\"", CX, 1405, font("monor", 26), MUTED,
              0.9, align="center", max_w=COL_W)


# ------------------------------------------------------------------ board investigation diagram
def v_board(c, lt, d, p):
    bg(c, glow=(CX, 640, 700, GREEN, 0.06))
    c.save(); push(c, lt, d, 0.03)
    e1 = ease_out(prog(lt, 0.0, 0.3)); e2 = ease_out(prog(lt, 0.35, 0.35)); e3 = ease_out(prog(lt, 0.7, 0.35))
    rrect(c, SAFE_X0 + 120, 280, COL_W - 240, 150, 18, PANEL, e1)
    rrect(c, SAFE_X0 + 120, 280, COL_W - 240, 150, 18, GREEN, e1, stroke=3)
    draw_text(c, "NVIDIA BOARD", CX, 375, font("disp", 64), INK, e1, align="center")
    c.drawRect(skia.Rect.MakeXYWH(CX - 3, 430, 6, 120 * e2), paint(GREEN, e2))
    tri = skia.Path(); tri.moveTo(CX - 22, 545); tri.lineTo(CX + 22, 545); tri.lineTo(CX, 575); tri.close()
    c.drawPath(tri, paint(GREEN, e2))
    rrect(c, SAFE_X0, 590, COL_W, 170, 18, GREEN, e2)
    draw_text(c, "INDEPENDENT", CX, 665, font("disp", 64), BG, e2, align="center")
    draw_text(c, "INVESTIGATION", CX, 735, font("disp", 64), BG, e2, align="center")
    for i, s in enumerate(["Committee of independent directors", "Assisted by outside counsel"]):
        ei = ease_out(prog(lt, 0.7 + 0.2 * i, 0.3))
        pill(c, s, CX, 820 + i * 86, font("mono", 30), INK, PANEL, ei, pad=(22, 14), align="center")
    c.restore()
    src_tag(c, "Source: Nvidia board statement, Nov 8, 2026")


# ------------------------------------------------------------------ probe status table
def v_status(c, lt, d, p):
    bg(c, glow=(CX, 640, 700, AMBER, 0.05))
    c.save(); push(c, lt, d, 0.03)
    kicker(c, p.get("kicker", "WHERE THE PROBES STAND"), 330, AMBER, ease_out(prog(lt, 0, 0.3)))
    y = 400
    for i, (k_, v_, colr) in enumerate(p["rows"]):
        ei = ease_out(prog(lt, 0.1 + 0.2 * i, 0.3))
        c.save(); c.translate((1 - ei) * -60, 0)
        rrect(c, SAFE_X0, y, COL_W, 150, 16, PANEL, ei)
        rrect(c, SAFE_X0, y, 10, 150, 4, colr, ei)
        draw_text(c, k_, SAFE_X0 + 40, y + 62, font("bold", 40), INK, ei, max_w=COL_W - 80)
        draw_text(c, v_, SAFE_X0 + 40, y + 118, font("med", 32), colr, ei, max_w=COL_W - 80)
        c.restore()
        y += 172
    c.restore()


# ------------------------------------------------------------------ leadership chart
def v_orgchart(c, lt, d, p):
    bg(c, glow=(CX, 640, 700, GREEN, 0.06))
    c.save(); push(c, lt, d, 0.03)
    rows = [("PRESIDENT & CEO", "Jen-Hsun Huang", "resignation accepted Nov 11, 2026", MUTED, True),
            ("INTERIM CEO", "Colette Kress", "remains Chief Financial Officer", GREEN, False),
            ("CHAIR OF THE BOARD", "Harvey C. Jones", "first-ever board Chair", GREEN, False)]
    y = 300
    for i, (role, name, sub, colr, strike) in enumerate(rows):
        ei = ease_out(prog(lt, 0.05 + 0.25 * i, 0.32))
        c.save(); c.translate(0, (1 - ei) * 50)
        rrect(c, SAFE_X0, y, COL_W, 200, 18, PANEL, ei)
        rrect(c, SAFE_X0, y, COL_W, 200, 18, colr, ei * (0.5 if strike else 1), stroke=3)
        draw_text(c, role, SAFE_X0 + 40, y + 55, font("mono", 28), colr, ei)
        nf = font("disp", 66)
        draw_text(c, name, SAFE_X0 + 40, y + 128, nf, INK if not strike else MUTED, ei)
        if strike:
            c.drawRect(skia.Rect.MakeXYWH(SAFE_X0 + 36, y + 104, text_w(name, nf) + 8, 6), paint(RED, ei))
        draw_text(c, sub, SAFE_X0 + 40, y + 177, font("med", 30), MUTED, ei)
        c.restore()
        y += 228
    c.restore()
    src_tag(c, "Source: Nvidia Form 8-K and press release, Nov 12, 2026")


# ------------------------------------------------------------------ alleged vs proven
def v_alleged(c, lt, d, p):
    bg(c)
    e1 = ease_out(prog(lt, 0, 0.3)); e2 = ease_out(prog(lt, 0.45, 0.3))
    hw = COL_W / 2 - 12
    for j, (ttl, colr, items, e) in enumerate([
            ("ALLEGED", AMBER, ["Intelligence-asset claim", "Anonymous U.S. officials, via NYT", "Chip-diversion suspicions"], e1),
            ("PROVEN", GREEN, ["None so far", "No charges reported", "Board: no reason to believe secrets were compromised"], e2)]):
        x = SAFE_X0 + j * (hw + 24)
        c.save(); c.translate(0, (1 - e) * 60)
        rrect(c, x, 280, hw, 760, 20, PANEL, e)
        rrect(c, x, 280, hw, 12, 6, colr, e)
        draw_text(c, ttl, x + hw / 2, 400, font("disp", 70), colr, e, align="center", max_w=hw - 40)
        y = 500
        for s in items:
            y = draw_para(c, s, x + 30, y, font("semi", 36), hw - 60, 1.2, INK, e) + 40
        c.restore()
    k = ease_back(prog(lt, 0.9, 0.35))
    if k > 0:
        c.save(); c.translate(CX, 1000); c.scale(k, k)
        pill(c, "Nvidia, Megaspeed and China deny wrongdoing", 0, -30, font("mono", 28), INK, RED, 1, pad=(22, 14), align="center")
        c.restore()


# ------------------------------------------------------------------ what to watch (calendar)
def v_watch(c, lt, d, p):
    bg(c, glow=(CX, 640, 700, GREEN, 0.06))
    kicker(c, "WHAT TO WATCH", 320, GREEN, ease_out(prog(lt, 0, 0.3)))
    cards = p["cards"]
    for i, (mon, day, title, sub, active) in enumerate(cards):
        ei = ease_out(prog(lt, p.get("delay", 0) + 0.18 * i, 0.32))
        y = 400 + i * 300
        a = ei * (1 if active else 0.35)
        c.save(); c.translate((1 - ei) * 80, 0)
        rrect(c, SAFE_X0, y, COL_W, 260, 20, PANEL, a)
        rrect(c, SAFE_X0, y, 210, 260, 20, GREEN if active else (0.3, 0.32, 0.35), a)
        draw_text(c, mon, SAFE_X0 + 105, y + 80, font("mono", 38), BG, a, align="center")
        draw_text(c, day, SAFE_X0 + 105, y + 200, font("disp", 110), BG, a, align="center")
        draw_text(c, title, SAFE_X0 + 245, y + 115, font("xbold", 50), INK, a, max_w=COL_W - 280)
        draw_text(c, sub, SAFE_X0 + 245, y + 175, font("med", 32), MUTED, a, max_w=COL_W - 280)
        c.restore()


# ------------------------------------------------------------------ end card
def v_end(c, lt, d, p):
    bg(c)
    e = ease_out(prog(lt, 0, 0.35))
    draw_text(c, "AS OF NOV 14, 2026", SAFE_X0, 300, font("mono", 40), GREEN, e)
    draw_para(c, "Allegations are unproven. Nvidia, Megaspeed and China deny wrongdoing. Story developing.",
              SAFE_X0, 380, font("xbold", 50), COL_W, 1.18, INK, e)
    y = 640
    draw_text(c, "SOURCES", SAFE_X0, y, font("mono", 28), MUTED, e); y += 50
    y = draw_para(c, "Nvidia SEC Form 8-K · Nvidia board statement · Singapore MHA · U.S. House committee letter · "
                     "The New York Times · CNBC · NBC News · CBS News · CNN · SCMP · Fortune · TechCrunch",
                  SAFE_X0, y, font("med", 32), COL_W, 1.3, INK, e) + 30
    draw_text(c, "IMAGES & DATA", SAFE_X0, y, font("mono", 28), MUTED, e); y += 50
    y = draw_para(c, "U.S. Capitol west front — Architect of the Capitol (public domain) · Marina Bay Sands — "
                     "Someformofhuman, CC BY-SA 3.0, via Wikimedia Commons · Map data: Natural Earth (public domain)",
                  SAFE_X0, y, font("med", 28), COL_W, 1.3, INK, e) + 30
    draw_para(c, "AI-generated narration and graphics. Full source links in the description.",
              SAFE_X0, y, font("med", 28), COL_W, 1.3, MUTED, e)
