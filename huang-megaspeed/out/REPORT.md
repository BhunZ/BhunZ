# Final report: v2 documentary cut

As of **2026-11-14**. Branch `ccr-bf443029-plmqpt`, folder `huang-megaspeed/`.

## Deliverables
| File | Notes |
|---|---|
| `out/huang_megaspeed.mp4` | 1080×1920, 30 fps, **3:00.7**. H.264 at about 3.8 Mbps (2-pass) plus AAC 160k, 89 MB (sized to fit GitHub's 100 MB file limit). A higher-bitrate master can be rebuilt with `src/render2.py`. |
| `out/description.txt` | Two-sentence summary, the required disclaimer, 26 source URLs, every CC BY/BY-SA attribution, and the AI disclosure. |
| `out/credits.json` | 50 assets, each with URL, author, licence and how it was verified. |
| `out/qc_report.json` | Full machine-readable QC. |
| `research/ledger.md` | v1 ledger plus the v2 section: primary-source upgrades and new rows N6, N8, N9, N10. |
| `research/script_v2.md` | The 31-sentence documentary script with ledger tags. |
| `storyboard.json` | 75 background segments, each with the active front/mid/card layers, ledger IDs, sfx and motion. |
| `out/v2_checkpoint/` | Asset contact sheet and six key stills. |

## QC (measured on the final MP4): all pass
| # | Check | Result |
|---|---|---|
| 1 | Every sentence maps to a ledger ID with matching attribution | **PASS**. 31/31 sentences. "CNBC reported" was added to the market sentence because N8 is class REPORTED. |
| 2 | Four counterpoints | **PASS**. Board "no reason to believe…", Huang "would cooperate fully", China "unsubstantiated", Megaspeed "denies wrongdoing". |
| 3 | No face of Alice Huang, no family, no unrelated people | **PASS**. 61 face-detector hits at 2 fps. Each is either a Jensen Huang photo on an allowed beat or a false positive on hardware or windows, eye-checked per asset (`assets2/face_review.json`). No Huang photo appears during the Alice Huang lines. The NYT "Spy Plot" headline never shares a frame with a person. Alice Huang appears only as a silhouette card. |
| 4 | Every asset credited, with a licence allowing this use | **PASS**. 31 screenshots, 16 Commons (CC BY / BY-SA / PD), 3 NASA (PD). |
| 5 | Caption sync ≤ 80 ms; captions clear of the bottom 18% | **PASS**. Caption-to-audio-onset drift: median 16 ms, max 67 ms. Captions centred at 55% height; lowest caption edge at y = 1123 against a limit of 1574. |
| 6 | Loudness | **PASS**. **−14.1 LUFS, −1.3 dBTP**. |
| 7 | Format | **PASS**. 1080×1920, 30 fps, 180.7 s. |
| 8 | No recreated or look-alike documents | **PASS**. All 31 document cuts come from real browser screenshots. The only drawn cards are the three you allowed: silhouette, alleged-vs-proven summary, end card. |
| 9 | Full-bleed: ≤ 15% empty background at 1 fps | **PASS**. Worst frame 12.1% solid or black void outside the document layers. ⚠ See note. |
| 10 | ≥ 45 scene cuts | **PASS**. **76** scene changes (> 0.25). |

**Note on check 9.** I tested two metrics.
- **Void/solid metric (the pass criterion):** counts solid fills and black voids outside the documents. It passes, at worst 12.1%.
- **Strict texture metric:** flags any smooth 16 px area. It still flags 39 frames, because it treats natural sky, water and night city as "empty".

To get the void metric passing I removed footage rather than tuning the threshold. Dropped: a dark cabinet-door clip, a hazy-sky clip, and a black-space NASA globe. I also fixed clips that faded in from black or looped back to title cards. Both numbers are in `qc_report.json`.

## What changed from the approved v2 script (all accuracy-driven)
- **Sentence 12:** the wording now matches Nvidia's on-record quote: *"not unusual or unexpected… meetings with customers are part of a CEO's job"*.
- **Sentence 13:** "unsubstantiated", the word in the official MFA transcript, replaces "groundless".
- **Sentence 25:** "CNBC reported" added, because N8 is REPORTED.

## Assets and access
- **B-roll:** 7 Wikimedia Commons videos (Singapore ×2, KL, port ×2, Capitol dome, Washington Monument) plus 3 NASA data-center segments. Every clip was reviewed frame by frame, with clean start points recorded in `assets2/review.json`.
  - **Rejected:** January 6 footage featuring a named senator, warships, stock-exchange ceremonies with identifiable people, YouTuber presenter footage, a Google-watermarked clip, and a "CC0" Internet Archive item that was actually a game trailer. The Internet Archive was dropped as a source.
  - **Port of Cork aerials** are used only as generic port imagery and never labelled as an Asian port.
- **Photos:** 9 Huang photos (CC BY / BY-SA) from Stanford 2026, Computex 2010 and 2016, and a 2023 Taiwan event, with face-centred 9:16 crops that exclude the audience. 4 crowd shots were rejected. Plus 2 PD/CC photos (Capitol, Singapore).
- **Documents:** real screenshots of the SEC 8-K and Ex. 99.1 (sec.gov, using your email in the User-Agent), 5 Nvidia newsroom pages, the China MFA transcript and the House letter. **Headlines:** NYT, CBS, NBC, TechCrunch and Yahoo/Motley Fool, cropped to masthead, headline and byline, with article photos removed.
- **Blocked automation, so not used and not recreated:** CNBC, SCMP, Fortune, Axios, Reuters, AP, the Singapore Home Affairs ministry, The Hill and Forbes.
- **Your email** went into exactly two places: the sec.gov and Wikimedia User-Agent headers, as both sites' policies require. Nowhere else.

## Tools, keys and cost
- **Packages:** Kokoro-82M TTS, faster-whisper, Playwright/Chromium, skia-python, numpy/scipy/Pillow, OpenCV (QC) and ffmpeg.
- **API keys used: none.** Pexels was paused.
- **API spend: $0.** Everything ran locally. Wikimedia, NASA, SEC and the news sites are free to access.

## Limitations
- **The B-roll is real but modest.** Commons has few stock-style clips, and its rate limit capped collection. Some clips repeat at different offsets.
- **Headline screenshots are third-party pages** shown briefly with attribution for commentary. That's your call; it's noted in the credits.
- **The story moves daily.** The end card says "As of Nov 14, 2026", so re-verify before posting if time passes.
