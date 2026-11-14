"""v2 shot plan: word-anchored tracks for comp.py, plus storyboard2.json.

Rules encoded here (see research/ledger.md):
- Huang photos only on Nvidia/tenure, admission, resignation and testimony beats; never near the Alice Huang,
  "intelligence" or "close relationship" lines.
- The NYT Oct 29 headline ("...Spy Plot") is only shown over B-roll, never over a photo of a person.
- Silhouette card for Alice Huang; no image of her.
"""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A2 = os.path.join(ROOT, "assets2")
WJ = json.load(open(os.path.join(ROOT, "build", "words2.json")))
WORDS, DUR = WJ["words"], WJ["duration"]


SHIFT = [(334, 2)]   # words inserted after anchors were authored ("CNBC reported" before old word 334)


def W(i):
    for at, n in SHIFT:
        if i >= at:
            i += n
    return i


def ws(i):
    return WORDS[W(i)]["s"]


# ------------------------------------------------------------------ asset pools
def load_pools():
    pools = {}
    com = json.load(open(os.path.join(A2, "commons.json")))
    rv = json.load(open(os.path.join(A2, "review.json"))) if os.path.exists(os.path.join(A2, "review.json")) else {}
    for k, v in com.items():
        if k in rv:
            v.update(rv[k])
    nasa = json.load(open(os.path.join(A2, "nasa.json")))
    vcat = {  # Commons video query -> pool
        "Singapore skyline": "sg", "Marina Bay Singapore": "sg", "Singapore timelapse": "sg", "Singapore night": "sg",
        "Kuala Lumpur skyline": "kl", "Petronas Towers": "kl", "Kuala Lumpur night": "kl",
        "container terminal": "port", "Port of Singapore": "port", "container ship": "port",
        "United States Capitol": "capitol", "Capitol Hill Washington": "capitol", "Washington D.C. timelapse": "capitol",
        "stock exchange": "market", "stock ticker": "market", "rain drops window": "rain", "rain city night": "rain",
        "skyscraper glass": "tower", "office building timelapse": "tower", "data center": "dc", "server room": "dc",
        "printed circuit board": "chip", "silicon wafer": "chip", "semiconductor fabrication": "chip",
        "keyboard typing": "typing", "newspaper printing": "news", "city lights timelapse": "night",
        "highway night timelapse": "night", "Santa Clara California": "tower"}
    pcat = {"singapore": "sg", "kl": "kl", "datacenter": "dc", "gpu": "chip", "wafer": "chip", "cleanroom": "chip",
            "port": "port", "capitol": "capitol", "hearing": "capitol", "nvidia_hq": "tower", "ticker": "market",
            "tower": "tower", "rain": "rain", "huang": "huang"}
    for k, v in com.items():
        if v.get("rejected"):
            continue
        if v["kind"] == "video" and not v.get("reviewed"):      # every video is checked by eye before use
            continue
        if v["kind"] == "video":
            pools.setdefault(vcat.get(v["cat"], "dc") if k != "commons_dc_aisle" else "dc", []).append(
                {"id": k, "kind": "video", "file": v["file"], "clip_starts": v.get("clip_starts")})
        else:
            pools.setdefault("photo_" + pcat.get(v["cat"], "misc"), []).append({"id": k, "kind": "photo", "file": v["file"]})
    for k, v in nasa.items():
        v = {**v, **rv.get(k, {})}
        pools.setdefault("globe" if "globe" in k else ("chip" if "board" in k else "dc"), []).append({"id": k, "kind": "video", "file": v["file"], "clip_starts": v.get("clip_starts")})
    if "sg" in pools:   # daytime drone shots first; the night skyline (large black sky) last
        order = {"vid_03": 0, "vid_04": 1, "vid_02": 2, "vid_01": 3}
        pools["sg"].sort(key=lambda a: order.get(a["id"], 9))
    if "port" in pools:
        pools["port"].sort(key=lambda a: a["id"] != "vid_06")
    if "dc" in pools:   # open on the brighter NASA rack footage; the dark aisle clip goes last
        pools["dc"].sort(key=lambda a: (a["id"] == "commons_dc_aisle", a["id"] != "nasa_racks"))
    pools.setdefault("photo_capitol", []).append({"id": "v1_capitol", "kind": "photo", "file": "assets/commons/capitol.jpg", "crop": [300, 80, 1300, 600]})
    pools.setdefault("photo_sg", []).append({"id": "v1_singapore", "kind": "photo", "file": "assets/commons/singapore.jpg", "crop": [0, 330, 1920, 950]})
    return pools


POOLS = load_pools()
FALLBACK = {"sg": ["photo_sg", "night", "tower"], "kl": ["photo_kl", "night", "tower", "sg"], "port": ["photo_port", "night", "dc"],
            "capitol": ["photo_capitol"], "market": ["photo_market", "tower", "night", "dc"], "rain": ["photo_rain", "night", "tower"],
            "tower": ["photo_tower", "night", "dc"], "night": ["photo_sg", "tower", "dc"], "chip": ["photo_chip", "dc"],
            "dc": ["photo_dc"], "globe": ["night", "dc"], "typing": ["dc"], "news": ["tower"]}
_USE = {}


def pick(cat):
    """Rotate through a pool (with fallbacks) so consecutive segments differ."""
    for c in [cat] + FALLBACK.get(cat, []) + ["dc"]:
        if POOLS.get(c):
            n = _USE.get(c, 0); _USE[c] = n + 1
            a = dict(POOLS[c][n % len(POOLS[c])])
            rep = n // len(POOLS[c])
            cs = a.pop("clip_starts", None)
            a["clip_start"] = cs[rep % len(cs)] if cs else 1.5 + 3.7 * rep      # reviewed clean segments only
            a["pool"] = c
            return a
    raise RuntimeError("no assets")


HUANG_OK = {  # 9:16 crops centred on Huang's face (x, y, w, h in source px); audience excluded; brightest first
    "huang_03": [0, 0, 1307, 2324], "huang_01": [183, 0, 1440, 2560], "huang_06": [216, 0, 1404, 2497],
    "huang_11": [240, 0, 1440, 2560], "huang_12": [597, 0, 720, 1280], "huang_13": [627, 0, 480, 854],
    "huang_15": [606, 0, 480, 854], "huang_16": [424, 0, 480, 854], "huang_14": [440, 0, 607, 1080]}


def huang(i):
    keys = [k for k in HUANG_OK if os.path.exists(os.path.join(A2, "photos", k + ".jpg"))]
    k = keys[i % len(keys)]
    return {"id": k, "kind": "photo", "file": f"assets2/photos/{k}.jpg", "crop": HUANG_OK[k], "pool": "huang"}


# ------------------------------------------------------------------ BG timeline: (start word, pool or asset, extra)
BG = [
    (0, "dc"), (6, "dc"), (11, ("huang", 0), {"desat": 0.75}), (19, ("huang", 1), {"desat": 0.75}), (24, "chip"), (31, "dc"), (38, "chip"),
    (43, "sg"), (48, "sg"), (56, "night"), (62, "kl"), (67, "chip"), (75, "dc"),
    (79, "port"), (86, "chip"), (93, "photo_sg"), (99, "night"), (105, "tower"), (111, "rain"), (116, "tower"),
    (122, "night"), (129, "dc"), (133, "night", {"dim": 0.25}), (142, "rain"), (147, "tower"), (152, "night"),
    (157, "tower"), (165, "dc"), (172, "rain"), (181, "night"), (188, "tower"),
    (194, "tower"), (200, "rain"), (204, "night", {"dim": 0.15}), (212, ("huang", 2), {"desat": 0.5}), (216, "tower"), (222, "rain"),
    (227, "night"), (233, "tower"), (238, "tower"), (242, "dc"), (250, "chip"), (257, "tower"), (264, "rain"),
    (270, "dc"), (277, "tower"),
    (285, "dc"), (291, "night"), (300, "dc"), (305, "tower"), (309, ("huang", 3), {"desat": 0.6}), (314, "tower"), (318, "rain"),
    (322, "tower"), (327, "night"), (331, "market"), (336, "market"), (342, "night"), (348, "market"), (354, "tower"), (360, "night"),
    (367, "capitol"), (374, "capitol"), (379, "capitol"), (384, "capitol"), (390, ("huang", 4), {"desat": 0.4}), (395, "capitol"), (399, "capitol"), (403, "capitol"),
    (407, "port", {"dim": 0.3}), (411, "night", {"dim": 0.3}), (415, "dc"), (419, "market"), (424, "tower"), (427, "capitol"),
]

# ------------------------------------------------------------------ FRONT groups: (start word, transition, [(cut, at word, opts)])
FRONT = [
    (0, None, [("8k_cover", 1, {"zoom": 1.0, "w": 0.92}), ("8k_resign", 5, {"zoom": 2.4, "rot": -1.5, "w": 0.94})]),
    (11, "flash", []),                                       # clear documents: full-bleed Huang photo (tenure)
    (24, "whip", [("8k_cover", 25, {"zoom": 1.25, "w": 0.9}),
                  ("ex991_top", 33, {"zoom": 1.0, "w": 0.9, "stamp": "CONFIRMED", "stamp_color": "green"}),
                  ("hl_cbs_investigation", 37, {"zoom": 1.0, "w": 0.88, "rot": 2.0, "stamp": "REPORTED", "stamp_color": "amber"}),
                  ("hl_nyt_1029", 41, {"zoom": 1.0, "w": 0.86, "rot": -2.0, "stamp": "ALLEGED", "stamp_color": "amber"})]),
    (43, "flash", [("hl_cbs_megaspeed", 47, {"zoom": 1.5}), ("hl_nyt_2025", 56, {"zoom": 1.5, "rot": 1.5}),
                   ("cbs_48", 66, {"zoom": 1.9, "rot": -1.0})]),
    (79, "whip", [("__stamp__", 83, {"stamp": "ALLEGED", "stamp_color": "amber"})]),
    (93, "zoom", []),
    (105, "slide", [("hl_nbc_megaspeed", 105, {"zoom": 1.6, "stamp": "DENIED", "stamp_at_word": 106})]),
    (122, "whip", [("hl_nyt_1029", 123, {"zoom": 1.6, "w": 0.92}), ("hl_cbs_investigation", 129, {"zoom": 1.5, "rot": 1.8})]),
    (133, "flash", []),                                      # silhouette card (CARDS)
    (142, "zoom", [("hl_cbs_investigation", 142, {"zoom": 1.7, "rot": -1.2})]),
    (147, "whip", []),
    (157, "slide", [("tc_notunusual", 158, {"zoom": 1.9, "stamp": "DENIED", "stamp_at_word": 166}),
                    ("mfa_answer", 181, {"zoom": 1.6, "rot": 1.5, "stamp": "DENIED", "stamp_at_word": 187}),
                    ("hl_nbc_megaspeed", 189, {"zoom": 1.0, "rot": -2.0, "w": 0.86, "stamp": "DENIED", "stamp_at_word": 190})]),
    (194, "whip", [("nv_msg_title", 197, {"zoom": 1.3}), ("nv_msg_quote", 204, {"zoom": 1.0, "w": 0.84})]),
    (212, "flash", []),
    (216, "cut", [("nv_msg_natsec", 217, {"zoom": 1.7})]),
    (233, "slide", [("nv_board_title", 235, {"zoom": 1.2}), ("nv_board_inv", 239, {"zoom": 1.6, "rot": 1.2}),
                    ("nv_board_noreason", 245, {"zoom": 1.8, "rot": -1.0})]),
    (257, "flash", [("cbs_pledge", 258, {"zoom": 1.8})]),
    (270, "whip", [("nv_indep", 276, {"zoom": 2.2, "w": 0.9})]),
    (285, "cut", [("tc_doj", 289, {"zoom": 1.8})]),
    (300, "whip", [("hl_tc_resigns", 301, {"zoom": 1.3, "rot": -1.5, "w": 0.88}), ("8k_resign", 310, {"zoom": 2.4, "rot": 1.2, "w": 0.94})]),
    (314, "slide", [("8k_kress", 316, {"zoom": 2.5, "w": 0.94, "pos": (540, 700)}), ("8k_kress_role", 319, {"zoom": 2.5, "w": 0.94, "pos": (540, 700)}),
                    ("8k_jones", 324, {"zoom": 2.5, "rot": 1.0, "w": 0.94, "pos": (540, 980)})]),
    (331, "flash", [("hl_yahoo_1112", 332, {"zoom": 1.4}), ("yahoo_close", 342, {"zoom": 1.9, "rot": -1.0}),
                    ("hl_nyt_wallst", 350, {"zoom": 1.4, "rot": 1.5})]),
    (367, "whip", [("house_letter_top", 368, {"zoom": 1.9, "w": 0.9}), ("house_letter_date", 377, {"zoom": 2.0, "rot": 1.0})]),
    (384, "slide", [("hl_tc_testify", 385, {"zoom": 2.0})]),
    (399, "cut", []),
    (407, "flash", []),                                      # alleged-vs-proven summary (CARDS)
    (415, "whip", [("nv_earnings", 419, {"zoom": 1.9}), ("nv_indep", 424, {"zoom": 1.0, "rot": 1.5, "w": 0.86}),
                   ("hl_tc_testify", 428, {"zoom": 1.0, "rot": -1.5, "w": 0.9})]),
]
MID = [  # printed photo cards (Huang only on allowed beats)
    (26, 31, ("huang", 5), {"pos": (300, 1300), "w": 420, "rot": -4, "from_x": -900}),
    (322, 331, ("huang", 6), {"pos": (760, 1330), "w": 420, "rot": 3.5, "from_x": 900}),
    (399, 407, ("huang", 7), {"pos": (540, 760), "w": 640, "rot": -3, "from_x": -900}),
]
CARDS = [("silhouette", 133, 142), ("summary", 407, 415)]
LABELS = [(79, 93, "ALLEGATIONS · UNDER INVESTIGATION"), (122, 157, "ALLEGATIONS · UNDER INVESTIGATION")]
SENTENCES = [(0, ["B6a"]), (11, ["N10"]), (24, ["B6a"]), (29, []), (43, ["B1a"]), (56, ["B2a"]), (79, ["N5"]), (93, ["B2c"]),
             (105, ["B2b", "N9"]), (122, ["B3a", "B3e"]), (147, ["B3a"]), (157, ["B3b"]), (181, ["B3c"]), (194, ["B4a"]),
             (204, ["B4a"]), (212, ["B4b"]), (233, ["B4c"]), (242, ["B4d"]), (257, ["N6"]), (270, ["B5a"]), (285, ["B5b"]),
             (300, ["B6a", "N6"]), (314, ["B6b"]), (322, ["B6c"]), (331, ["N8"]), (348, ["N8"]), (367, ["B7a"]),
             (384, ["B7b", "B7c"]), (399, ["B7e"]), (407, ["B3a", "B5b"]), (415, ["N3", "B4c", "B5a", "B7c"])]

# ------------------------------------------------------------------ captions
SEQ = [  # token sequences -> one caption
    (["nineteen", "ninety-three"], "1993", "green"), (["thirty-three"], "33 YEARS", "green"),
    (["four", "point", "eight", "billion", "dollars"], "$4.8 BILLION", "green"), (["june", "twenty", "twenty-four"], "JUNE 2024", "green"),
    (["october", "twenty-ninth"], "OCT. 29", "green"), (["november", "eleventh"], "NOV. 11", "green"),
    (["november", "eighth"], "NOV. 8", "green"), (["november", "twelfth"], "NOV. 12", "green"),
    (["november", "fourth"], "NOV. 4", "green"), (["november", "seventeenth"], "NOV. 17", "green"),
    (["four", "trillion", "dollars"], "$4 TRILLION", "green"), (["july", "twenty", "twenty-five"], "JULY 2025", "green"),
    (["fourteen", "percent"], "14%", "red"), (["four", "percent"], "4%", "red"), (["new", "york", "times"], "NEW YORK TIMES", "green"),
    (["wachtell", "lipton"], "WACHTELL LIPTON", "green"),
]
TEXT = {"c-e-o": "CEO", "c-e-o's": "CEO'S", "c-e-o.": "CEO."}
QUOTE_OPEN = {(204, "i"), (114, "extremely"), (166, "not"), (187, "unsubstantiated"), (189, "nothing")}
QUOTE_CLOSE = {(209, "wife"), (115, "seriously"), (169, "unexpected"), (187, "unsubstantiated"), (193, "china")}
GREEN = {"jensen", "huang", "huang's", "nvidia", "nvidia's", "megaspeed", "megaspeed's", "alice", "colette", "kress", "harvey",
         "jones", "resignation", "december", "proven", "confirmed", "reported", "alleged"}
RED = {"denies", "unsubstantiated", "smears", "not", "unusual", "unexpected", "none"}
GLITCH = {"intelligence", "investigation", "investigating"}


def captions():
    ev, i = [], 0
    low = [w["w"].lower().strip(".,\"") for w in WORDS]
    while i < len(WORDS):
        hit = None
        for seq, txt, sty in SEQ:
            if low[i:i + len(seq)] == seq:
                hit = (len(seq), txt, sty); break
        if hit:
            n, txt, sty = hit
        else:
            n, raw = 1, WORDS[i]["w"]
            txt = TEXT.get(raw.lower(), raw.upper())
            sty = "green" if low[i] in GREEN else "red" if low[i] in RED else None
            if (i, low[i]) in QUOTE_OPEN:
                txt = "“" + txt
            if (i, low[i]) in QUOTE_CLOSE:
                txt = txt.rstrip(".") + ".”"
        ev.append({"s": WORDS[i]["s"], "e": WORDS[i + n - 1]["e"], "text": txt, "style": sty, "words": [i, i + n - 1]})
        i += n
    for a, b in zip(ev, ev[1:]):
        a["hide"] = b["s"] if b["s"] - a["e"] < 0.35 else a["e"] + 0.15
    ev[-1]["hide"] = ev[-1]["e"] + 0.3
    return ev


def build():
    end_t = WORDS[-1]["e"] + 0.4
    bg = []
    for j, row in enumerate(BG):
        w0, src = row[0], row[1]
        extra = row[2] if len(row) > 2 else {}
        a = huang(src[1]) if isinstance(src, tuple) else pick(src)
        a.update(extra)
        a["start"] = 0.0 if j == 0 else round(ws(w0) - 0.05, 3)
        a["drift"] = [(-1) ** j * 0.8, -0.6 if j % 2 else 0.6]
        bg.append(a)
    for j, a in enumerate(bg):
        a["end"] = bg[j + 1]["start"] if j + 1 < len(bg) else end_t
        if a["kind"] == "video":       # never run past the end of a clip (it would loop back to a title card)
            dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                        os.path.join(ROOT, a["file"])], capture_output=True, text=True).stdout)
            a["clip_start"] = round(max(0.0, min(a.get("clip_start") or 0.0, dur - (a["end"] - a["start"]) - 0.3)), 2)
    front = []
    for j, (w0, tr, items) in enumerate(FRONT):
        g = {"start": 0.0 if j == 0 else round(ws(w0) - 0.05, 3), "trans": tr, "trans_d": {"flash": 2 / 30, "whip": 7 / 30, "zoom": 7 / 30, "slide": 8 / 30}.get(tr, 0),
             "prev": j - 1 if j else None, "items": []}
        n = len([x for x in items if x[0] != "__stamp__"])
        for k, (cut, aw, opt) in enumerate(items):
            it = {"cut": cut, "at": round(ws(aw) - 0.02, 3), **{kk: v for kk, v in opt.items() if kk not in ("stamp_at_word",)}}
            if "pos" not in it and n > 1:
                it["pos"] = (540 + (-1) ** k * 26, 700 + (k - (n - 1) / 2) * 230)
            if "stamp_at_word" in opt:
                it["stamp_at"] = round(ws(opt["stamp_at_word"]) - it["at"], 3)
            g["items"].append(it)
        front.append(g)
    for j, g in enumerate(front):
        g["end"] = front[j + 1]["start"] if j + 1 < len(front) else end_t
        for k, it in enumerate(g["items"]):
            nxt = g["items"][k + 1]["at"] if k + 1 < len(g["items"]) else g["end"]
            it["hold"] = round(nxt - it["at"], 3)
    mid = []
    for w0, w1, src, opt in MID:
        a = huang(src[1]); a.update(opt); a["start"], a["end"] = round(ws(w0), 3), round(ws(w1) - 0.05, 3)
        mid.append(a)
    cards = [{"type": t, "start": round(ws(a) - 0.05, 3), "end": round(ws(b) - 0.05, 3)} for t, a, b in CARDS]
    used = {a["id"] for a in bg} | {m["id"] for m in mid}
    com = json.load(open(os.path.join(A2, "commons.json")))
    cred = []
    for k in sorted(used):
        v = com.get(k)
        if v:
            auth = re.sub(r"\s+", " ", v.get("author") or "unknown").strip()[:40]
            auth = {"總統府": "Office of the President, Taiwan"}.get(auth, auth)
            if not auth.isascii():
                auth = re.sub(r"[^\x00-\x7f]+", "", auth).strip() or "Wikimedia Commons contributor"
            cred.append(f"{auth} ({v.get('license')})")
    if any(k.startswith("nasa_") for k in used):
        cred.append("NASA Ames (public domain)")
    if "v1_capitol" in used:
        cred.append("Architect of the Capitol (PD)")
    if "v1_singapore" in used:
        cred.append("Someformofhuman (CC BY-SA 3.0)")
    sources = ("SEC (Nvidia Form 8-K, Ex. 99.1) · Nvidia newsroom · China MFA transcript · U.S. House committee letter · "
               "The New York Times · CBS News · NBC News · TechCrunch · Fox Business · Yahoo Finance/Motley Fool")
    cards.append({"type": "end", "start": round(end_t, 3), "end": DUR, "sources": sources,
                  "credits": "Wikimedia Commons & NASA: " + "; ".join(dict.fromkeys(cred))})
    labels = [{"start": round(ws(a) - 0.05, 3), "end": round(ws(b) - 0.05, 3), "text": t} for a, b, t in LABELS]
    glitch = sorted({int(round((w["s"] + 0.06) * 30)) for w in WORDS if w["w"].lower().strip(".,") in GLITCH})
    leaks = [{"t": 0.0, "d": 0.9, "side": 0}, {"t": ws(204) - 0.2, "d": 0.8, "side": 1}, {"t": ws(311) - 0.1, "d": 0.8, "side": 0},
             {"t": ws(407) - 0.2, "d": 0.9, "side": 1}]
    plan = {"duration": DUR, "bg": bg, "front": front, "mid": mid, "cards": cards, "labels": labels,
            "captions": captions(), "glitch_frames": glitch, "leaks": leaks}
    return plan


def storyboard(plan):
    """One storyboard beat per background segment, with the layers active in it."""
    beats = []
    sent = [(ws(w), ids) for w, ids in SENTENCES]
    for j, b in enumerate(plan["bg"]):
        st, en = b["start"], b["end"]
        nw = [w["w"] for w in WORDS if st <= w["s"] < en]
        ids = sorted({i for t, idl in sent for i in idl if t < en} & {i for t, idl in sent if t <= max(st, 0) or t < en for i in idl}
                     if False else {i for (t, idl), nxt in zip(sent, sent[1:] + [(1e9, [])]) if t < en and nxt[0] > st for i in idl})
        layers = []
        for g in plan["front"]:
            for it in g["items"]:
                if st - 0.01 <= it["at"] < en:
                    layers.append(f"FRONT {it['cut']} (slam at {it['at']:.2f}s" + (f", zoom {it.get('zoom', 1.8)}x" if it.get("zoom", 1.8) > 1.01 else "") + ")")
        for m in plan["mid"]:
            if m["start"] < en and m["end"] > st:
                layers.append(f"MID printed card {m['id']}")
        for c in plan["cards"]:
            if c["start"] < en and c["end"] > st:
                layers.append(f"CARD {c['type']}")
        g0 = next((g for g in plan["front"] if abs(g["start"] - st) < 0.06), None)
        lab = next((l["text"] for l in plan["labels"] if l["start"] < en and l["end"] > st), None)
        sfx = []
        if g0 and g0["trans"] in ("whip", "slide", "zoom"):
            sfx.append({"sfx": "whoosh", "t": st})
        beats.append({"id": f"s{j + 1:02d}", "start": round(st, 3), "end": round(en, 3), "narration_words": " ".join(nw),
                      "caption_emphasis": [c["text"] for c in plan["captions"] if c["style"] and st <= c["s"] < en],
                      "visual_type": "BG " + ("video" if b["kind"] == "video" else "photo") + (" + " + "; ".join(layers) if layers else ""),
                      "asset_path_or_spec": {"back": b["file"], "back_id": b["id"], "clip_start": b.get("clip_start"), "crop": b.get("crop"),
                                             "desat": b.get("desat")},
                      "motion": "slow push 4.5% + drift; mid 1.5x / front 2x parallax" + (f"; transition in: {g0['trans']}" if g0 and g0["trans"] else ""),
                      "overlay": lab, "sfx": sfx, "ledger_ids": ids})
    return beats


if __name__ == "__main__":
    p = build()
    json.dump(p, open(os.path.join(ROOT, "build", "plan2.json"), "w"), indent=1)
    sb = storyboard(p)
    json.dump({"fps": 30, "size": [1080, 1920], "duration": DUR, "beats": sb}, open(os.path.join(ROOT, "storyboard.json"), "w"), indent=1)
    lens = [b["end"] - b["start"] for b in p["bg"]]
    print("bg segments", len(lens), "min %.2f max %.2f" % (min(lens), max(lens)), "front groups", len(p["front"]),
          "doc slams", sum(len(g["items"]) for g in p["front"]), "pools", {k: len(v) for k, v in POOLS.items()})
    print([round(x, 1) for x in lens])
