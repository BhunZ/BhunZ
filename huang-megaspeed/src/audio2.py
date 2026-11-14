"""v2 audio: narration2 + synthesized music bed (ducked 12 dB) + SFX driven by plan2, mastered to -14 LUFS / -1 dBTP."""
import json, os, re, subprocess, sys
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio as A

ROOT = A.ROOT; B = A.B; SR = A.SR


def main():
    nar, sr = sf.read(os.path.join(B, "narration2.wav"), dtype="float64")
    plan = json.load(open(os.path.join(B, "plan2.json")))
    words = json.load(open(os.path.join(B, "words2.json")))["words"]
    total = len(nar) / SR
    mus = A.music(total) * A.db(-11)
    mus_d = mus * A.duck_gain(nar, 12.0)
    sfx = np.zeros(len(nar)); events = []

    def place(x, t, g):
        i0 = int(round(t * SR))
        if 0 <= i0 < len(sfx):
            m = min(len(x), len(sfx) - i0); sfx[i0:i0 + m] += x[:m] * A.db(g)

    W, SL, ST, GL, SH = A.sfx_whoosh(), A.sfx_slap(), A.sfx_stamp(), A.sfx_glitch(), A.sfx_sub_hit()
    for j, g in enumerate(plan["front"]):
        if g["trans"] in ("whip", "slide", "zoom"):
            place(W, g["start"] - 0.2, -14); events.append({"sfx": "whoosh", "t": g["start"]})
        if g["trans"] == "flash":
            place(SL, g["start"], -13); events.append({"sfx": "flash_hit", "t": g["start"]})
        for k, it in enumerate(g["items"]):
            if it["cut"] != "__stamp__" and k % 2 == 0:
                place(SL, it["at"] + 0.02, -16); events.append({"sfx": "paper_slap", "t": it["at"]})
            if it.get("stamp"):
                t = it["at"] + it.get("stamp_at", 0.25) if it["cut"] != "__stamp__" else it["at"]
                place(ST, t - 0.02, -10); events.append({"sfx": "stamp", "t": t, "what": it["stamp"]})
    for fi in plan["glitch_frames"]:
        place(GL, fi / 30, -12); events.append({"sfx": "glitch", "t": fi / 30})
    t_res = [w["s"] for w in words if w["w"].lower() == "then"][0]          # "Then, on November eleventh..."
    place(A.riser(4.0), t_res - 4.0, -12); events.append({"sfx": "riser", "t": t_res - 4.0, "t_end": t_res})
    for t in (0.0, t_res, plan["cards"][-1]["start"]):
        place(SH, t, -9); events.append({"sfx": "sub_hit", "t": t})

    mix = nar + mus_d + sfx
    st = np.stack([mix, mix], 1); st /= max(1.0, np.abs(st).max() / 0.9)
    pre = os.path.join(B, "mix2_premaster.wav"); sf.write(pre, st.astype(np.float32), SR, subtype="FLOAT")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", pre, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = json.loads(re.findall(r"\{[^{}]+\}", r.stderr)[-1])
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
          f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000")
    out = os.path.join(B, "master2.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", pre, "-af", af, "-ar", "48000", "-c:a", "pcm_s24le", out], check=True)
    json.dump({"sfx_events": events}, open(os.path.join(B, "audio2_events.json"), "w"), indent=1)
    print("master2 written;", len(events), "sfx events")


if __name__ == "__main__":
    main()
