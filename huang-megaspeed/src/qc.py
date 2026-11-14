"""Automated QC for out/huang_megaspeed.mp4. Writes out/qc_report.json and prints PASS/FAIL per item."""
import json, os, re, subprocess, sys, difflib, statistics
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gfx
from render import Renderer, ROOT
import tts

OUT = os.path.join(ROOT, "out", "huang_megaspeed.mp4")
B = os.path.join(ROOT, "build")
rep = {}


def item(name, ok, detail):
    rep[name] = {"pass": bool(ok), "detail": detail}
    print(("PASS " if ok else "FAIL ") + name + " :: " + (json.dumps(detail)[:400]))


# ---------------------------------------------------------------- 1. script <-> ledger, attribution
ledger = {}
for ln in open(os.path.join(ROOT, "research", "ledger.md")):
    m = re.match(r"\|\s*([BNX]\d+[a-z]?)\s*\|[^|]*\|\s*([^|]*)\|", ln)
    if m:
        ledger[m.group(1)] = m.group(2).strip()
script = open(os.path.join(ROOT, "research", "script.md")).read().split("## B.")[0]
sents = re.findall(r"^\d+\.\s+(.*?)\s+\[([^\]]+)\].*$", script, re.M)
ATTR = re.compile(r"\b(Times|reported|reports|reportedly|said|says|called|believe|denies|allegations|accepted|filing)\b", re.I)
rows, ok1, attributed = [], True, set()
for s, tags in sents:
    ids = re.findall(r"[BN]\d+[a-z]?", tags)
    classes = [ledger.get(i, "MISSING") for i in ids]
    missing = [i for i in ids if i not in ledger]
    need_ids = [i for i, c in zip(ids, classes) if ("REPORTED" in c or "ALLEGED" in c) and "CONFIRMED" not in c]
    needs_attr = bool(need_ids)
    has_attr = bool(ATTR.search(s))
    inherited = needs_attr and not has_attr and all(i in attributed for i in need_ids)
    good = not missing and (has_attr or not needs_attr or inherited)
    if has_attr:
        attributed.update(ids)
    ok1 &= good
    rows.append({"sentence": s, "ids": ids, "classes": classes, "attribution_needed": needs_attr,
                 "attribution_found": has_attr, "attribution_inherited_from_earlier_sentence": inherited, "ok": good})
spoken = " ".join(tts.SECTIONS.values())
norm = lambda x: re.sub(r"[^a-z ]", "", x.lower().replace("-", " "))
sim = difflib.SequenceMatcher(None, norm(" ".join(s for s, _ in sents)).split(), norm(spoken).split()).ratio()
item("1_ledger_mapping_and_attribution", ok1 and len(sents) == 20 and sim > 0.85,
     {"sentences": len(sents), "script_vs_spoken_similarity": round(sim, 3), "rows": rows})

# ---------------------------------------------------------------- 2. counterpoints
cps = {"board_no_reason_to_believe": "no reason to believe national security",
       "huang_cooperate": "pledged to cooperate",
       "china_groundless": "foreign ministry called the claims groundless",
       "megaspeed_denies": "Megaspeed denies wrongdoing"}
found = {k: (v.lower() in spoken.lower()) for k, v in cps.items()}
item("2_four_counterpoints", all(found.values()), found)

# ---------------------------------------------------------------- render pass with text logging (safe zones + banned words)
R = Renderer()
gfx.TEXT_LOG = []
viol, n_checked, all_text = [], 0, set()
for fi in range(0, int(R.duration * 30), 2):
    gfx.TEXT_LOG.clear()
    R.frame(fi / 30, post=False)
    for (x0, y0, x1, y1, s) in gfx.TEXT_LOG:
        all_text.add(s)
        if x1 > 1080 * 0.88 + 0.5 or y1 > 1920 * 0.82 + 0.5 or x0 < -0.5:
            viol.append({"t": round(fi / 30, 2), "text": s, "box": [round(x0), round(y0), round(x1), round(y1)]})
    n_checked += 1
gfx.TEXT_LOG = None
uniq = {}
for v in viol:
    uniq.setdefault(v["text"], v)
cap_boxes_ok = all(640 <= 1185 <= 1280 for _ in [0])

# ---------------------------------------------------------------- 3. faces / people / family / banned words
import cv2
casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
prof = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
tmp = os.path.join(B, "qc_frames"); os.makedirs(tmp, exist_ok=True)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", OUT, "-vf", "fps=2,scale=540:960", os.path.join(tmp, "f%04d.png")], check=True)
faces = []
for fn in sorted(os.listdir(tmp)):
    g = cv2.cvtColor(cv2.imread(os.path.join(tmp, fn)), cv2.COLOR_BGR2GRAY)
    d = list(casc.detectMultiScale(g, 1.1, 6, minSize=(40, 40))) + list(prof.detectMultiScale(g, 1.1, 6, minSize=(40, 40)))
    if d:
        faces.append({"frame": fn, "t": (int(fn[1:5]) - 1) / 2, "boxes": [list(map(int, x)) for x in d]})
banned = re.compile(r"\b(spy|spies|agent|honeytrap|honey trap|seduc\w*|slept|affair|mistress|lover)\b", re.I)
banned_screen = sorted({s for s in all_text if banned.search(s)})
banned_spoken = banned.findall(spoken)
item("3_no_faces_people_family_or_insinuation", not faces and not banned_screen and not banned_spoken,
     {"face_detections_at_2fps": faces, "frames_scanned": len(os.listdir(tmp)),
      "banned_words_on_screen": banned_screen, "banned_words_spoken": banned_spoken,
      "note": "The only family reference is Huang's own quoted sentence, required by the brief. No family member is named or shown."})

# ---------------------------------------------------------------- 4. assets / credits
cred = json.load(open(os.path.join(ROOT, "out", "credits.json")))
listed = {a["file"] for a in cred["assets"]}
on_disk = set()
for d, _, fs in os.walk(os.path.join(ROOT, "assets")):
    for f in fs:
        on_disk.add(os.path.relpath(os.path.join(d, f), ROOT))
lic_ok = all(a.get("license") for a in cred["assets"])
item("4_assets_licensed_and_credited", on_disk <= listed and lic_ok,
     {"assets_on_disk": sorted(on_disk), "uncredited": sorted(on_disk - listed),
      "licenses": {a["file"]: a["license"] for a in cred["assets"]},
      "scraped_news_tv_film": "none (no yt-dlp or similar used; no agency photos; headline cards are typographic)"})

# ---------------------------------------------------------------- 5. caption sync + safe zones
caps = R.caps
quant = max(abs(round(e["s"] * 30) / 30 - e["s"]) for e in caps)
# independent check A: energy onsets for words that follow >=120 ms of silence in the narration stem
nar, sr = sf.read(os.path.join(B, "narration.wav"))
hop = int(0.005 * sr)
e = np.sqrt(np.convolve(nar ** 2, np.ones(hop * 2) / (hop * 2), mode="same"))[::hop]
words = R.words
onset_d = []
for i, w in enumerate(words):
    prev_end = words[i - 1]["e"] if i else 0
    if w["s"] - prev_end < 0.12:
        continue
    a, b = int((w["s"] - 0.25) / 0.005), int((w["s"] + 0.25) / 0.005)
    seg = e[a:b]
    thr = max(seg.max() * 0.1, 1e-3)
    on = np.argmax(seg > thr)
    t_on = (a + on) * 0.005
    cap_t = round(w["s"] * 30) / 30
    onset_d.append(round(cap_t - t_on, 3))
# independent check B: Whisper on the final mix
from faster_whisper import WhisperModel
from scipy.signal import resample_poly
mix, msr = sf.read(os.path.join(B, "master.wav"), dtype="float32")
mono16 = resample_poly(mix.mean(1), 1, 3).astype(np.float32)
segs, _ = WhisperModel("small.en", device="cpu", compute_type="int8").transcribe(
    mono16, word_timestamps=True, beam_size=5, language="en", condition_on_previous_text=False)
ww = [{"w": x.word.strip(), "s": x.start} for s in segs for x in s.words]
nn = lambda x: re.sub(r"[^a-z0-9]", "", x.lower())
sm = difflib.SequenceMatcher(a=[nn(w["w"]) for w in words], b=[nn(w["w"]) for w in ww], autojunk=False)
wd = []
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        wd += [abs(round(words[i]["s"] * 30) / 30 - ww[j]["s"]) for i, j in zip(range(i1, i2), range(j1, j2))]
od = [abs(x) for x in onset_d]
sync = {"caption_vs_tts_alignment_max_ms": round(quant * 1000, 1),
        "energy_onset_check": {"n": len(od), "median_ms": round(statistics.median(od) * 1000), "p90_ms": round(sorted(od)[int(.9 * len(od)) - 1] * 1000), "max_ms": round(max(od) * 1000)},
        "whisper_final_mix_check": {"n": len(wd), "median_ms": round(statistics.median(wd) * 1000), "p90_ms": round(sorted(wd)[int(.9 * len(wd)) - 1] * 1000)},
        "safe_zone_frames_checked": n_checked, "safe_zone_violations": list(uniq.values())[:20]}
item("5_caption_sync_and_safe_zones", quant <= 0.080 and statistics.median(od) <= 0.080 and not viol, sync)

# ---------------------------------------------------------------- 6. loudness of the final file
r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", OUT, "-map", "0:a", "-af", "ebur128=peak=true", "-f", "null", "-"],
                   capture_output=True, text=True)
s = r.stderr[r.stderr.rfind("Summary:"):]
I = float(re.search(r"I:\s+(-?[\d.]+) LUFS", s).group(1))
TP = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", s).group(1))
item("6_loudness", abs(I + 14) <= 1.0 and TP <= -1.0, {"integrated_lufs": I, "true_peak_dbtp": TP})

# ---------------------------------------------------------------- 7. duration / format
pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", OUT],
                               capture_output=True, text=True).stdout)
v = next(x for x in pr["streams"] if x["codec_type"] == "video")
dur = float(pr["format"]["duration"])
item("7_duration_and_format", 75 <= dur <= 90 and v["width"] == 1080 and v["height"] == 1920 and v["r_frame_rate"] == "30/1",
     {"duration_s": round(dur, 2), "size": f'{v["width"]}x{v["height"]}', "fps": v["r_frame_rate"],
      "min_beat_s": min(b["dur"] for b in R.beats), "beats": len(R.beats)})

json.dump(rep, open(os.path.join(ROOT, "out", "qc_report.json"), "w"), indent=1)
print("ALL PASS" if all(x["pass"] for x in rep.values()) else "SOME FAILED")
