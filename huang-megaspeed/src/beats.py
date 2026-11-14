"""Storyboard: beats anchored to narration word indices (build/words.json).

Params may contain "@wN" (time of word N's start, local to the beat) or "@eN" (word N's end).
Running this file writes ../storyboard.json.
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G, R, A, M = "green", "red", "amber", "muted"

# id, start word, visual_type, params, alleged-label, sfx, ledger ids, motion
BEATS = [
 ("b01", 0,   "gpu", {"label": "NVIDIA · PRESIDENT & CEO", "push_d": 6.0}, False, ["sub_hit@0"], ["B6a"], "slow 5% push-in on GPU illustration"),
 ("b02", 8,   "gpu", {"stamp_at": "@w11", "t_off": 2.94, "push_d": 6.0}, False, ["stamp@w11"], ["B6a"], "push continues; RESIGNED stamp slams, image desaturates"),
 ("b03", 12,  "doc8k", {"reason_at": "@w15"}, False, ["whoosh@0"], ["B6a"], "document slides up, 5% push; 'reason: none' tag pops"),
 ("b04", 17,  "photo", {"img": "singapore.jpg", "kicker": "SINGAPORE", "title": "MEGASPEED INTERNATIONAL", "crop": [500, 0, 900, 1280], "dim": 0.35,
                        "credit": "Photo: Someformofhuman, CC BY-SA 3.0, Wikimedia Commons"}, False, ["whoosh@0"], ["B1a"], "Ken Burns push on skyline; title rises"),
 ("b05", 20,  "photo", {"img": "singapore.jpg", "crop": [900, 150, 900, 1100], "pan": 0.6, "chips": ["SINGAPORE-BASED", "CLOUD COMPUTING", "NVIDIA CUSTOMER"],
                        "chip_y": 380, "dim": 0.3, "credit": "Photo: Someformofhuman, CC BY-SA 3.0, Wikimedia Commons"}, False, [], ["B1a"], "slow pan right; chips pop in"),
 ("b06", 27,  "card", {"kicker": "CITED BY THE NEW YORK TIMES", "title": "TRADE RECORDS", "tsize": 130,
                       "lines": [("Purchases by Megaspeed's Malaysian affiliate, Speedmatrix", "muted")]}, False, ["slap@0"], ["B2a"], "card pops in"),
 ("b07", 35,  "map", {"stage": 1}, False, ["whoosh@0"], ["B2a"], "map: SG pin, arrow draws to Johor"),
 ("b08", 42,  "counter", {}, False, [], ["B2a"], "counter 0→4.8B; server racks stack in"),
 ("b09", 50,  "map", {"stage": 2}, True, [], ["B2c", "N5"], "camera pulls out; dashed amber arrow to 'China?'"),
 ("b10", 54,  "denied", {"who": "MEGASPEED", "when": "Company statement", "stamp_at": "@w55",
                         "quotes": ["Denies wrongdoing", "Says reviews by U.S. and Malaysian authorities, and by Nvidia, found no violations"]},
         False, ["stamp@w55"], ["B2b"], "card slides up; DENIED stamp"),
 ("b11", 57,  "card", {"kicker": "MEGASPEED STATEMENT", "kcolor": "red", "glow": "red",
                       "lines": [("“fully within the bounds of all applicable export control regulations”", "quote"),
                                 ("Megaspeed, on its operations", "muted")]}, False, [], ["B2b"], "quote card pop"),
 ("b12", 63,  "headline", {"outlet": "The New York Times", "date": "Oct 29, 2026",
                           "text": "Reported: U.S. intelligence officials believe a former Megaspeed executive is a Chinese intelligence asset.",
                           "foot": "OUR SUMMARY OF THE REPORT, NOT ITS HEADLINE"}, True, ["slap@0"], ["B3a"], "paper card slaps in, slight tilt"),
 ("b13", 69,  "card", {"kicker": "ANONYMOUS SOURCES · ALLEGED", "kcolor": "amber", "glow": "amber", "title": "U.S. INTELLIGENCE OFFICIALS",
                       "lines": [("reportedly believe…", "muted")]}, True, ["glitch@w71"], ["B3a"], "card pop; glitch on 'intelligence'"),
 ("b14", 74,  "silhouette", {"label_at": 0.2}, True, ["whoosh@0"], ["B3e"], "neutral silhouette card; label fades in"),
 ("b15", 78,  "silhouette", {"label_at": -1, "zoom": 1.05}, True, [], ["B3e"], "tighter reframe of silhouette card"),
 ("b16", 83,  "card", {"kicker": "ALLEGED", "kcolor": "amber", "glow": "amber", "title": "NOT PROVEN", "tsize": 150, "tcolor": "amber",
                       "lines": [("The reported view of U.S. intelligence officials, per The New York Times.", "muted"), ("China denies it.", "body")]},
         True, ["glitch@w86"], ["B3a", "B3c"], "type card pop; glitch on 'intelligence'"),
 ("b17", 88,  "card", {"kicker": "ALSO REPORTED BY THE TIMES", "kcolor": "amber", "glow": "amber", "title": "A CLOSE RELATIONSHIP WITH JENSEN HUANG", "tsize": 92},
         True, [], ["B3a"], "type card pop"),
 ("b18", 96,  "denied", {"who": "NVIDIA", "when": "Statement · Oct 29, 2026", "stamp_at": "@w100",
                         "quotes": ["Interactions “not unusual”", "Megaspeed is one of many regional cloud customers; diversion claims “investigated and debunked”"]},
         False, ["whoosh@0", "stamp@w100"], ["B3b"], "card slides up; DENIED stamp"),
 ("b19", 102, "denied", {"who": "CHINA'S FOREIGN MINISTRY", "when": "Briefing · Oct 30, 2026", "stamp_at": "@w108",
                         "quotes": ["“groundless speculation”", "Says the report aims to smear China"]},
         False, ["stamp@w108"], ["B3c"], "card slides up; DENIED stamp"),
 ("b20", 109, "card", {"kicker": "NOV 8, 2026", "title": "EMAIL TO NVIDIA EMPLOYEES", "tsize": 104,
                       "lines": [("Jensen Huang", "muted")]}, False, ["whoosh@0"], ["B4a"], "card pop"),
 ("b21", 115, "letter", {"type_from": "@w115", "type_to": "@e120"}, False, ["type@w115-@e120"], ["B4a"], "letter card; quote types on"),
 ("b22", 121, "letter", {"typed": True, "enter": False, "note": "NAMED NO ONE", "note_at": 0.05}, False, [], ["B4b"], "note tag pops on letter"),
 ("b23", 125, "card", {"kicker": "IN THE SAME EMAIL", "title": "LINKED IT TO THE NATIONAL-SECURITY CONCERNS IN NEWS REPORTS", "tsize": 82},
         False, [], ["B4b"], "type card pop"),
 ("b24", 134, "card", {"kicker": "HUANG", "title": "PLEDGED TO COOPERATE", "tsize": 116,
                       "lines": [("with the board's review", "muted")]}, False, [], ["B4b"], "type card pop"),
 ("b25", 138, "board", {}, False, ["whoosh@0"], ["B4c"], "diagram builds top-down"),
 ("b26", 144, "boardquote", {"hl": [], "push_d": 5.3}, False, [], ["B4d"], "quote card slides in"),
 ("b27", 152, "boardquote", {"hl": ["national", "security"], "enter": False, "t_off": "@b", "push_d": 5.3}, False, [], ["B4d"], "highlight 'national security'"),
 ("b28", 156, "boardquote", {"hl": ["nvidia", "secrets", "compromised"], "enter": False, "t_off": "@b", "push_d": 5.3}, False, [], ["B4d"], "highlight 'NVIDIA secrets … compromised'"),
 ("b29", 159, "card", {"kicker": "REPORTED BY THE NEW YORK TIMES", "kcolor": "amber", "glow": "amber",
                       "title": "JUSTICE DEPARTMENT TAKES OVER FEDERAL MEGASPEED PROBE", "tsize": 84,
                       "lines": [("DOJ does not comment on ongoing investigations", "muted")]}, True, ["whoosh@0", "riser@0-@w172"], ["B5b"], "card pop; tension riser starts"),
 ("b30", 169, "status", {"rows": [["Singapore police", "Investigation ongoing (MHA)", "green"],
                                  ["U.S. Justice Department", "Criminal inquiry, as reported", "amber"],
                                  ["Charges", "None reported", "muted"]]}, True, [], ["B2c", "B5b"], "rows slide in"),
 ("b31", 172, "doc8k", {"date_at": "@w174"}, False, ["sub_hit@0"], ["B6a"], "8-K recreation slides up; date tag"),
 ("b32", 178, "doc8k", {"highlight_at": 0.0, "stamp_at": "@w179"}, False, ["stamp@w179"], ["B6a"], "highlight swipe over 'accepted the resignation'; RESIGNED stamp"),
 ("b33", 180, "headline", {"outlet": "TechCrunch", "date": "Nov 12, 2026",
                           "text": "“Nvidia's Jensen Huang resigns, chipmaker names CFO Colette Kress as interim CEO”",
                           "foot": "HEADLINE AS PUBLISHED, RECREATED AS TEXT"}, False, ["slap@0"], ["B6b"], "paper card slaps in"),
 ("b34", 183, "orgchart", {}, False, [], ["B6a", "B6b", "B6c"], "three role cards stack in"),
 ("b35", 186, "headline", {"outlet": "CNN", "date": "Nov 11, 2026", "bgimg": "capitol.jpg", "crop": [400, 120, 1120, 560],
                           "text": "“Jensen Huang summoned to testify before Congress after resigning as Nvidia CEO”",
                           "foot": "HEADLINE AS PUBLISHED, RECREATED AS TEXT"}, False, ["whoosh@0", "slap@0.1"], ["B7b"], "paper card over blurred Capitol"),
 ("b36", 194, "photo", {"img": "capitol.jpg", "crop": [560, 150, 800, 520], "kicker": "REPORTED", "kcolor": "amber", "title": "AGREED IN PRINCIPLE",
                        "chips": ["CLOSED-DOOR INTERVIEW", "DATE UNDER NEGOTIATION"], "chip_y": 660, "dim": 0.35,
                        "credit": "Photo: Architect of the Capitol, public domain, Wikimedia Commons"}, False, [], ["B7c"], "Ken Burns on Capitol dome"),
 ("b37", 199, "photo", {"img": "capitol.jpg", "crop": [180, 160, 1560, 520], "pan": -0.6, "kicker": "BIPARTISAN PRESSURE", "title": "TESTIMONY EXPECTED", "tsize": 96,
                        "dim": 0.4, "credit": "Photo: Architect of the Capitol, public domain, Wikimedia Commons"}, False, ["whoosh@0"], ["B7e"], "slow pan across Capitol"),
 ("b37b", 203, "photo", {"img": "capitol.jpg", "crop": [700, 160, 900, 520], "pan": 0.5, "kicker": "REPORTED", "kcolor": "amber",
                        "chips": ["HOUSE: INTERVIEW DEMANDED", "SENATE BANKING: TESTIMONY REQUEST", "LETTER TO DOJ, COMMERCE, STATE, DNI"], "chip_y": 400, "dim": 0.45,
                        "credit": "Photo: Architect of the Capitol, public domain, Wikimedia Commons"}, False, [], ["B7e"], "tighter crop on the dome; chips pop in"),
 ("b38", 207, "alleged", {}, True, ["whoosh@0"], ["B3a", "B5b", "B4d"], "two columns slide in"),
 ("b39", 215, "watch", {"cards": [["NOV", "17", "Nvidia earnings", "Q3 fiscal 2027 results", False],
                                  ["EARLY", "DEC", "Congress interview", "Requested; date being negotiated", False]], "delay": 0.15}, False, [], ["N3", "B7c"], "calendar cards slide in (dim)"),
 ("b40", 219, "watch", {"cards": [["NOV", "17", "Nvidia earnings", "Q3 fiscal 2027 results", True],
                                  ["EARLY", "DEC", "Congress interview", "Requested; date being negotiated", False]]}, False, [], ["N3"], "earnings card lights up"),
 ("b41", 224, "watch", {"cards": [["NOV", "17", "Nvidia earnings", "Q3 fiscal 2027 results", False],
                                  ["EARLY", "DEC", "Congress interview", "Requested; date being negotiated", True]]}, False, [], ["B7c"], "testimony card lights up"),
 ("b42", "end", "end", {}, False, ["sub_hit@0"], [], "end card fades in"),
]

# Caption display overrides: start word -> (end word, display text, style)
CAPTION_GROUPS = {
    32: (34, "NEW YORK TIMES", G),
    42: (46, "$4.8 BILLION", G),
    64: (65, "OCT. 29", G),
    110: (111, "NOV. 8", G),
    173: (174, "NOV. 11", G),
    222: (223, "NOV. 17", G),
}
CAPTION_TEXT = {115: "“I", 120: "WIFE.”", 100: "“NOT", 101: "UNUSUAL.”"}
EMPH = {
    G: {"jensen", "huang", "huang's", "nvidia", "nvidia's", "megaspeed", "alice", "colette", "kress", "times",
        "resigned", "resignation", "december", "proven", "cfo", "ceo"},
    R: {"denies", "groundless", "not", "unusual", "none"},
}
GLITCH_WORDS = {71, 86}


def resolve(words, beats_out):
    """Compute beat start/end and resolve @w/@e markers to local seconds."""
    total = json.load(open(os.path.join(ROOT, "build", "words.json")))["duration"]
    starts = []
    for b in BEATS:
        if b[1] == "end":
            starts.append(round(words[-1]["e"] + 0.30, 3))
        else:
            starts.append(0.0 if b[1] == 0 else round(words[b[1]]["s"] - 0.06, 3))
    out = []
    for i, b in enumerate(BEATS):
        bid, w0, vt, params, alleged, sfx, ledger, motion = b
        st = starts[i]; en = starts[i + 1] if i + 1 < len(BEATS) else total

        def rv(v):
            if isinstance(v, str):
                m = re.fullmatch(r"@([we])(\d+)", v)
                if m:
                    w = words[int(m.group(2))]
                    return round((w["s"] if m.group(1) == "w" else w["e"]) - st, 3)
                if v == "@b":
                    # time offset from the first beat of a continuing group (for continuous push)
                    j = i
                    while j > 0 and BEATS[j][3].get("enter") is False:
                        j -= 1
                    return round(st - starts[j], 3)
            return v
        p = {k: rv(v) for k, v in params.items()}
        sfx_abs = []
        for s in sfx:
            name, at = s.split("@", 1)
            at = "-".join(x if re.fullmatch(r"[\d.]+", x) or x.startswith("@") else "@" + x for x in at.split("-"))
            if "-" in at:
                a0, a1 = at.split("-")
                t0 = st + (rv(a0) if a0.startswith("@") else float(a0))
                t1 = st + (rv(a1) if a1.startswith("@") else float(a1))
                sfx_abs.append({"sfx": name, "t": round(t0, 3), "t_end": round(t1, 3)})
            else:
                sfx_abs.append({"sfx": name, "t": round(st + (rv(at) if at.startswith("@") else float(at)), 3)})
        if w0 == "end":
            nw = []
        else:
            nxt = BEATS[i + 1][1] if i + 1 < len(BEATS) else "end"
            last = len(words) if nxt == "end" else nxt
            nw = [w["w"] for w in words[w0:last]]
        emph = [w for w in nw if w.lower().strip(".,\"") in EMPH[G] | EMPH[R]]
        out.append({"id": bid, "start": round(st, 3), "end": round(en, 3), "dur": round(en - st, 3),
                    "narration_words": " ".join(nw), "caption_emphasis": emph, "visual_type": vt,
                    "asset_path_or_spec": p, "motion": motion,
                    "overlay": "ALLEGATIONS · UNDER INVESTIGATION" if alleged else None,
                    "sfx": sfx_abs, "ledger_ids": ledger})
    return out


def captions(words):
    ev, i = [], 0
    while i < len(words):
        if i in CAPTION_GROUPS:
            j, txt, sty = CAPTION_GROUPS[i]
        else:
            j = i
            raw = words[i]["w"]
            txt = CAPTION_TEXT.get(i, raw.upper())
            key = raw.lower().strip(".,\"")
            sty = G if key in EMPH[G] else R if key in EMPH[R] else None
        ev.append({"s": words[i]["s"], "e": words[j]["e"], "text": txt, "style": sty, "glitch": i in GLITCH_WORDS,
                   "words": [i, j]})
        i = j + 1
    for a, b in zip(ev, ev[1:]):
        gap = b["s"] - a["e"]
        a["hide"] = b["s"] if gap < 0.35 else a["e"] + 0.15
    ev[-1]["hide"] = ev[-1]["e"] + 0.3
    return ev


if __name__ == "__main__":
    W = json.load(open(os.path.join(ROOT, "build", "words.json")))
    sb = resolve(W["words"], None)
    json.dump({"fps": 30, "size": [1080, 1920], "duration": W["duration"], "beats": sb},
              open(os.path.join(ROOT, "storyboard.json"), "w"), indent=1)
    for b in sb:
        flag = " <1.0!" if b["dur"] < 1.0 else (" >3.2" if b["dur"] > 3.2 else "")
        print(b["id"], b["start"], b["end"], b["dur"], b["visual_type"], flag)
    print(len(sb), "beats")
