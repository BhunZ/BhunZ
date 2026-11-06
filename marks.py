"""Artist mark for the profile: drawn from scratch, deliberately unrelated to the legal signature.

Each mark is a list of (path, relative_weight) strokes in its own box, drawn as smooth monoline ink.
"""

# Option B: a lowercase "bh" ligature in one breath, finished with a four-point star.
MARK_B = dict(
    w=480, h=320,
    strokes=[
        ("M30,262 C62,236 92,180 112,112 C122,72 120,46 108,50 C96,56 92,122 88,182 "
         "C85,218 84,246 86,264 C108,232 138,212 160,222 C182,234 172,270 140,270 "
         "C118,270 104,264 100,258 C132,264 154,252 172,232 C196,190 214,120 226,70 "
         "C234,40 220,38 213,68 C204,130 198,210 194,264 C202,230 222,204 244,206 "
         "C266,208 262,242 258,262 C256,276 274,272 296,252 C330,226 380,222 424,236", 0.88),
        ("M440,196 C442,212 444,214 460,216 C444,218 442,220 440,236 C438,220 436,218 420,216 "
         "C436,214 438,212 440,196 Z", 0.12),
    ],
)

MARKS = {"B": MARK_B}


def mark_svg(mark, x, y, height, uid, color="#FFFFFF", px=2.2, delay=0.3, dur=2.6):
    """Inline SVG group that writes the mark stroke by stroke (needs MARK_CSS in the document)."""
    s = height / mark["h"]
    out, t = [], delay
    for d, wgt in mark["strokes"]:
        span = dur * wgt
        out.append(f'<path class="ink" d="{d}" pathLength="1" fill="none" stroke="{color}" stroke-width="{px / s:.2f}" '
                   f'stroke-linecap="round" stroke-linejoin="round" '
                   f'style="animation-duration:{span:.2f}s;animation-delay:{t:.2f}s"/>')
        t += span
    return f'<g id="mark-{uid}" transform="translate({x} {y}) scale({s:.4f})">{"".join(out)}</g>'


MARK_CSS = (".ink{stroke-dasharray:1 1;stroke-dashoffset:1;animation-name:write;"
            "animation-timing-function:cubic-bezier(.45,.05,.55,.95);animation-fill-mode:forwards}"
            "@keyframes write{to{stroke-dashoffset:0}}")
