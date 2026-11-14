"""Collect freely licensed photos and video B-roll from Wikimedia Commons.

Only PD / CC0 / CC BY / CC BY-SA files are kept; licence, author and URL are recorded from the
Commons API (extmetadata). Videos are taken from Commons' own transcoded derivatives.
Usage: python src/commons.py
"""
import json, os, re, subprocess, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets2")
UA = "BhunZ-news-explainer/2.0 (baohung.clone@gmail.com) python-urllib/3.12"   # Wikimedia UA policy (owner-approved contact)
API = "https://commons.wikimedia.org/w/api.php"
OK_LIC = re.compile(r"^(public domain|pd|cc0|cc by(-sa)? ?\d(\.\d)?|cc by(-sa)?)", re.I)

PHOTO_Q = {
    "huang": ["Jensen Huang GTC", "Jensen Huang Computex 2023", "Jensen Huang Computex 2024", "黃仁勳 2024", "Jensen Huang 2019"],
}
VIDEO_Q = ["Petronas Towers", "Kuala Lumpur skyline", "container terminal", "Port of Singapore", "United States Capitol",
           "Washington D.C. timelapse", "stock exchange", "rain drops window", "skyscraper glass", "city lights timelapse",
           "printed circuit board", "silicon wafer"]


def get(params):
    """API GET that honours Wikimedia's Retry-After on 429 (rate-limit best practice)."""
    import urllib.error
    params.update({"format": "json", "formatversion": 2, "maxlag": 5})
    url = API + "?" + urllib.parse.urlencode(params)
    for i in range(12):
        try:
            time.sleep(3.0)
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return json.load(urllib.request.urlopen(req, timeout=40))
        except urllib.error.HTTPError as e:
            wait = int(e.headers.get("Retry-After") or 30) + 2
            print(f"  429/err {e.code}: waiting {wait}s", flush=True); time.sleep(wait); err = e
        except Exception as e:
            time.sleep(10); err = e
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
            if len([k for k in reg if reg[k]["cat"] == q]) >= 2:
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
                if len([k for k in reg if k.startswith(cat + "_") and not reg[k].get("rejected")]) >= (22 if cat == "huang" else 4):
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
