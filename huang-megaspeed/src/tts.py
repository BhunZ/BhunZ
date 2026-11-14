"""Generate narration per section with Kokoro TTS and record word timestamps.

Usage: python src/tts.py [SECTION ...]   (no args = all sections)
Outputs build/vo/<sec>.wav and build/vo/<sec>.json (word timings relative to section start).
Deterministic: Kokoro inference on CPU with fixed voice/speed.
"""
import json, sys, os, warnings
warnings.filterwarnings("ignore")
import numpy as np, soundfile as sf
from kokoro import KPipeline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build", "vo")
os.makedirs(OUT, exist_ok=True)

VOICE = "af_heart"
SPEED = 1.2
SR = 24000

# Spoken text per section (VO-friendly version from research/script.md).
SECTIONS = {
    "S1": "Two weeks ago, Jensen Huang was running Nvidia. This week, he resigned. The filing gives no reason.",
    "S2": ("Start with Megaspeed. A Singapore cloud firm, and Nvidia customer. "
           "Trade records cited by The New York Times show its Malaysian affiliate bought at least "
           "four point eight billion dollars of Nvidia-based gear. Singapore police are investigating. "
           "Megaspeed denies wrongdoing, and says it follows export rules."),
    "S3": ("On October twenty-ninth, the Times reported that U.S. intelligence officials believe Alice Huang, "
           "a former Megaspeed executive, and no relation, is a Chinese intelligence asset. "
           "It said she was close to Jensen Huang. Nvidia called his interactions \"not unusual.\" "
           "China's foreign ministry called the claims groundless."),
    "S4": ("On November eighth, Huang told employees: \"I was unfaithful to my wife.\" He named no one. "
           "But he linked it to the national security reports, and pledged to cooperate. "
           "The board opened an independent probe. It said it has no reason to believe national security, "
           "or Nvidia secrets, were compromised."),
    "S5": ("The Times reports the Justice Department has taken over a federal Megaspeed probe. "
           "On November eleventh, the board accepted Huang's resignation. CFO Colette Kress is interim CEO."),
    "S6": ("House committees want a closed-door interview in December. Huang reportedly agreed, in principle. "
           "Senators from both parties are reportedly pressing too."),
    "S7": ("None of the espionage allegations has been proven. Here's what to watch: "
           "Nvidia's earnings on November seventeenth. And Huang's testimony."),
}


def gen(pipe, sec):
    audio, words, offset = [], [], 0.0
    for r in pipe(SECTIONS[sec], voice=VOICE, speed=SPEED, split_pattern=r"\n+"):
        a = r.audio.numpy()
        for t in r.tokens or []:
            if t.start_ts is None:
                continue
            if any(ch.isalnum() for ch in t.text):
                words.append({"w": t.text, "s": round(offset + t.start_ts, 4),
                              "e": round(offset + (t.end_ts or t.start_ts), 4)})
        audio.append(a)
        offset += len(a) / SR
    a = np.concatenate(audio).astype(np.float32)
    sf.write(os.path.join(OUT, f"{sec}.wav"), a, SR, subtype="PCM_24")
    json.dump({"section": sec, "voice": VOICE, "speed": SPEED, "sr": SR,
               "duration": len(a) / SR, "text": SECTIONS[sec], "words": words},
              open(os.path.join(OUT, f"{sec}.json"), "w"), indent=1)
    print(f"{sec}: {len(a)/SR:.2f}s, {len(words)} words")


if __name__ == "__main__":
    pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    for sec in (sys.argv[1:] or list(SECTIONS)):
        gen(pipe, sec)
