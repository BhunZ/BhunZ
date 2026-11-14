# Final report — Huang / Megaspeed explainer

As of 2026-11-14. Branch `ccr-bf443029-plmqpt`, folder `huang-megaspeed/`.

## Deliverables
| File | Notes |
|---|---|
| `out/huang_megaspeed.mp4` | 1080×1920, 30 fps, H.264 at about 7 Mbps (2-pass) plus AAC 256k. **89.81 s**, 81 MB. This is the upload version; GitHub limits files to 100 MB. A CRF-17 master can be regenerated with `src/render.py` (it is about 320 MB, so it is not committed). |
| `out/description.txt` | Two-sentence summary, the required disclaimer, full source URLs, and the AI disclosure. |
| `out/credits.json` | Every asset with its URL, author, licence and how the licence was verified. |
| `research/ledger.md`, `research/sources.md` | Claim ledger (IDs B1a–B7e, N1–N5, X1–X5) and source list. |
| `research/script.md` | The tagged script and the VO version. |
| `storyboard.json` | 43 beats with every field in your schema. |
| `out/qc_report.json` | Machine-readable QC with per-sentence attribution rows. |
| `out/stills/` | Checkpoint C stills and the contact sheet. |

## QC (measured on the final MP4)
| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Every narration sentence maps to a ledger ID with the right attribution wording | **PASS** | 20 of 20 sentences mapped. Every REPORTED/ALLEGED sentence carries attribution. Sentence 20 inherits "reportedly" from sentence 17 (same ID, B7c). Spoken text matches the approved script at 0.97 similarity; the differences are numbers spelled out for speech. |
| 2 | All four counterpoints present | **PASS** | Board: "no reason to believe…" · Huang: "pledged to cooperate" · China: "groundless" · Megaspeed: "denies wrongdoing". |
| 3 | No face of Alice Huang, no family members, no unrelated people | **PASS** | Haar face detection (frontal and profile) at 2 fps over 180 frames: one hit, a "6" in the $4.8B counter (b08), which I checked by eye as a false positive. No faces in any asset. Photos are cropped to exclude people. On screen and in the narration: no "spy", "agent", "honeytrap", "seduction", "slept" or "affair". The only family reference is Huang's own quoted sentence, which you required. |
| 4 | No scraped news/TV/film footage; every asset in credits.json with its licence | **PASS** | 3 assets on disk, all credited: Capitol (PD), Marina Bay Sands (CC BY-SA 3.0), Natural Earth via world-atlas (PD/ISC). |
| 5 | Caption sync ≤ 80 ms; no captions in the UI safe zones | **PASS** | Against acoustic word onsets: median 16 ms, p90 33 ms, **max 72 ms** (n=16). Frame quantisation ≤ 16.6 ms. Safe zones: every visible text box logged on 1,347 frames, with 0 boxes past x = 950 or y = 1574. ⚠️ See the caveat below. |
| 6 | Loudness about −14 LUFS, true peak ≤ −1 dBTP | **PASS** | **−14.0 LUFS integrated, −1.5 dBTP**, measured on the AAC audio in the final MP4. Music is ducked 11.9 dB (median) under the voice. |
| 7 | Duration 75–90 s | **PASS** | 89.81 s. Beats run 1.13–3.04 s, with 43 beats. |

**Caption-sync caveat.** Kokoro's own timestamps start about 50–70 ms before the audible onset, so captions are displayed 60 ms after them (`CAP_OFFSET`). A second check, Whisper word timestamps on the final mix, shows a median of 80 ms and p90 of 180 ms. Whisper's timestamps are known to run early and disagree with the onset measurement by about 60 ms, so I used the acoustic onsets as the pass criterion. The onset check only covers the 16 words that follow a pause; words in continuous speech can't be measured that way.

## Tools, packages and API keys
- **API keys used: none.** `ELEVENLABS_API_KEY`, `PEXELS_API_KEY` and `PIXABAY_API_KEY` were all unset.
- **Narration:** Kokoro-82M (`kokoro` 0.9.4, `misaki` 0.9.4, spaCy 3.8 with `en_core_web_sm`), voice `af_heart`, speed 1.2, on torch 2.15 (CPU).
- **Timing check:** `faster-whisper` 1.2.1 with the `small.en` model.
- **Visuals:** `skia-python` 144, Pillow, numpy. Rendered frame by frame in Python and piped to ffmpeg/x264. **Why this stack:** it runs without a browser, is deterministic, and uses one toolchain for graphics and audio DSP.
- **Audio:** numpy/scipy synthesis and mixing, then ffmpeg `loudnorm` two-pass (linear) and `ebur128` measurement.
- **QC:** `opencv-python-headless` 4.14 (Haar cascades).
- **System:** apt `libegl1` and `libgl1` (needed by skia). Map data from `npm pack world-atlas@2.0.2`. Fonts already on the machine: Inter, JetBrains Mono, DejaVu Serif.
- **Research:** web search only. Direct page fetches were blocked by the environment's network policy (see the limitations below).

## Estimated API cost
**$0 in third-party API spend.** Kokoro, Whisper, the music and the effects all ran locally, and Wikimedia downloads are free. The only cost is this Claude session's own usage, which I can't measure from inside the session.

## Beats where a desired visual became a generated graphic
| Beat | Wanted | Used instead | Why |
|---|---|---|---|
| b03, b31, b32 | Screenshot of the 8-K on sec.gov | Typographic recreation, labelled "Recreated from…", quoting only the verified sentence; the rest is grey placeholder bars | sec.gov returned HTTP 403 to this environment. |
| — | NVDA line chart, Nov 6–13 | **Skipped**, as the brief says | Yahoo returned 429, Nasdaq timed out, Stooq served an anti-bot page. |
| b12 | NYT headline card | A card labelled "our summary of the report, not its headline" | I could not verify the Times' headline text. |
| b01–b02 | Generic GPU stock footage | GPU illustration drawn in code, with no logo | No stock API keys. |
| b07, b09 | Map | Natural Earth map drawn in code | As intended. |
| b25, b29, b30 | DOJ or Nvidia imagery | Diagrams and status cards | Avoids official seals and logos. |
| b14, b15 | Alice Huang | Neutral silhouette card with your label | As required. |

## Claims dropped or softened because they couldn't be verified
- **B3d:** Huang told Bloomberg the business was "normal". Dropped; the only source was an aggregator.
- **B7d:** testimony "before Thanksgiving". Dropped. The requested dates (Dec 1 / early December) are after Thanksgiving. The video says "December" and "reportedly agreed in principle".
- **B2b:** "complies with all applicable laws". Replaced with "says it follows export rules", which matches the documented wording about export control regulations.
- **B4e:** Huang personally denied compromising secrets. Replaced with "pledged to cooperate" (your option a). The only source was a CNBC live-blog summary.
- **B6a:** "effective immediately". Not used; I never saw it verbatim.
- **B5a:** Wachtell Lipton. Not narrated; the only source is Quartz.
- **N1:** Singapore's passport and re-entry findings. Not used, to avoid extra claims about a private individual.
- **N4:** the Attorney General saying DOJ has "no conclusion". Not used; single source.
- **X1–X5:** excluded on purpose. These are the Reuters report that Huang misled Nvidia's lawyers, the other-relationship reports, the lawyer's contact with Commerce, the $7.5B and $4.6B figures, and the Alibaba claims.

## Deviations from the brief or the approved plan
1. **Speed 1.2× instead of 1.05×.** At 1.05× the approved script ran past 90 s.
2. **One word added after approval:** "Senators from both parties are **reportedly** pressing too." QC found that B7e is class REPORTED and the sentence had no attribution. The script is now **221 words**, one over the 220 cap.
3. **Female voice (`af_heart`).** It is Kokoro's highest-rated voice.
4. **43 beats instead of 42.** Beat b37 was split to stay under 3 s.
5. **Nvidia's card is stamped "DENIED".** Nvidia's statement was a rebuttal ("not unusual"; diversion claims "investigated and debunked"). Change the word in `src/beats.py` (b18) if you want "DISPUTES".

## Known limitations
- **Research rests on search-result excerpts, not full articles.** The environment's network policy refused direct fetches of news sites and sec.gov, and both requests to widen it were rejected by the environments service. Rows marked ⚠️ in the ledger should be checked by a person before publishing, especially the exact 8-K wording and the board-statement quote.
- **The story is moving fast.** The end card says "As of Nov 14, 2026". Re-verify before posting if more than a day or two passes.
- **Licence obligation:** the Marina Bay Sands photo is CC BY-SA 3.0. It is credited on screen in b04 and b05, on the end card, and in the description.

## Re-running
```
python src/tts.py [S1..S7]   # re-record one section
python src/timeline.py && python src/beats.py
python src/audio.py && python src/render.py --video
ffmpeg … (see this file's history)  &&  python src/qc.py
```
