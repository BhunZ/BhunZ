"""Write out/description.txt for the v2 cut (sources + full attributions from credits.json)."""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cred = json.load(open(os.path.join(ROOT, "out", "credits.json")))
src = [
    ("Nvidia Form 8-K (SEC, Nov. 12, 2026)", "https://www.sec.gov/Archives/edgar/data/0001045810/000104581026000082/nvda-20261111.htm"),
    ("Nvidia press release, CEO transition (Ex. 99.1)", "https://www.sec.gov/Archives/edgar/data/0001045810/000104581026000082/nvidiaannouncesceotransiti.htm"),
    ("Nvidia: A Message to Our Company (Huang's email, Nov. 8)", "https://nvidianews.nvidia.com/news/a-message-to-our-company"),
    ("Nvidia: Statement From NVIDIA Board of Directors (Nov. 8)", "https://nvidianews.nvidia.com/news/statement-from-nvidia-board-of-directors"),
    ("Nvidia: Statement From the Independent Members of the NVIDIA Board (Nov. 10)", "https://nvidianews.nvidia.com/news/statement-from-the-independent-members-of-the-nvidia-board"),
    ("Nvidia: CEO transition and Nov. 17 earnings date", "https://nvidianews.nvidia.com/news/nvidia-announces-ceo-transition"),
    ("China MFA press conference, Oct. 30, 2026 (transcript)", "https://www.fmprc.gov.cn/eng/xw/fyrbt/lxjzh/202610/t20261030_12050434.html"),
    ("China MFA press conference, Nov. 9, 2026 (transcript)", "https://www.fmprc.gov.cn/eng/xw/fyrbt/202611/t20261109_12056171.html"),
    ("U.S. House committees' letter to Huang (Nov. 4)", "https://chinaselectcommittee.house.gov/sites/evo-subsites/selectcommitteeontheccp.house.gov/files/evo-media-document/nvidia-letter-pdf.pdf"),
    ("NYT: Nvidia Chief Seen as Target of Chinese Spy Plot (Oct. 29)", "https://www.nytimes.com/2026/10/29/us/politics/nvidia-china-jensen-huang-trump.html"),
    ("NYT: A Mystery C.E.O. and Billions in Sales (Oct. 9, 2025)", "https://www.nytimes.com/2025/10/09/technology/nvidia-chips-china-megaspeed.html"),
    ("NYT: The Fall of Jensen Huang ($4.8 billion figure)", "https://www.nytimes.com/interactive/2026/11/13/technology/nvidia-jensen-huang.html"),
    ("NYT: Jensen Huang Lost His Job. Wall Street Lost Its Biggest Prize.", "https://www.nytimes.com/2026/11/13/business/jensen-huang-nvidia-wall-street.html"),
    ("CBS News: Megaspeed's vacant offices raise questions", "https://www.cbsnews.com/news/megaspeed-nvidia-china-ties/"),
    ("CBS News: Nvidia investigates CEO Jensen Huang", "https://www.cbsnews.com/news/nvidia-jensen-huang-investigation-china-intelligence/"),
    ("CBS News: Nvidia's stock slides (spokesperson 'without interruption')", "https://www.cbsnews.com/news/nvidia-jensen-huang-stock-board-investigation-spy/"),
    ("NBC News: Megaspeed pledges to cooperate with U.S. investigation", "https://www.nbcnews.com/tech/tech-news/megaspeed-statement-nvidia-jensen-huang-alice-us-exports-chips-china-rcna608939"),
    ("TechCrunch: Huang resigns; Kress interim CEO", "https://techcrunch.com/2026/11/12/nvidias-jensen-huang-resigns-chipmaker-names-cfo-colette-kress-as-interim-ceo/"),
    ("TechCrunch: Huang agrees to testify before Congress", "https://techcrunch.com/2026/11/12/jensen-huang-agrees-to-testify-before-congress/"),
    ("TechCrunch: timeline (Nvidia 'not unusual or unexpected' statement)", "https://techcrunch.com/2026/11/13/nvidia-ceo-jensen-huangs-affair-with-alleged-chinese-spy-a-timeline/"),
    ("Yahoo Finance / Motley Fool: Nov. 12 market close", "https://finance.yahoo.com/markets/stocks/articles/stock-market-today-nov-12-221840920.html"),
    ("CNBC: Nvidia closes below $4T market cap (Nov. 13)", "https://www.cnbc.com/2026/11/13/nvidia-nvda-stock-jensen-huang-transition.html"),
    ("CNBC: Nvidia stock closes down over 4% (Nov. 12)", "https://www.cnbc.com/2026/11/12/nvidia-nvda-jensen-huang-second-affair.html"),
    ("CNBC: date and format of testimony still being negotiated (Nov. 13)", "https://cnbc.com/2026/11/13/nvidia-jensen-huang-washington-congress.html"),
    ("CNBC: Singapore police probe Megaspeed (Oct. 2025)", "https://www.cnbc.com/2025/10/10/singapore-us-investigate-nvidia-client-megaspeed-export-controls-violation.html"),
    ("The Hill: Senate pressure on the Megaspeed probe", "https://thehill.com/policy/technology/6214107-bennet-pushes-megaspeed-probe/"),
]
lines = [
    "Nvidia's board accepted Jensen Huang's resignation on Nov. 11, 2026, less than two weeks after The New York Times reported that "
    "U.S. intelligence officials believe a former executive of Nvidia customer Megaspeed is a Chinese intelligence asset. "
    "This documentary explainer separates what is confirmed in filings and statements from what is only reported or alleged, "
    "and covers what to watch next: Nvidia's Nov. 17 earnings, the board's investigation and Huang's testimony to Congress.",
    "",
    "Allegations are unproven; Nvidia, Megaspeed and China deny wrongdoing.",
    "",
    "As of Nov. 14, 2026. Nvidia's board said it has no reason to believe national security or Nvidia secrets were compromised. "
    "Huang said he would cooperate fully with the investigation. China's foreign ministry called the report \"unsubstantiated.\" "
    "Megaspeed denies wrongdoing and says it takes export rules \"extremely seriously.\"",
    "",
    "Sources:",
] + [f"{t}: {u}" for t, u in src] + ["", "Footage and photos (Wikimedia Commons / NASA; licences as listed):"]
seen = set()
for a in cred["assets"]:
    if a["type"].startswith("real"):
        continue
    key = a.get("source_url")
    if key in seen:
        continue
    seen.add(key)
    lines.append(f"{a.get('title') or a['file']} by {a.get('author') or 'NASA'}, {a.get('license')}: {key}")
lines += ["", "Document and headline images are cropped screenshots of the publicly available pages listed above, shown for news commentary.",
          "", "This video uses AI-generated narration and graphics."]
open(os.path.join(ROOT, "out", "description.txt"), "w").write("\n".join(lines) + "\n")
print("description written:", len(src), "sources,", len(seen), "credited media")
