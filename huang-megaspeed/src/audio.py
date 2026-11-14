"""Synthesize music bed + SFX in code, duck music under narration, mix, master to -14 LUFS / -1 dBTP.

Deterministic (fixed RNG seeds). Outputs build/mix_premaster.wav, build/music.wav, build/sfx.wav,
build/master.wav and build/loudness.json.
"""
import json, os, subprocess, sys, re
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, sosfiltfilt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import beats as BT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, "build")
SR = 48000
rng = np.random.default_rng(20261114)


def db(x): return 10 ** (x / 20)


def lp(x, f, o=2): return sosfilt(butter(o, f, "low", fs=SR, output="sos"), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, "high", fs=SR, output="sos"), x)
def bp(x, f1, f2, o=2): return sosfilt(butter(o, [f1, f2], "band", fs=SR, output="sos"), x)


def t_(n): return np.arange(n) / SR


def env_ad(n, a, d):
    e = np.ones(n)
    na = max(1, int(a * SR)); e[:na] = np.linspace(0, 1, na)
    e[na:] = np.exp(-np.arange(n - na) / (d * SR))
    return e


# ------------------------------------------------------------------ SFX
def sfx_whoosh(dur=0.5):
    n = int(dur * SR); x = rng.normal(0, 1, n)
    out = np.zeros(n)
    bands = [(300, 900), (700, 2000), (1500, 4500), (3000, 8000)]
    for i, (a, b) in enumerate(bands):
        c = (i + 0.5) / len(bands)
        w = np.exp(-((np.linspace(0, 1, n) - c) ** 2) / 0.03)
        out += bp(x, a, b) * w
    out *= np.sin(np.linspace(0, np.pi, n)) ** 1.5
    return out / np.abs(out).max() * 0.35


def sfx_slap():
    n = int(0.25 * SR); t = t_(n)
    noise = hp(rng.normal(0, 1, n), 900) * env_ad(n, 0.001, 0.03)
    thump = np.sin(2 * np.pi * (140 - 60 * t / 0.25) * t) * env_ad(n, 0.002, 0.05)
    x = noise * 0.7 + thump * 0.6
    return x / np.abs(x).max() * 0.5


def sfx_click(i):
    n = int(0.03 * SR); t = t_(n)
    r = np.random.default_rng(100 + i)
    x = hp(r.normal(0, 1, n), 2500) * env_ad(n, 0.0005, 0.004)
    x += np.sin(2 * np.pi * (1800 + 200 * r.random()) * t) * env_ad(n, 0.0005, 0.006) * 0.4
    return x / np.abs(x).max() * 0.22


def sfx_stamp():
    n = int(0.6 * SR); t = t_(n)
    f = 95 * np.exp(-t * 6) + 40
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(n, 0.002, 0.16)
    crack = lp(rng.normal(0, 1, n), 3500) * env_ad(n, 0.0005, 0.02)
    x = body * 0.9 + crack * 0.6
    return x / np.abs(x).max() * 0.7


def sfx_glitch():
    n = int(0.2 * SR); t = t_(n)
    sq = np.sign(np.sin(2 * np.pi * 220 * t)) * 0.5 + np.sign(np.sin(2 * np.pi * 1330 * t)) * 0.3
    hold = 24; sq = np.repeat(sq[::hold], hold)[:n]
    gate = np.repeat((rng.random(n // 480 + 1) > 0.35).astype(float), 480)[:n]
    x = sq * gate * env_ad(n, 0.001, 0.08)
    return lp(x, 6000) * 0.16


def sfx_sub_hit():
    n = int(1.6 * SR); t = t_(n)
    f = 55 * np.exp(-t * 2.2) + 32
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(n, 0.003, 0.5)
    x += lp(rng.normal(0, 1, n), 400) * env_ad(n, 0.001, 0.08) * 0.3
    return x / np.abs(x).max() * 0.8


def riser(dur):
    n = int(dur * SR); t = t_(n); k = t / dur
    noise = rng.normal(0, 1, n)
    out = np.zeros(n)
    for i in range(6):          # stepped band sweep
        c0 = i / 6
        w = np.clip(1 - np.abs(k - c0 - 1 / 12) * 6, 0, 1)
        lo = 200 * 2 ** (i * 0.9); out += bp(noise, lo, lo * 2.2) * w
    tone = np.sin(2 * np.pi * np.cumsum(110 * 2 ** (k * 1.5)) / SR) * 0.25
    x = (out * 0.6 + tone) * k ** 2.2
    return x / np.abs(x).max() * 0.4


# ------------------------------------------------------------------ music bed
def music(total):
    n = int(total * SR); t = t_(n)
    x = np.zeros(n)
    # drone: detuned saws on D2/A2, low-passed
    for f, a in [(73.42, 0.5), (73.9, 0.35), (110.0, 0.25), (146.83, 0.10)]:
        saw = 2 * ((t * f) % 1) - 1
        x += saw * a
    x = lp(x, 380, 4)
    swell = 0.75 + 0.25 * np.sin(2 * np.pi * t / 11.0)
    x *= swell
    # high shimmer pad
    pad = sum(np.sin(2 * np.pi * f * t + p) for f, p in [(587.3, 0), (880.0, 1.1), (698.5, 2.3)])
    x += lp(pad, 2000) * 0.02 * (0.5 + 0.5 * np.sin(2 * np.pi * t / 7.0))
    # slow sub pulse (heartbeat-ish), from 6.2 s
    beat = 60 / 68
    pulse = np.zeros(n)
    k = 6.2
    while k < total - 3.0:
        i0 = int(k * SR); m = min(int(0.5 * SR), n - i0); tt = t_(m)
        pulse[i0:i0 + m] += np.sin(2 * np.pi * 48 * tt) * np.exp(-tt / 0.12)
        k += beat
    x += pulse * 0.55
    # fades
    fi = int(1.5 * SR); x[:fi] *= np.linspace(0, 1, fi)
    fo = int(2.5 * SR); x[-fo:] *= np.linspace(1, 0, fo)
    return x / np.abs(x).max()


def duck_gain(nar, depth_db=12.0):
    """Sidechain envelope: ~depth_db reduction while the narrator speaks."""
    a = np.abs(nar)
    win = int(0.02 * SR)
    rms = np.sqrt(np.convolve(a ** 2, np.ones(win) / win, mode="same"))
    thr = 0.02
    target = np.clip(rms / thr, 0, 1)
    # attack 30 ms, release 350 ms (one-pole, downsampled for speed)
    hop = 48
    tg = target[::hop]
    out = np.zeros_like(tg); g = 0.0
    att, rel = np.exp(-hop / (0.03 * SR)), np.exp(-hop / (0.35 * SR))
    for i, v in enumerate(tg):
        co = att if v > g else rel
        g = co * g + (1 - co) * v
        out[i] = g
    env = np.repeat(out, hop)[:len(nar)]
    return db(-depth_db * env)


def main():
    nar, sr = sf.read(os.path.join(B, "narration.wav"), dtype="float64")
    assert sr == SR
    total = len(nar) / SR
    words = json.load(open(os.path.join(B, "words.json")))["words"]
    sb = BT.resolve(words, None)

    mus = music(total) * db(-11)
    g = duck_gain(nar, 12.0)
    mus_d = mus * g

    sfx = np.zeros(len(nar))
    events = []

    def place(x, t, gain_db=0.0):
        i0 = int(round(t * SR))
        if i0 >= len(sfx):
            return
        m = min(len(x), len(sfx) - i0)
        sfx[i0:i0 + m] += x[:m] * db(gain_db)

    W = sfx_whoosh(); SL = sfx_slap(); ST = sfx_stamp(); GL = sfx_glitch(); SH = sfx_sub_hit()
    for b in sb:
        for s in b["sfx"]:
            name, t = s["sfx"], s["t"]
            if name == "whoosh":
                place(W, t - 0.22, -14)
            elif name == "slap":
                place(SL, t + 0.05, -12)
            elif name == "stamp":
                place(ST, t - 0.02, -9)
            elif name == "glitch":
                place(GL, t, -11)
            elif name == "sub_hit":
                place(SH, t, -9)
            elif name == "riser":
                place(riser(s["t_end"] - t), t, -12)
            elif name == "type":
                q = "\u201cI was unfaithful to my wife.\u201d"
                for i in range(len(q)):
                    if q[i] != " ":
                        place(sfx_click(i), t + (s["t_end"] - t) * i / len(q), -15)
            events.append({"beat": b["id"], **s})

    sf.write(os.path.join(B, "music.wav"), mus_d.astype(np.float32), SR)
    sf.write(os.path.join(B, "sfx.wav"), sfx.astype(np.float32), SR)
    mix = nar * db(0) + mus_d + sfx
    st = np.stack([mix, mix], 1)
    st /= max(1.0, np.abs(st).max() / 0.9)
    pre = os.path.join(B, "mix_premaster.wav")
    sf.write(pre, st.astype(np.float32), SR, subtype="FLOAT")

    # two-pass loudnorm to -14 LUFS, -1 dBTP
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", pre, "-af",
                        "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = json.loads(re.findall(r"\{[^{}]+\}", r.stderr)[-1])
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:"
          f"linear=true:print_format=json,aresample=48000")
    out = os.path.join(B, "master.wav")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", pre, "-af", af, "-ar", "48000",
                    "-c:a", "pcm_s24le", out], check=True)
    # measure
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", out, "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True)
    s = r.stderr[r.stderr.rfind("Summary:"):]
    I = float(re.search(r"I:\s+(-?[\d.]+) LUFS", s).group(1))
    LRA = float(re.search(r"LRA:\s+(-?[\d.]+) LU", s).group(1))
    TP = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", s).group(1))
    res = {"integrated_lufs": I, "true_peak_dbtp": TP, "lra_lu": LRA, "duck_depth_db": 12.0,
           "pass1": m, "sfx_events": events}
    json.dump(res, open(os.path.join(B, "loudness.json"), "w"), indent=1)
    print(f"I={I} LUFS  TP={TP} dBTP  LRA={LRA}  sfx={len(events)}")


if __name__ == "__main__":
    main()
