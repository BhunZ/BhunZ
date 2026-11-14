"""Fast proxy for QC item 9: render 1 fps WITHOUT grain (stricter than the encoded file) and report empty fractions."""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comp import Comp, ROOT
plan = json.load(open(os.path.join(ROOT, "build", "plan2.json")))
C = Comp(plan); out = []
for t in range(0, int(plan["cards"][-1]["start"])):
    a = C.frame(t + 0.0, post=False)
    g = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2])[::2, ::2]
    bs = 16; hh, ww = g.shape
    flat = g[:hh // bs * bs, :ww // bs * bs].reshape(hh // bs, bs, ww // bs, bs).std(axis=(1, 3)) < 2.5
    mask = np.zeros_like(flat)
    for (x, y, w, h) in C.layer_rects:
        mask[int(max(0, y) / 2 / bs):int(min(1920, y + h) / 2 / bs) + 1, int(max(0, x) / 2 / bs):int(min(1080, x + w) / 2 / bs) + 1] = True
    fr = float((flat & ~mask).mean()); bg = C.seg_at(t)
    bs2 = 32; g2 = g[:hh // bs2 * bs2, :ww // bs2 * bs2].reshape(hh // bs2, bs2, ww // bs2, bs2)
    void = (g2.std(axis=(1, 3)) < 1.0) | (g2.mean(axis=(1, 3)) < 10)
    m2 = np.zeros_like(void)
    for (x, y, w, h) in C.layer_rects:
        m2[int(max(0, y) / 2 / bs2):int(min(1920, y + h) / 2 / bs2) + 1, int(max(0, x) / 2 / bs2):int(min(1080, x + w) / 2 / bs2) + 1] = True
    vf = float((void & ~m2).mean())
    out.append((round(vf, 3), round(fr, 3), t, bg["id"]))
out.sort(reverse=True)
print("worst", out[:12]); print("VOID over 15%:", sum(1 for x in out if x[0] > 0.15), "of", len(out), "| strict texture over 15%:", sum(1 for x in out if x[1] > 0.15))
json.dump(out, open(os.path.join(ROOT, "build", "fullbleed_probe.json"), "w"))
