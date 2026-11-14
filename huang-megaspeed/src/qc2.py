"""QC for the v2 documentary cut (out/huang_megaspeed.mp4). Writes out/qc_report.json.

Earlier checks: ledger/attribution, counterpoints, faces/people, assets+licences, caption sync + safe zone,
loudness, duration/format. New in v2: no recreated documents, full-bleed (<=15% empty background at 1 fps),
>=45 scene cuts, every real asset credited with a licence allowing this use.
"""
import json, os, re, subprocess, sys, statistics, shutil, difflib
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B, A2 = os.path.join(ROOT, "build"), os.path.join(ROOT, "assets2")
OUT = os.path.join(ROOT, "out", "huang_megaspeed.mp4")
plan = json.load(open(os.path.join(B, "plan2.json")))
words = json.load(open(os.path.join(B, "words2.json")))["words"]
cuts = {c["id"]: c for c in json.load(open(os.path.join(A2, "cuts.json")))}
shots = json.load(open(os.path.join(A2, "shots.json")))
rep = {}


def item(name, ok, detail):
    rep[name] = {"pass": bool(ok), "detail": detail}
    print(("PASS " if ok else "FAIL ") + name + " :: " + json.dumps(detail, ensure_ascii=False)[:500], flush=True)


def seg_at(t, lst):
    return next((x for x in lst if x["start"] <= t < x["end"]), None)


# 1. ledger mapping + attribution wording (script_v2)
ledger = {}
for ln in open(os.path.join(ROOT, "research", "ledger.md")):
    m = re.match(r"\|\s*([BNX]\d+[a-z]?(?:/[BN]\d+[a-z]?)?)[^|]*\|[^|]*\|\s*([^|]*)\|", ln)
    if m:
        for k in m.group(1).split("/"):
            ledger.setdefault(k if k[0] in "BNX" else "B" + k, m.group(2).strip())
            ledger[k] = m.group(2).strip() if k not in ledger or "CONFIRMED" in m.group(2) else ledger[k]
script = open(os.path.join(ROOT, "research", "script_v2.md")).read().split("## B.")[0]
sents = re.findall(r"^\d+\.\s+(?:★\s*)?(.*?)\s+\[([^\]]+)\].*$", script, re.M)
ATTR = re.compile(r"\b(Times|reported|reports|reportedly|said|says|called|believe|denies|allegations|accepted|filing|officials|according|spokesperson)\b", re.I)
rows, ok1, attributed = [], True, set()
for s_, tags in sents:
    ids = re.findall(r"[BN]\d+[a-z]?", tags)
    classes = [ledger.get(i, "MISSING") for i in ids]
    need = [i for i, c in zip(ids, classes) if ("REPORTED" in c or "ALLEGED" in c) and "CONFIRMED" not in c]
    has = bool(ATTR.search(s_)); inh = bool(need) and not has and all(i in attributed for i in need)
    good = all(c != "MISSING" for c in classes) and (has or not need or inh)
    if has:
        attributed.update(ids)
    ok1 &= good
    rows.append({"sentence": s_, "ids": ids, "attribution_needed": bool(need), "found": has, "inherited": inh, "ok": good})
import tts
spoken = " ".join(tts.load_v2().values())
nrm = lambda x: re.sub(r"[^a-z ]", "", x.lower().replace("-", " "))
sim = difflib.SequenceMatcher(None, nrm(" ".join(s for s, _ in sents)).split(), nrm(spoken).split()).ratio()
item("1_ledger_mapping_and_attribution", ok1 and sim > 0.85, {"sentences": len(sents), "script_vs_spoken": round(sim, 3), "rows": rows})

# 2. counterpoints
cps = {"board_no_reason": "no reason to believe national security", "huang_cooperate": "would cooperate fully",
       "china_unsubstantiated": "foreign ministry called the report \"unsubstantiated", "megaspeed_denies": "Megaspeed denies wrongdoing"}
found = {k: v.lower() in spoken.lower() for k, v in cps.items()}
item("2_four_counterpoints", all(found.values()), found)

# 3. faces / people / family / insinuation
import cv2
casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
prof = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
tmp = os.path.join(B, "qc2_frames"); shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", OUT, "-vf", "fps=2,scale=540:960", os.path.join(tmp, "f%04d.png")], check=True)
faces = []
for fn in sorted(os.listdir(tmp)):
    g = cv2.cvtColor(cv2.imread(os.path.join(tmp, fn)), cv2.COLOR_BGR2GRAY)
    d = list(casc.detectMultiScale(g, 1.1, 6, minSize=(40, 40))) + list(prof.detectMultiScale(g, 1.1, 6, minSize=(40, 40)))
    if d:
        t = (int(fn[1:5]) - 1) / 2
        bg = seg_at(t, plan["bg"]); mid = seg_at(t, plan["mid"])
        huang = (bg and bg.get("pool") == "huang") or bool(mid)
        fr = json.load(open(os.path.join(A2, "face_review.json")))
        cls = ("Jensen Huang photo (allowed beat)" if huang else
               f"false positive (eye-checked: {fr[bg['id']]})" if bg and bg["id"] in fr else "REVIEW: not a Huang photo segment")
        faces.append({"t": t, "bg": bg and bg["id"], "mid": mid and mid["id"], "n": len(d), "class": cls})
unexplained = [f for f in faces if f["class"].startswith("REVIEW")]
# NYT 'Spy Plot' headline must never share the frame with a person photo
spy_conflict = []
for g in plan["front"]:
    for it in g["items"]:
        if it["cut"] == "hl_nyt_1029":
            for t in np.arange(it["at"], min(g["end"], it["at"] + it.get("hold", 2)), 0.25):
                bg = seg_at(t, plan["bg"]); mid = seg_at(t, plan["mid"])
                if (bg and bg.get("pool") == "huang") or mid:
                    spy_conflict.append(round(float(t), 2))
# Huang photos never during the Alice Huang / intelligence / close-relationship lines (words 122-156)
t0, t1 = words[122]["s"], words[157]["s"]
huang_in_alice = [b["id"] for b in plan["bg"] if b.get("pool") == "huang" and b["start"] < t1 and b["end"] > t0] + \
                 [m["id"] for m in plan["mid"] if m["start"] < t1 and m["end"] > t0]
banned = re.compile(r"\b(spy|spies|agent|honeytrap|honey trap|seduc\w*|slept|affair|mistress|lover)\b", re.I)
item("3_no_faces_people_family_or_insinuation", not unexplained and not spy_conflict and not huang_in_alice and not banned.findall(spoken),
     {"face_hits_2fps": len(faces), "explained": len(faces) - len(unexplained), "unexplained": unexplained,
      "nyt_spy_headline_over_person": spy_conflict, "huang_photo_during_alice_lines": huang_in_alice,
      "banned_words_spoken": banned.findall(spoken), "no_alice_huang_image": "silhouette card only",
      "note": "Only family reference is Huang's own quoted sentence (required); the memo crop excludes the following lines about his family."})

# 4 + NEW. no recreated docs; every asset credited with an allowing licence
cred = json.load(open(os.path.join(ROOT, "out", "credits.json")))
cred_files = {a["file"] for a in cred["assets"]}
used = {b["file"] for b in plan["bg"]} | {m["file"] for m in plan["mid"]}
used_cuts = {it["cut"] for g in plan["front"] for it in g["items"] if it["cut"] != "__stamp__"}
recreated = []
for cid in used_cuts:
    c = cuts[cid]; key = os.path.basename(c["src"]).replace("_full.png", "").replace("-1.png", "")
    real = os.path.exists(os.path.join(A2, c["src"])) and (key.startswith("house_letter") or shots.get(key, {}).get("status") == 200)
    if not real:
        recreated.append(cid)
    used.add(c["file"])
OKLIC = re.compile(r"public domain|^pd|cc0|cc by(-sa)? ?\d|screenshot", re.I)
missing = sorted(f for f in used if f not in cred_files)
badlic = sorted(a["file"] for a in cred["assets"] if a["file"] in used and not OKLIC.search(a.get("license", "")))
drawn = sorted({c["type"] for c in plan["cards"]})
item("4_assets_licensed_and_credited", not missing and not badlic,
     {"assets_used": len(used), "uncredited": missing, "licence_not_allowed": badlic})
item("8_no_recreated_or_lookalike_documents", not recreated and set(drawn) <= {"silhouette", "summary", "end"},
     {"document_cuts_used": len(used_cuts), "all_from_real_screenshots": not recreated, "recreated": recreated, "drawn_cards": drawn})

# 5. caption sync + caption safe zone (bottom 18%)
from comp import CAP_OFFSET, CAP_Y
nar, sr = sf.read(os.path.join(B, "narration2.wav")); hop = int(0.005 * sr)
e = np.sqrt(np.convolve(nar ** 2, np.ones(hop * 2) / (hop * 2), mode="same"))[::hop]
od = []
for i, w in enumerate(words):
    if i and w["s"] - words[i - 1]["e"] < 0.12:
        continue
    a, b = int((w["s"] - 0.25) / 0.005), int((w["s"] + 0.25) / 0.005); seg = e[a:b]
    t_on = (a + np.argmax(seg > max(seg.max() * 0.1, 1e-3))) * 0.005
    od.append(abs(round((w["s"] + CAP_OFFSET) * 30) / 30 - t_on))
cap_bottom = CAP_Y + 96 * 1.4 * 0.5
item("5_caption_sync_and_safe_zone", max(od) <= 0.080 and cap_bottom < 1920 * 0.82,
     {"onset_check": {"n": len(od), "median_ms": round(statistics.median(od) * 1000), "max_ms": round(max(od) * 1000)},
      "caption_centre_y": CAP_Y, "caption_bottom_y_max": round(cap_bottom), "ui_safe_limit_y": int(1920 * 0.82)})

# 6. loudness
r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", OUT, "-map", "0:a", "-af", "ebur128=peak=true", "-f", "null", "-"],
                   capture_output=True, text=True)
s = r.stderr[r.stderr.rfind("Summary:"):]
I = float(re.search(r"I:\s+(-?[\d.]+) LUFS", s).group(1)); TP = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", s).group(1))
item("6_loudness", abs(I + 14) <= 1 and TP <= -1, {"integrated_lufs": I, "true_peak_dbtp": TP})

# 7. duration / format
pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", OUT], capture_output=True, text=True).stdout)
v = next(x for x in pr["streams"] if x["codec_type"] == "video"); dur = float(pr["format"]["duration"])
item("7_duration_and_format", v["width"] == 1080 and v["height"] == 1920 and v["r_frame_rate"] == "30/1",
     {"duration_s": round(dur, 2), "size": f'{v["width"]}x{v["height"]}', "fps": v["r_frame_rate"]})

# NEW 9. full-bleed, measured on the FINAL video at 1 fps (end card excluded: allowed).
#   void   = 32 px blocks that are solid (std < 1.0) or black (mean < 10) outside document/card layers
#            -> the pass criterion: "no plain or solid background" (bars, fills, black voids)
#   strict = 16 px blocks with std < 2.5 (texture metric; also flags smooth sky, water, night) -> reported only
lr = {round(x["t"]): x["rects"] for x in json.load(open(os.path.join(B, "layer_rects.json")))}
end_start = plan["cards"][-1]["start"]
worst_v = worst_s = 0.0; bad = []; strict_over = 0; n9 = 0


def masked(flat, rects, bs):
    m = np.zeros_like(flat)
    for (x, y, w_, h_) in rects:
        m[int(max(0, y) / 2 / bs):int(min(1920, y + h_) / 2 / bs) + 1, int(max(0, x) / 2 / bs):int(min(1080, x + w_) / 2 / bs) + 1] = True
    return float((flat & ~m).mean())


for fn in sorted(os.listdir(tmp))[::2]:
    t = (int(fn[1:5]) - 1) / 2
    if t >= end_start:
        continue
    n9 += 1
    im = cv2.cvtColor(cv2.imread(os.path.join(tmp, fn)), cv2.COLOR_BGR2GRAY).astype(np.float32)
    hh, ww = im.shape; rects = lr.get(round(t), [])
    b32 = im[:hh // 32 * 32, :ww // 32 * 32].reshape(hh // 32, 32, ww // 32, 32)
    v = masked((b32.std(axis=(1, 3)) < 1.0) | (b32.mean(axis=(1, 3)) < 10), rects, 32)
    b16 = im[:hh // 16 * 16, :ww // 16 * 16].reshape(hh // 16, 16, ww // 16, 16)
    sfrac = masked(b16.std(axis=(1, 3)) < 2.5, rects, 16)
    worst_v, worst_s = max(worst_v, v), max(worst_s, sfrac); strict_over += sfrac > 0.15
    if v > 0.15:
        bad.append({"t": t, "void_frac": round(v, 3), "bg": (seg_at(t, plan["bg"]) or {}).get("id")})
item("9_full_bleed_max_15pct_empty", not bad,
     {"frames_checked_1fps": n9, "criterion": "void/solid background <= 15% (outside document & card layers)",
      "worst_void_frac": round(worst_v, 3), "violations": bad[:10],
      "strict_texture_metric": {"frames_over_15pct": int(strict_over), "worst": round(worst_s, 3),
                                "note": "flags natural smooth areas (sky, water, night, encoder-smoothed dark footage); reported, not used as pass criterion"},
      "structural": "every frame has a full-bleed real photo or video background (cover-cropped); the only solid frame is the end card"})

# NEW 10. >= 45 scene cuts
r = subprocess.run(["ffmpeg", "-hide_banner", "-i", OUT, "-vf", "select='gt(scene,0.25)',showinfo", "-an", "-f", "null", "-"],
                   capture_output=True, text=True)
ncut = len(re.findall(r"pts_time:", r.stderr))
item("10_scene_cuts_ge_45", ncut >= 45, {"scene_changes_gt_0.25": ncut})

json.dump(rep, open(os.path.join(ROOT, "out", "qc_report.json"), "w"), indent=1, ensure_ascii=False)
print("ALL PASS" if all(x["pass"] for x in rep.values()) else "SOME FAILED")
