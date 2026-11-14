"""Collect public-domain B-roll from the NASA Image and Video Library (images-api.nasa.gov).

NASA media is generally not subject to U.S. copyright; items whose description mentions a
copyright holder or third-party credit are skipped. Clips are trimmed to 20 s, scaled to 1080p,
and checked for faces (Haar cascades on 6 sampled frames); clips with faces are rejected.
Usage: python src/nasa.py
"""
import json, os, re, subprocess, time, urllib.parse, urllib.request
import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets2", "broll")
REG = os.path.join(ROOT, "assets2", "nasa.json")
API = "https://images-api.nasa.gov"
UA = "news-explainer-build/2.0 (educational video research)"
QUERIES = {
    "supercomputer": "datacenter", "computer servers": "datacenter", "data center": "datacenter",
    "computer racks": "datacenter", "clean room": "cleanroom", "circuit board": "circuit",
    "microchip": "circuit", "electronics assembly": "circuit", "Singapore night": "singapore",
    "Malaysia night": "malaysia", "Earth at night city lights": "night_earth", "Washington DC aerial": "capitol",
    "United States Capitol": "capitol", "city timelapse": "city", "rain": "rain", "ship port": "port",
}
FACE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
PROF = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")


def get(url):
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(req, timeout=60).read()
        except Exception as e:
            time.sleep(5 * (i + 1)); err = e
    raise err


def faces(path):
    n = 0
    cap = cv2.VideoCapture(path)
    tot = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    for k in range(6):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(tot * (k + 0.5) / 6))
        ok, fr = cap.read()
        if not ok:
            continue
        g = cv2.cvtColor(cv2.resize(fr, (960, 540)), cv2.COLOR_BGR2GRAY)
        n += len(FACE.detectMultiScale(g, 1.1, 6, minSize=(36, 36))) + len(PROF.detectMultiScale(g, 1.1, 6, minSize=(36, 36)))
    return n


def main():
    reg = json.load(open(REG)) if os.path.exists(REG) else {}
    seen = {v["nasa_id"] for v in reg.values()}
    for q, cat in QUERIES.items():
        got = 0
        d = json.loads(get(f"{API}/search?" + urllib.parse.urlencode({"q": q, "media_type": "video"})))
        for it in d["collection"]["items"][:15]:
            if got >= 2:
                break
            m = it["data"][0]; nid = m["nasa_id"]
            if nid in seen:
                continue
            desc = (m.get("description", "") + " " + m.get("title", "")).lower()
            if re.search(r"copyright|©|courtesy of (?!nasa)|credit: (?!nasa)", desc) or m.get("secondary_creator", "").lower().startswith("courtesy"):
                continue
            files = json.loads(get(f"{API}/asset/{urllib.parse.quote(nid)}"))["collection"]["items"]
            mp4s = [f["href"] for f in files if f["href"].endswith(".mp4")]
            pick = next((u for tag in ("~medium.mp4", "~orig.mp4", "~large.mp4", "~mobile.mp4") for u in mp4s if u.endswith(tag)), None)
            if not pick:
                continue
            key = f"nasa_{cat}_{len([k for k in reg if reg[k]['cat'] == cat]) + 1:02d}"
            raw, mp4 = os.path.join(OUT, key + "_raw.mp4"), os.path.join(OUT, key + ".mp4")
            try:
                open(raw, "wb").write(get(pick.replace("http://", "https://").replace(" ", "%20")))
            except Exception as e:
                print("skip", nid, e); continue
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "2", "-i", raw, "-t", "20", "-an", "-vf",
                            "scale=-2:1080:flags=lanczos,fps=30", "-c:v", "libx264", "-crf", "18", "-preset", "fast", mp4])
            os.remove(raw)
            if not os.path.exists(mp4) or os.path.getsize(mp4) < 50000:
                continue
            nf = faces(mp4)
            if nf:
                os.remove(mp4); print("reject (faces)", nid, flush=True); continue
            reg[key] = {"kind": "video", "cat": cat, "query": q, "nasa_id": nid, "title": m.get("title"),
                        "center": m.get("center"), "date": m.get("date_created"), "file": os.path.relpath(mp4, ROOT),
                        "page": f"https://images.nasa.gov/details/{urllib.parse.quote(nid)}", "src": pick,
                        "license": "Public domain (NASA media, not subject to U.S. copyright)",
                        "license_url": "https://www.nasa.gov/nasa-brand-center/images-and-media/",
                        "author": "NASA" + (f" / {m.get('center')}" if m.get("center") else "")}
            seen.add(nid); got += 1
            json.dump(reg, open(REG, "w"), indent=1)
            print("video", key, m.get("title", "")[:70], flush=True)
    print("total", len(reg))


if __name__ == "__main__":
    main()
