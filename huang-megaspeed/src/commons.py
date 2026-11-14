"""Collect freely licensed photos and video B-roll from Wikimedia Commons.

Only PD / CC0 / CC BY / CC BY-SA files are kept; licence, author and URL are recorded from the
Commons API (extmetadata). Videos are taken from Commons' own transcoded derivatives.
Usage: python src/commons.py
"""
import json, os, re, subprocess, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets2")
UA = "news-explainer-build/2.0 (non-commercial educational video research)"
API = "https://commons.wikimedia.org/w/api.php"
OK_LIC = re.compile(r"^(public domain|pd|cc0|cc by(-sa)? ?\d(\.\d)?|cc by(-sa)?)", re.I)

PHOTO_Q = {
    "huang": ["Jensen Huang Computex", "Jensen Huang GTC", "Jensen Huang keynote", "黃仁勳", "黄仁勋",
              "Jensen Huang Taiwan", "Jensen Huang White House", "Jensen Huang 2018", "Jensen Huang 2019",
              "Jensen Huang 2023", "Jensen Huang 2024", "Jensen Huang 2025", "Jensen Huang"],
    "singapore": ["Singapore skyline night", "Marina Bay Singapore night"],
    "kl": ["Kuala Lumpur skyline night"],
    "datacenter": ["data center server room", "server racks datacenter"],
    "gpu": ["Nvidia GPU", "graphics card circuit board", "Nvidia H100"],
    "wafer": ["silicon wafer", "semiconductor wafer"],
    "cleanroom": ["semiconductor clean room"],
    "port": ["container port Singapore", "container terminal night"],
    "capitol": ["United States Capitol dome", "United States Capitol night"],
    "hearing": ["Rayburn House Office Building hearing room", "congressional hearing room empty"],
    "nvidia_hq": ["Nvidia headquarters Santa Clara", "Nvidia Voyager building"],
    "ticker": ["stock ticker Nasdaq MarketSite", "Nasdaq MarketSite"],
    "tower": ["glass office tower", "glass skyscraper facade"],
    "rain": ["rain on window glass"],
}
VIDEO_Q = ["data center", "server room", "computer servers", "Singapore night timelapse", "Singapore skyline",
           "Kuala Lumpur timelapse", "container port", "container ship port", "United States Capitol",
           "stock market ticker", "rain window", "circuit board", "semiconductor", "city traffic night timelapse",
           "skyscraper", "typing keyboard", "clean room"]


def get(params):
    params.update({"format": "json", "formatversion": 2})
    url = API + "?" + urllib.parse.urlencode(params)
    for i in range(6):
        try:
            time.sleep(4.0)
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return json.load(urllib.request.urlopen(req, timeout=40))
        except Exception as e:
            print("  api retry", i, e, flush=True); time.sleep(60 * (i + 1)); err = e
    raise err


def search(q, kind, n=30):
    ft = "filetype:bitmap" if kind == "photo" else "filetype:video"
    d = get({"action": "query", "list": "search", "srsearch": f"{q} {ft}", "srnamespace": 6, "srlimit": n})
    titles = [x["title"] for x in d.get("query", {}).get("search", [])]
    if not titles:
        return []
    prop = "imageinfo" if kind == "photo" else "videoinfo"
    pre = "ii" if kind == "photo" else "vi"
    d = get({"action": "query", "titles": "|".join(titles[:50]), "prop": prop,
             pre + "prop": "url|size|extmetadata|mime" + ("" if kind == "photo" else "|derivatives")})
    pages = {p["title"]: p for p in d.get("query", {}).get("pages", [])}
    return [pages[t] for t in titles if t in pages]


def thumb(ii, title, w=1920):
    """Standard-size CDN thumbnail URL (avoids asking the API to render thumbnails)."""
    url = ii["url"]
    if ii.get("width", 0) <= w or not re.search(r"\.(jpe?g|png|tiff?)$", url, re.I):
        return url
    m = re.match(r"https://upload\.wikimedia\.org/wikipedia/commons/(\w)/(\w\w)/(.+)$", url)
    if not m:
        return url
    name = m.group(3)
    ext = ".jpg" if re.search(r"\.tiff?$", name, re.I) else ""
    return f"https://thumb.wikimedia.org/wikipedia/commons/thumb/{m.group(1)}/{m.group(2)}/{name}/{w}px-{name}{ext}"


def meta(info):
    m = info.get("extmetadata", {})
    g = lambda k: re.sub(r"<[^>]+>", "", (m.get(k) or {}).get("value", "")).strip()
    return {"license": g("LicenseShortName"), "license_url": g("LicenseUrl"), "author": g("Artist")[:200],
            "credit": g("Credit")[:200], "desc": g("ImageDescription")[:300], "date": g("DateTimeOriginal")[:40],
            "restrictions": g("Restrictions")}


def fetch(url, path):
    for i in range(5):
        try:
            time.sleep(1.5)
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
                f.write(r.read())
            return
        except Exception as e:
            print("  dl retry", i, e, flush=True); time.sleep(15 * (i + 1)); err = e
    raise err


def main():
    reg_path = os.path.join(OUT, "commons.json")
    reg = json.load(open(reg_path)) if os.path.exists(reg_path) else {}
    seen = {v["title"] for v in reg.values()}
    # videos
    for q in VIDEO_Q:
        for pg in search(q, "video", 10):
            if pg["title"] in seen or "videoinfo" not in pg:
                continue
            if len([k for k in reg if reg[k]["cat"] == q]) >= 3:
                break
            vi = pg["videoinfo"][0]; md = meta(vi)
            if not OK_LIC.match(md["license"]):
                continue
            ders = [d for d in vi.get("derivatives", []) if d.get("height", 0) >= 480 and "webm" in d.get("type", "")]
            if not ders:
                continue
            der = sorted(ders, key=lambda d: abs(d.get("height", 0) - 1080))[0]
            key = f"vid_{len([k for k in reg if k.startswith('vid_')]) + 1:02d}"
            raw = os.path.join(OUT, "broll", key + ".webm")
            try:
                fetch(der["src"], raw)
            except Exception as e:
                print("skip", pg["title"], e); continue
            mp4 = raw[:-5] + ".mp4"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-t", "20", "-an", "-vf",
                            "scale=-2:1080:flags=lanczos", "-c:v", "libx264", "-crf", "18", "-preset", "fast", mp4])
            os.remove(raw)
            reg[key] = {"kind": "video", "cat": q, "title": pg["title"], "file": os.path.relpath(mp4, ROOT),
                        "page": vi["descriptionurl"], "src": der["src"], "duration": vi.get("duration"), **md}
            seen.add(pg["title"]); print("video", key, md["license"], pg["title"][:70], flush=True)
            json.dump(reg, open(reg_path, "w"), indent=1, ensure_ascii=False)
            time.sleep(0.5)
    # photos
    for cat, qs in PHOTO_Q.items():
        for q in qs:
            for pg in search(q, "photo"):
                if pg["title"] in seen or "imageinfo" not in pg:
                    continue
                if len([k for k in reg if k.startswith(cat + "_")]) >= (16 if cat == "huang" else 4):
                    break
                ii = pg["imageinfo"][0]; md = meta(ii)
                if not OK_LIC.match(md["license"]) or ii["width"] < 1000:
                    continue
                if cat == "huang" and not re.search(r"huang|黃仁勳|黄仁勋", pg["title"] + md["desc"], re.I):
                    continue
                stem = re.sub(r"[\d\W_]+", " ", pg["title"].lower().replace("(cropped)", "")).strip()[:40]
                if sum(1 for v in reg.values() if v.get("stem") == stem) >= (2 if cat == "huang" else 1):
                    continue
                key = f"{cat}_{len([k for k in reg if k.startswith(cat + '_')]) + 1:02d}"
                path = os.path.join(OUT, "photos", key + ".jpg")
                try:
                    fetch(thumb(ii, pg["title"]), path)
                except Exception as e:
                    print("skip", pg["title"], e); continue
                reg[key] = {"kind": "photo", "cat": cat, "title": pg["title"], "file": os.path.relpath(path, ROOT),
                            "page": ii["descriptionurl"], "src": thumb(ii, pg["title"]), "stem": stem if cat == "huang" else pg["title"], **md}
                seen.add(pg["title"]); print("photo", key, md["license"], pg["title"][:70], flush=True)
                json.dump(reg, open(reg_path, "w"), indent=1, ensure_ascii=False)
                time.sleep(0.5)
    json.dump(reg, open(reg_path, "w"), indent=1, ensure_ascii=False)
    print("total", len(reg))


if __name__ == "__main__":
    main()
