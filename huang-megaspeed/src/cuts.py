"""Crop real page screenshots into document/headline 'cuts' (no redrawing, no edits).

Every cut is a rectangle of a real screenshot (CSS px; screenshots are DSF 2).
Crops exclude news photos (Getty/AP/Reuters/Bloomberg/TV stills), any face, and
lines that mention people we must not name or show. `focus` is the quoted phrase box
used for the zoom target and the highlighter swipe (page CSS coords).
Writes assets2/cuts/<id>.png and assets2/cuts.json.
"""
import json, os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "assets2")
S = json.load(open(os.path.join(A, "shots.json")))


def h1(k):
    return S[k].get("h1") or {}


def ph(k, p, i=0):
    return S[k]["phrases"][p][i]


def union(*rects):
    x0 = min(r[0] for r in rects); y0 = min(r[1] for r in rects)
    x1 = max(r[0] + r[2] for r in rects); y1 = max(r[1] + r[3] for r in rects)
    return [x0, y0, x1 - x0, y1 - y0]


CUTS = []


def cut(cid, src, rect, focus=None, outlet="", date="", url="", kind="doc", note=""):
    CUTS.append(dict(id=cid, src=src, rect=[round(v) for v in rect], focus=[round(v) for v in focus] if focus else None,
                     outlet=outlet, date=date, url=url or S.get(src.split("/")[-1].replace("_full.png", ""), {}).get("url", ""),
                     kind=kind, note=note))


D, Hd = "docs/", "headlines/"
# --- SEC 8-K and Exhibit 99.1 (real sec.gov pages)
cut("8k_cover", D + "sec_8k_full.png", [0, 0, 900, 420], None, "SEC / Nvidia Form 8-K", "Nov 12, 2026")
p1 = ph("sec_8k", "accepted the resignation of Jen-Hsun Huang"); p2 = ph("sec_8k", "effective immediately")
cut("8k_resign", D + "sec_8k_full.png", [0, p1[1] - 70, 900, 110], union(p1, p2), "SEC / Nvidia Form 8-K", "Nov 12, 2026")
k1 = ph("sec_8k", "Colette M. Kress"); k2 = ph("sec_8k", "interim Chief Executive Officer")
cut("8k_kress", D + "sec_8k_full.png", [0, k1[1] - 25, 900, 70], union(k1, k2), "SEC / Nvidia Form 8-K", "Nov 12, 2026")
j1 = ph("sec_8k", "Harvey C. Jones")
cut("8k_jones", D + "sec_8k_full.png", [0, j1[1] - 20, 900, 60], j1, "SEC / Nvidia Form 8-K", "Nov 12, 2026")
cut("ex991_top", D + "sec_ex991_full.png", [0, 14, 900, 316], ph("sec_ex991", "Jensen Huang has resigned"), "Nvidia press release (Ex. 99.1)", "Nov 12, 2026")
# --- Nvidia newsroom
cut("nv_msg_title", D + "nv_message_full.png", [0, 190, 600, 270], None, "Nvidia newsroom", "Nov 8, 2026",
    note="title, intro and date only")
q = ph("nv_message", "I was unfaithful to my wife")
cut("nv_msg_quote", D + "nv_message_full.png", [q[0] - 8, q[1] - 8, q[2] + 13, q[3] + 15], q, "Nvidia newsroom", "Nov 8, 2026",
    note="cropped to the quoted sentence only; the rest of the paragraph is excluded")
n1 = ph("nv_message", "national security"); n2 = ph("nv_message", "cooperate fully")
cut("nv_msg_natsec", D + "nv_message_full.png", [0, n1[1] - 32, 600, n2[1] - n1[1] + 56], union(n1, n2), "Nvidia newsroom", "Nov 8, 2026")
cut("nv_board_title", D + "nv_board_full.png", [0, 190, 600, 150], None, "Nvidia newsroom", "Nov 8, 2026")
b1 = ph("nv_board", "independent investigation")
cut("nv_board_inv", D + "nv_board_full.png", [0, b1[1] - 34, 600, 104], b1, "Nvidia newsroom", "Nov 8, 2026")
r1 = ph("nv_board", "no reason to believe"); r2, r3 = S["nv_board"]["phrases"]["NVIDIA secrets were compromised"]
cut("nv_board_noreason", D + "nv_board_full.png", [0, r1[1] - 34, 600, 110], union(r1, r2, r3), "Nvidia newsroom", "Nov 8, 2026")
w1 = ph("nv_independent", "Wachtell")
cut("nv_indep", D + "nv_independent_full.png", [0, 190, 600, w1[1] - 190 + 90], w1, "Nvidia newsroom", "Nov 10, 2026",
    note="title, date and statement; Nvidia logo panel in between is part of the page")
cut("nv_transition", D + "nv_transition_full.png", [0, 190, 600, 330], ph("nv_transition", "Interim Chief Executive Officer"), "Nvidia newsroom", "Nov 12, 2026")
# --- China MFA transcript (answer only; spokesperson photo and AFP question excluded)
u = ph("mfa_1030", "unsubstantiated"); sm = ph("mfa_1030", "smear")
cut("mfa_answer", D + "mfa_1030_full.png", [0, u[1] - 14, 600, sm[1] + sm[3] - u[1] + 30], union(u, sm), "China MFA transcript", "Oct 30, 2026",
    note="spokesperson's answer only")
# --- House letter (PDF rendered at 200 dpi; 1 pt = 200/72 px). Stored as CSS-equivalent px (/2).
pt = 200 / 72 / 2
cut("house_letter_top", D + "house_letter_1104-1.png", [60 * pt, 20 * pt, 492 * pt, 329.5 * pt], [72 * pt, 334 * pt, 468 * pt, 16 * pt],
    "U.S. House committees", "Nov 4, 2026", url="https://chinaselectcommittee.house.gov/sites/evo-subsites/selectcommitteeontheccp.house.gov/files/evo-media-document/nvidia-letter-pdf.pdf",
    note="letterhead to first sentence; following lines that name a third party are excluded")
cut("house_letter_date", D + "house_letter_1104-1.png", [60 * pt, 466 * pt, 492 * pt, 40 * pt], [72 * pt, 486 * pt, 217 * pt, 16 * pt],
    "U.S. House committees", "Nov 4, 2026", url="https://chinaselectcommittee.house.gov/sites/evo-subsites/selectcommitteeontheccp.house.gov/files/evo-media-document/nvidia-letter-pdf.pdf")
# --- Headlines: masthead + headline + byline/date only
h = h1("hl_nyt_1029_desk"); a = ph("hl_nyt_1029_desk", "Nvidia Chief Seen as", 1); b = ph("hl_nyt_1029_desk", "Target of Chinese Spy Plot")
cut("hl_nyt_1029", Hd + "hl_nyt_1029_desk_full.png", [60, 0, 580, b[1] + b[3] + 2], union(a, b), "The New York Times", "Oct 29, 2026", kind="headline",
    note="masthead + headline; photo and dek excluded")
for k, extra, outlet, date in [("hl_nyt_2025", 8, "The New York Times", "Oct 9, 2025"), ("hl_nyt_wallst", 70, "The New York Times", "Nov 13, 2026"),
                               ("hl_cbs_megaspeed", 120, "CBS News", "Nov 13, 2026"), ("hl_cbs_investigation", 115, "CBS News", "Nov 9, 2026"),
                               ("hl_cbs_stock", 115, "CBS News", "Nov 9, 2026"), ("hl_nbc_megaspeed", 70, "NBC News", "Nov 12, 2026"),
                               ("hl_yahoo_1112", 10, "Yahoo Finance / The Motley Fool", "Nov 12, 2026")]:
    hh = h1(k)
    cut(k.replace("hl_", "hl_"), Hd + k + "_full.png", [0, 0, 600, hh["bottom"] + extra], [hh["left"], hh["top"], hh["right"] - hh["left"], hh["bottom"] - hh["top"]],
        outlet, date, kind="headline")
hh = h1("hl_techcrunch_resigns")
cut("hl_tc_resigns", Hd + "hl_techcrunch_resigns_full.png", [0, hh["top"] - 70, 600, hh["bottom"] - hh["top"] + 185],
    [hh["left"], hh["top"], hh["right"] - hh["left"], hh["bottom"] - hh["top"]], "TechCrunch", "Nov 12, 2026", kind="headline",
    note="headline panel; photo above excluded")
hh = h1("hl_techcrunch_testify")
cut("hl_tc_testify", Hd + "hl_techcrunch_testify_full.png", [0, hh["top"] - 16, 600, 150], [hh["left"], hh["top"], hh["right"] - hh["left"], hh["bottom"] - hh["top"]],
    "TechCrunch", "Nov 12, 2026", kind="headline", note="headline and lede; photo above excluded")
hh = h1("hl_fox_kress")
cut("hl_fox_kress", Hd + "hl_fox_kress_full.png", [0, hh["top"] - 50, 600, hh["bottom"] - hh["top"] + 215], [hh["left"], hh["top"], hh["right"] - hh["left"], hh["bottom"] - hh["top"]],
    "Fox Business", "Nov 12, 2026", kind="headline", note="dateline to byline; video thumbnails excluded")
c = S["hl_cbs_megaspeed"]["phrases"]["purchased $4.8 billion of Nvidia's advanced artificial intelligence equipment"]
cut("cbs_48", Hd + "hl_cbs_megaspeed_full.png", [0, c[0][1] - 40, 600, 110], ph("hl_cbs_megaspeed", "$4.8 billion"), "CBS News", "Nov 13, 2026", kind="headline")
hh = h1("hl_nyt_fall")
cut("nyt_fall_title", Hd + "hl_nyt_fall_full.png", [0, hh["top"] - 30, 600, 150], None, "The New York Times", "Nov 13, 2026", kind="headline")
y1, y2 = ph("hl_yahoo_1112", "closed at $166.19"), ph("hl_yahoo_1112", "falling 4.34%")
cut("yahoo_close", Hd + "hl_yahoo_1112_full.png", [0, y1[1] - 30, 600, 90], union(y1, y2), "Yahoo Finance / The Motley Fool", "Nov 12, 2026", kind="headline")


# --- added: on-record quotes located in captured pages
c1 = S["hl_cbs_stock"]["phrases"]["committed to continuing to lead Nvidia as CEO without interruption"]
cut("cbs_pledge", Hd + "hl_cbs_stock_full.png", [0, c1[0][1] - 32, 600, 92], union(*c1), "CBS News", "Nov 9, 2026", kind="headline",
    note="Nvidia spokesperson quote as published by CBS")
d1 = S["hl_techcrunch_resigns"]["phrases"]["The Justice Department has since taken over the federal investigation into the company"]
cut("tc_doj", Hd + "hl_techcrunch_resigns_full.png", [0, d1[0][1] - 10, 600, 96], union(*d1), "TechCrunch (citing NYT)", "Nov 12, 2026", kind="headline")
e1 = S["nv_transition"]["phrases"]["third-quarter fiscal 2027 financial results"]; e2 = S["nv_transition"]["phrases"]["Tuesday, November 17"]
cut("nv_earnings", D + "nv_transition_full.png", [0, e1[0][1] - 30, 600, 92], union(e1[0], *e2), "Nvidia newsroom", "Nov 12, 2026")
n1 = S["hl_tc_timeline"]["phrases"]["not unusual"][0]
cut("tc_notunusual", Hd + "hl_tc_timeline_full.png", [0, n1[1] - 34, 600, 96], n1, "TechCrunch (Nvidia statement)", "Nov 13, 2026", kind="headline",
    note="Nvidia spokesperson quote as published by TechCrunch")


def main():
    os.makedirs(os.path.join(A, "cuts"), exist_ok=True)
    out = []
    for c in CUTS:
        im = Image.open(os.path.join(A, c["src"])).convert("RGB")
        k = 2  # DSF
        x, y, w, hgt = c["rect"]
        box = (max(0, x * k), max(0, y * k), min(im.width, (x + w) * k), min(im.height, (y + hgt) * k))
        cr = im.crop(box)
        path = os.path.join(A, "cuts", c["id"] + ".png"); cr.save(path)
        c["file"] = os.path.relpath(path, ROOT); c["px"] = list(cr.size)
        if c["focus"]:
            fx, fy, fw, fh = c["focus"]
            c["focus_px"] = [(fx - x) * k, (fy - y) * k, fw * k, fh * k]
        out.append(c)
    json.dump(out, open(os.path.join(A, "cuts.json"), "w"), indent=1)
    print(len(out), "cuts")


if __name__ == "__main__":
    main()
