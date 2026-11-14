"""Animated map: Singapore -> Johor (Malaysia) -> 'China?' (alleged), from Natural Earth via world-atlas."""
import json, math, os
import skia
from gfx import *
from visuals import ASSET, bg, src_tag

IDS = {"702": "SG", "458": "MY", "156": "CN", "360": "ID", "764": "TH", "704": "VN", "116": "KH",
       "418": "LA", "104": "MM", "608": "PH", "158": "TW", "96": "BN"}
BBOX = (88, -12, 135, 42)
_PATHS = None


def merc_y(lat):
    return -math.degrees(math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))


def _load():
    global _PATHS
    if _PATHS is not None:
        return _PATHS
    topo = json.load(open(ASSET("data", "countries-10m.json")))
    sc, tr = topo["transform"]["scale"], topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0; pts = []
        for dx, dy in arc:
            x += dx; y += dy
            pts.append((x * sc[0] + tr[0], y * sc[1] + tr[1]))
        arcs.append(pts)

    def ring(idx):
        out = []
        for i in idx:
            pts = arcs[i] if i >= 0 else list(reversed(arcs[~i]))
            out.extend(pts if not out else pts[1:])
        return out

    paths = {}
    for g in topo["objects"]["countries"]["geometries"]:
        polys = g.get("arcs", [])
        if g["type"] == "Polygon":
            polys = [polys]
        elif g["type"] != "MultiPolygon":
            continue
        p = skia.Path(); n = 0
        for poly in polys:
            for r in poly:
                pts = ring(r)
                if not pts:
                    continue
                if not any(BBOX[0] <= x <= BBOX[2] and BBOX[1] <= y <= BBOX[3] for x, y in pts[::5] + pts[-1:]):
                    continue
                p.moveTo(pts[0][0], merc_y(pts[0][1]))
                for x, y in pts[1:]:
                    p.lineTo(x, merc_y(y))
                p.close(); n += 1
        if n:
            paths[IDS.get(str(g.get("id")), "x" + str(g.get("id")))] = p
    _PATHS = paths
    return paths


# camera presets: (centre lon, centre lat, px per degree)
CAM_NEAR = (103.6, 2.4, 150.0)
CAM_FAR = (108.0, 12.0, 34.0)


def _cam(lt, p):
    if p.get("stage", 1) == 1:
        a, b, k = CAM_NEAR, CAM_NEAR, 1
    else:
        a, b = CAM_NEAR, CAM_FAR
        k = ease_in_out(prog(lt, 0.0, 0.9))
    lon = a[0] + (b[0] - a[0]) * k
    lat = a[1] + (b[1] - a[1]) * k
    s = math.exp(math.log(a[2]) + (math.log(b[2]) - math.log(a[2])) * k)
    s *= 1 + 0.03 * clamp(lt / 3)          # slow push
    return lon, lat, s


def proj(lon, lat, cam, cx=540, cy=700):
    clon, clat, s = cam
    return cx + (lon - clon) * s, cy + (merc_y(lat) - merc_y(clat)) * s


def pin(c, x, y, colr, lt, a=1):
    r = 14 + 10 * (0.5 + 0.5 * math.sin(lt * 6))
    c.drawCircle(x, y, r + 14, paint(colr, 0.25 * a))
    c.drawCircle(x, y, 14, paint(colr, a))
    c.drawCircle(x, y, 14, paint(BG, a, stroke=4))


def label(c, s, sub, x, y, colr, a, align="left"):
    f1, f2 = font("xbold", 46), font("mono", 28)
    w = max(text_w(s, f1), text_w(sub, f2)) + 44
    if align == "right":
        x -= w
    x = clamp(x, SAFE_X0, SAFE_X1 - w)
    rrect(c, x, y, w, 118, 14, (0.05, 0.06, 0.07), 0.82 * a)
    rrect(c, x, y, 8, 118, 4, colr, a)
    draw_text(c, s, x + 26, y + 52, f1, INK, a)
    draw_text(c, sub, x + 26, y + 96, f2, colr, a)


def v_map(c, lt, d, p):
    bg(c)
    paths = _load()
    cam = _cam(lt, p)
    clon, clat, s = cam
    c.save()
    c.translate(540, 700); c.scale(s, s); c.translate(-clon, -merc_y(clat))
    sea = skia.Paint(AntiAlias=True)
    for code, path in paths.items():
        fill = (0.16, 0.18, 0.20)
        if code == "SG":
            fill = GREEN
        elif code == "MY":
            fill = (0.24, 0.33, 0.16)
        elif code == "CN" and p.get("stage", 1) == 2:
            fill = (0.30, 0.22, 0.12)
        c.drawPath(path, paint(fill))
        c.drawPath(path, paint((0.33, 0.36, 0.38), stroke=1.6 / s))
    c.restore()
    # graticule-ish subtle lines
    for gl in range(90, 140, 5):
        x, _ = proj(gl, 0, cam)
        c.drawRect(skia.Rect.MakeXYWH(x, 0, 1, H), paint(INK, 0.04))

    sg = proj(103.82, 1.35, cam)
    jh = proj(103.40, 2.00, cam)       # Johor state (approx. centroid)
    e1 = ease_out(prog(lt, 0.1, 0.35))
    pin(c, *sg, GREEN, lt, e1)
    if p.get("stage", 1) == 1:
        label(c, "SINGAPORE", "MEGASPEED · HQ", sg[0] + 40, sg[1] + 20, GREEN, e1)
        e2 = ease_out(prog(lt, 0.45, 0.4))
        # curved arrow SG -> Johor
        ctrl = (sg[0] - 160, sg[1] - 60)
        path = skia.Path(); path.moveTo(*sg); path.quadTo(ctrl[0], ctrl[1], jh[0], jh[1])
        pm = skia.PathMeasure(path, False); L = pm.getLength()
        seg = skia.Path(); pm.getSegment(0, L * e2, seg, True)
        c.drawPath(seg, paint(INK, e2, stroke=7, cap_round=True))
        pin(c, *jh, (0.55, 0.75, 0.3), lt, e2)
        label(c, "SPEEDMATRIX", "MALAYSIAN AFFILIATE · JOHOR", jh[0] - 40, jh[1] - 190, (0.55, 0.75, 0.3), e2, align="right")
    else:
        pin(c, *jh, (0.55, 0.75, 0.3), lt, 1)
        cn = proj(113.0, 22.6, cam)
        e3 = ease_out(prog(lt, 0.85, 0.7))
        ctrl = (jh[0] + 260, jh[1] - 380)
        path = skia.Path(); path.moveTo(*jh); path.quadTo(ctrl[0], ctrl[1], cn[0], cn[1])
        pm = skia.PathMeasure(path, False); L = pm.getLength()
        seg = skia.Path(); pm.getSegment(0, L * e3, seg, True)
        dp = paint(AMBER, 1, stroke=7, cap_round=True)
        dp.setPathEffect(skia.DashPathEffect.Make([26, 22], -lt * 60))
        c.drawPath(seg, dp)
        e4 = ease_out(prog(lt, 1.3, 0.35))
        label(c, "CHINA?", "ALLEGED · UNDER U.S. INVESTIGATION", cn[0] - 70, cn[1] + 20, AMBER, e4, align="right")
        e5 = ease_out(prog(lt, 0.3, 0.35))
        label(c, "SINGAPORE POLICE", "INVESTIGATION ONGOING", SAFE_X0, 870, GREEN, e5)
    src_tag(c, "Map: Natural Earth · locations approximate", 0.8)
