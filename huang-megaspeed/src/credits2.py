"""Write out/credits.json for the v2 cut from the asset registries and the plan."""
import json, os, re


def clean_author(a):
    return re.sub(r"\s*\(talk[^)]*\)", "", a or "").strip()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A2, B = os.path.join(ROOT, "assets2"), os.path.join(ROOT, "build")
plan = json.load(open(os.path.join(B, "plan2.json")))
cuts = {c["id"]: c for c in json.load(open(os.path.join(A2, "cuts.json")))}
com = json.load(open(os.path.join(A2, "commons.json")))
nasa = json.load(open(os.path.join(A2, "nasa.json")))
shots = json.load(open(os.path.join(A2, "shots.json")))

used_bg = {}
for b in plan["bg"]:
    used_bg.setdefault(b["id"], b)
for m in plan["mid"]:
    used_bg.setdefault(m["id"], m)
used_cuts = sorted({it["cut"] for g in plan["front"] for it in g["items"] if it["cut"] != "__stamp__"})

assets = []
for cid in used_cuts:
    c = cuts[cid]
    key = os.path.basename(c["src"]).replace("_full.png", "").replace("-1.png", "")
    assets.append({"file": c["file"], "type": "real screenshot (cropped)", "outlet_or_publisher": c["outlet"], "date": c["date"],
                   "source_url": c["url"] or shots.get(key, {}).get("url", ""),
                   "captured": "2026-11-14, Playwright/Chromium, deviceScaleFactor 2" + (" (sec.gov fair-access User-Agent with owner-approved contact)" if "sec.gov" in (c["url"] or "") else ""),
                   "license": "screenshot of a publicly accessible page, cropped, shown briefly with attribution for news commentary (fair use / fair dealing); not a recreation",
                   "crop_note": c.get("note", "")})
for k, a in used_bg.items():
    if k in com:
        v = com[k]
        assets.append({"file": v["file"], "type": "Wikimedia Commons " + v["kind"], "title": v["title"], "author": clean_author(v.get("author")),
                       "license": v.get("license"), "license_url": v.get("license_url"), "source_url": v.get("page"),
                       "download_url": v.get("src"), "segment_or_crop": v.get("segment") or v.get("note") or a.get("crop"),
                       "license_verified_via": "Commons API extmetadata (LicenseShortName), 2026-11-14"})
    elif k in nasa:
        v = nasa[k]
        assets.append({"file": v["file"], "type": "NASA video", "title": v["title"], "author": v["author"], "license": v["license"],
                       "license_url": v["license_url"], "source_url": v["page"], "segment": v.get("segment"),
                       "note": "NASA media not subject to U.S. copyright; no NASA insignia shown; no endorsement implied"})
    elif k == "v1_capitol":
        assets.append({"file": "assets/commons/capitol.jpg", "type": "Wikimedia Commons photo", "title": "United States Capitol west front edit2.jpg",
                       "author": "Architect of the Capitol (derivative: O.J.)", "license": "Public domain",
                       "source_url": "https://commons.wikimedia.org/wiki/File:United_States_Capitol_west_front_edit2.jpg"})
    elif k == "v1_singapore":
        assets.append({"file": "assets/commons/singapore.jpg", "type": "Wikimedia Commons photo", "title": "Marina Bay Sands in the evening - 20101120.jpg",
                       "author": "Someformofhuman", "license": "CC BY-SA 3.0", "license_url": "https://creativecommons.org/licenses/by-sa/3.0/",
                       "source_url": "https://commons.wikimedia.org/wiki/File:Marina_Bay_Sands_in_the_evening_-_20101120.jpg"})
    elif a.get("file", "").startswith("assets2/photos/"):
        v = com.get(k, {})
        assets.append({"file": a["file"], "type": "Wikimedia Commons photo", "title": v.get("title"), "author": clean_author(v.get("author")),
                       "license": v.get("license"), "source_url": v.get("page")})

out = {"project": "Huang / Megaspeed documentary explainer (v2)", "as_of": "2026-11-14", "assets": assets,
       "generated_in_code": {
           "drawn_cards": "Only three drawn cards: Alice Huang silhouette (no image of her), alleged-vs-proven summary, end card.",
           "stamps_and_highlights": "DENIED / CONFIRMED / REPORTED / ALLEGED stamps and highlighter swipes are graphic overlays on real screenshots; page content itself is never edited.",
           "music": "Synthesized in code (src/audio.py).", "sfx": "Synthesized in code (src/audio.py).",
           "narration": "AI-generated: Kokoro-82M (hexgrad/Kokoro-82M, Apache-2.0), voice af_heart, speed 1.05."},
       "fonts": [{"name": "Inter / Inter Display", "license": "SIL OFL 1.1"}, {"name": "JetBrains Mono", "license": "SIL OFL 1.1"}],
       "not_used": ["No TV/news video, film or podcast clips; no YouTube/TikTok/X downloads.",
                    "No Getty/AP/Reuters/AFP/Bloomberg photos: headline screenshots are cropped to exclude article images.",
                    "Internet Archive dropped (unreliable licence labels: a 'CC0' item was a copyrighted game trailer).",
                    "No recreated or look-alike documents or headlines."]}
json.dump(out, open(os.path.join(ROOT, "out", "credits.json"), "w"), indent=1, ensure_ascii=False)
print(len(assets), "assets credited:", sum(1 for a in assets if a["type"].startswith("real")), "screenshots,",
      sum(1 for a in assets if "Commons" in a["type"]), "Commons,", sum(1 for a in assets if a["type"] == "NASA video"), "NASA")
