"""Collect freely licensed B-roll from the Internet Archive (archive.org).

Only items whose `licenseurl` is Public Domain Mark, CC0, CC BY or CC BY-SA are used (no NC/ND).
Clips are trimmed to 20 s, scaled to 1080p and rejected if a face is detected.
"""
import json, os, re, subprocess, time, urllib.parse, urllib.request
import cv2
sys_path = os.path.dirname(os.path.abspath(__file__))
import sys; sys.path.insert(0, sys_path)
from nasa import faces

ROOT = os.path.dirname(sys_path)
OUT = os.path.join(ROOT, "assets2", "broll")
REG = os.path.join(ROOT, "assets2", "ia.json")
UA = "news-explainer-build/2.0 (educational video research)"
OKLIC = re.compile(r"creativecommons\.org/(publicdomain/(zero|mark)|licenses/by(-sa)?/)", re.I)
QUERIES = {"singapore": "Singapore skyline", "kl": "Kuala Lumpur", "port": "container port", "ticker": "stock ticker",
           "typing": "typing keyboard", "tower": "skyscraper glass", "rain": "rain window", "capitol": "Capitol Washington",
           "city_night": "city night timelapse", "newsroom": "newspaper printing press", "server": "server room"}


def get(url):
    for i in range(4):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60).read()
        except Exception as e:
            time.sleep(5 * (i + 1)); err = e
    raise err


def main():
    reg = json.load(open(REG)) if os.path.exists(REG) else {}
    seen = {v["identifier"] for v in reg.values()}
    for cat, q in QUERIES.items():
        qq = f'({q}) AND mediatype:movies AND licenseurl:*creativecommons*'
        url = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(
            {"q": qq, "fl[]": ["identifier", "title", "licenseurl", "creator"], "rows": 25, "output": "json"}, doseq=True)
        docs = json.loads(get(url))["response"]["docs"]
        got = 0
        for d in docs:
            if got >= 2 or d["identifier"] in seen:
                continue
            lic = d.get("licenseurl", "")
            # never use re-uploads of YouTube/TV material, even when hosted on archive.org
            if re.search(r"youtube|tv|news|cnn|bbc|fox|nbc|abc|cbs", d["identifier"] + " " + str(d.get("title", "")), re.I):
                continue
            if not OKLIC.search(lic) or re.search(r"-nc|-nd", lic):
                continue
            md = json.loads(get(f"https://archive.org/metadata/{d['identifier']}"))
            if re.search(r"youtube\.com|youtu\.be", json.dumps(md.get("metadata", {})), re.I):
                continue
            files = [f for f in md.get("files", []) if f.get("name", "").lower().endswith(".mp4")]
            if not files:
                continue
            f = sorted(files, key=lambda f: -int(f.get("size", 0) or 0))[0]
            if int(f.get("size", 0) or 0) > 400e6:
                continue
            key = f"ia_{cat}_{got + 1:02d}"
            raw, mp4 = os.path.join(OUT, key + "_raw.mp4"), os.path.join(OUT, key + ".mp4")
            src = f"https://archive.org/download/{d['identifier']}/{urllib.parse.quote(f['name'])}"
            try:
                open(raw, "wb").write(get(src))
            except Exception as e:
                print("skip", d["identifier"], e); continue
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "3", "-i", raw, "-t", "20", "-an", "-vf",
                            "scale=-2:1080:flags=lanczos,fps=30", "-c:v", "libx264", "-crf", "18", "-preset", "fast", mp4])
            os.remove(raw)
            if not os.path.exists(mp4) or os.path.getsize(mp4) < 50000:
                continue
            if faces(mp4):
                os.remove(mp4); print("reject (faces)", d["identifier"], flush=True); continue
            reg[key] = {"kind": "video", "cat": cat, "identifier": d["identifier"], "title": d.get("title"),
                        "author": d.get("creator") if isinstance(d.get("creator"), str) else ", ".join(d.get("creator") or []),
                        "license_url": lic, "license": lic.split("creativecommons.org/")[-1].strip("/"),
                        "page": f"https://archive.org/details/{d['identifier']}", "src": src, "file": os.path.relpath(mp4, ROOT)}
            seen.add(d["identifier"]); got += 1
            json.dump(reg, open(REG, "w"), indent=1)
            print("video", key, lic, (d.get("title") or "")[:60], flush=True)
    print("total", len(reg))


if __name__ == "__main__":
    main()
