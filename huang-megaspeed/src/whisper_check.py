"""Independent check of the TTS: transcribe each section with faster-whisper and
compare (a) the words heard vs the script, and (b) word start times vs Kokoro's timestamps.
Writes build/vo/whisper_check.json. Used for the caption-sync QC (≤80 ms)."""
import json, glob, os, re, difflib, statistics
from faster_whisper import WhisperModel
import soundfile as sf, numpy as np
from scipy.signal import resample_poly

def load16(path):
    a, sr = sf.read(path, dtype="float32")
    return resample_poly(a, 2, 3).astype(np.float32) if sr == 24000 else a


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VO = os.path.join(ROOT, "build", "vo")
norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())

model = WhisperModel("small.en", device="cpu", compute_type="int8")
report = {}
all_d = []
for jf in sorted(glob.glob(os.path.join(VO, "S*.json"))):
    k = json.load(open(jf))
    sec = k["section"]
    segs, _ = model.transcribe(load16(os.path.join(VO, f"{sec}.wav")), word_timestamps=True,
                               beam_size=5, language="en", condition_on_previous_text=False)
    ww = [{"w": w.word.strip(), "s": w.start, "e": w.end} for s in segs for w in s.words]
    a = [norm(x["w"]) for x in k["words"]]
    b = [norm(x["w"]) for x in ww]
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    diffs, mism = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2)):
                diffs.append(round(ww[j]["s"] - k["words"][i]["s"], 3))
        else:
            mism.append({"script": [x["w"] for x in k["words"][i1:i2]], "heard": [x["w"] for x in ww[j1:j2]]})
    all_d += diffs
    report[sec] = {"heard": " ".join(x["w"] for x in ww), "mismatches": mism,
                   "matched": len(diffs), "median_offset_s": statistics.median(diffs) if diffs else None}
    print(sec, "matched", len(diffs), "/", len(a), "median Δ", report[sec]["median_offset_s"], "mismatch", mism)
ad = [abs(x) for x in all_d]
report["_summary"] = {"n": len(ad), "median_abs_s": statistics.median(ad),
                      "p90_abs_s": sorted(ad)[int(0.9 * len(ad)) - 1], "max_abs_s": max(ad)}
print(report["_summary"])
json.dump(report, open(os.path.join(VO, "whisper_check.json"), "w"), indent=1)
