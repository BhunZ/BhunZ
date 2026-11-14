"""Contact sheet: every beat at 75% of its duration (QC aid)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
from render import Renderer, ROOT
R = Renderer(); tw, th, cols = 270, 480, 7
rows = (len(R.beats) + cols - 1) // cols
sheet = Image.new("RGB", (cols * tw, rows * th), (40, 40, 40))
for i, b in enumerate(R.beats):
    im = Image.fromarray(R.frame(b["start"] + 0.75 * b["dur"])).resize((tw, th), Image.LANCZOS)
    ImageDraw.Draw(im).text((6, 4), b["id"], fill=(255, 255, 0))
    sheet.paste(im, ((i % cols) * tw, (i // cols) * th))
sheet.save(os.path.join(ROOT, "build", "contact.png")); print("ok")
