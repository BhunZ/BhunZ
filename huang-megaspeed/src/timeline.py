"""Assemble per-section VO into one narration track and a global word timeline.

Writes build/narration.wav (48 kHz mono) and build/words.json.
Each section is trimmed to its speech span (+pad) and placed after a fixed gap.
"""
import json, os
import numpy as np, soundfile as sf
from scipy.signal import resample_poly

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, "build")
SR = 48000
LEAD = 0.40          # silence before first word
GAP = 0.25           # silence between sections
PAD = 0.06           # kept around each section's speech span
END_CARD = 3.2       # seconds after last word
SECS = ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]


def build():
    out, words, t = [], [], LEAD
    out.append(np.zeros(int(LEAD * SR), np.float32))
    sec_spans = {}
    for i, s in enumerate(SECS):
        meta = json.load(open(os.path.join(B, "vo", f"{s}.json")))
        a, sr = sf.read(os.path.join(B, "vo", f"{s}.wav"), dtype="float32")
        a = resample_poly(a, 2, 1).astype(np.float32)  # 24k -> 48k
        w0, w1 = meta["words"][0]["s"] - PAD, meta["words"][-1]["e"] + PAD
        w0 = max(0.0, w0)
        seg = a[int(w0 * SR):int(w1 * SR)]
        # 10 ms fades to avoid clicks at the trim points
        f = int(0.01 * SR)
        seg[:f] *= np.linspace(0, 1, f); seg[-f:] *= np.linspace(1, 0, f)
        start = t
        for w in meta["words"]:
            words.append({"i": len(words), "sec": s, "w": w["w"],
                          "s": round(start + w["s"] - w0, 4), "e": round(start + w["e"] - w0, 4)})
        out.append(seg)
        t += len(seg) / SR
        sec_spans[s] = [round(start, 4), round(t, 4)]
        if i < len(SECS) - 1:
            out.append(np.zeros(int(GAP * SR), np.float32)); t += GAP
    out.append(np.zeros(int(END_CARD * SR), np.float32)); t += END_CARD
    nar = np.concatenate(out)
    sf.write(os.path.join(B, "narration.wav"), nar, SR, subtype="PCM_24")
    json.dump({"duration": round(len(nar) / SR, 4), "sections": sec_spans, "words": words},
              open(os.path.join(B, "words.json"), "w"), indent=1)
    return len(nar) / SR, words, sec_spans


if __name__ == "__main__":
    d, words, spans = build()
    print("duration", round(d, 2), "words", len(words))
    print(spans)
    for w in words:
        print(w["i"], w["sec"], w["w"], w["s"], w["e"])
