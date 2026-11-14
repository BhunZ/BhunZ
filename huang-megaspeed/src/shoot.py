"""Real screenshots of primary documents and news headlines (Playwright, DSF 2).

For every page: a full-page PNG, the page text, and the bounding boxes of key phrases
(used later as zoom/highlight targets). Overlays such as cookie banners are hidden; page
content is never edited. Headline captures are cropped to masthead + headline + byline/date.
"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets2")
SEC_UA = "BhunZ news-explainer research baohung.clone@gmail.com"   # SEC fair-access policy (owner-approved)

DOCS = [  # (key, url, phrases)
 ("sec_8k", "https://www.sec.gov/Archives/edgar/data/0001045810/000104581026000082/nvda-20261111.htm",
  ["accepted the resignation of Jen-Hsun Huang", "effective immediately", "Colette M. Kress", "interim Chief Executive Officer", "Harvey C. Jones"]),
 ("sec_ex991", "https://www.sec.gov/Archives/edgar/data/0001045810/000104581026000082/nvidiaannouncesceotransiti.htm",
  ["Jensen Huang has resigned", "effective immediately", "Interim Chief Executive Officer", "first-ever Chair of the Board"]),
 ("nv_board", "https://nvidianews.nvidia.com/news/statement-from-nvidia-board-of-directors",
  ["independent investigation", "no reason to believe", "national security", "NVIDIA secrets were compromised"]),
 ("nv_message", "https://nvidianews.nvidia.com/news/a-message-to-our-company",
  ["I was unfaithful to my wife", "national security", "cooperate fully"]),
 ("nv_transition", "https://nvidianews.nvidia.com/news/nvidia-announces-ceo-transition",
  ["Jensen Huang has resigned", "Interim Chief Executive Officer", "first-ever Chair"]),
 ("nv_independent", "https://nvidianews.nvidia.com/news/statement-from-the-independent-members-of-the-nvidia-board",
  ["Wachtell", "Joon H. Kim", "independent investigation"]),
 ("mfa_1030", "https://www.fmprc.gov.cn/eng/xw/fyrbt/lxjzh/202610/t20261030_12050434.html",
  ["Nvidia", "New York Times", "smear", "groundless", "unsubstantiated"]),
 ("mfa_1109", "https://www.fmprc.gov.cn/eng/xw/fyrbt/202611/t20261109_12056171.html",
  ["Nvidia", "smear", "groundless", "unsubstantiated"]),

]
HEADLINES = [  # (key, url) — outlets other than the parties; no headline containing spy/affair wording
 ("hl_techcrunch_resigns", "https://techcrunch.com/2026/11/12/nvidias-jensen-huang-resigns-chipmaker-names-cfo-colette-kress-as-interim-ceo/"),
 ("hl_techcrunch_testify", "https://techcrunch.com/2026/11/12/jensen-huang-agrees-to-testify-before-congress/"),
 ("hl_cbs_megaspeed", "https://www.cbsnews.com/news/megaspeed-nvidia-china-ties/"),
 ("hl_cbs_investigation", "https://www.cbsnews.com/news/nvidia-jensen-huang-investigation-china-intelligence/"),
 ("hl_cbs_stock", "https://www.cbsnews.com/news/nvidia-jensen-huang-stock-board-investigation-spy/"),
 ("hl_nbc_megaspeed", "https://www.nbcnews.com/tech/tech-news/megaspeed-statement-nvidia-jensen-huang-alice-us-exports-chips-china-rcna608939"),
 ("hl_yahoo_1112", "https://finance.yahoo.com/markets/stocks/articles/stock-market-today-nov-12-221840920.html"),
 ("hl_fox_kress", "https://www.foxbusiness.com/markets/colette-kress-named-nvidia-interim-ceo-jensen-huangs-abrupt-resignation-raises-investor-concerns"),
 ("hl_nyt_2025", "https://www.nytimes.com/2025/10/09/technology/nvidia-chips-china-megaspeed.html"),
 ("hl_nyt_wallst", "https://www.nytimes.com/2026/11/13/business/jensen-huang-nvidia-wall-street.html"),
 ("hl_nyt_fall", "https://www.nytimes.com/interactive/2026/11/13/technology/nvidia-jensen-huang.html"),
]

HIDE_OVERLAYS = """
() => { for (const el of document.querySelectorAll('*')) {
  const s = getComputedStyle(el);
  if ((s.position === 'fixed' || s.position === 'sticky') && el.tagName !== 'HEADER' && !el.querySelector('h1')) {
    const r = el.getBoundingClientRect();
    if (r.height > 0 && (r.height > 120 || /cookie|consent|banner|modal|overlay|newsletter|paywall|gdpr/i.test(el.className + el.id)))
      el.style.setProperty('display', 'none', 'important');
  } }
  document.documentElement.style.overflow = 'auto'; document.body.style.overflow = 'auto'; }
"""
FIND = """
(phrases) => { const out = {};
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const nodes = []; let n; while ((n = walker.nextNode())) nodes.push(n);
  for (const ph of phrases) {
    for (const node of nodes) {
      const i = node.textContent.toLowerCase().indexOf(ph.toLowerCase());
      if (i >= 0) { const r = document.createRange(); r.setStart(node, i); r.setEnd(node, i + ph.length);
        const rs = [...r.getClientRects()].map(b => [b.left + scrollX, b.top + scrollY, b.width, b.height]);
        if (rs.length) { out[ph] = rs; break; } }
    } }
  return out; }
"""
HEAD = """
() => { const h = document.querySelector('h1'); if (!h) return null;
  const r = h.getBoundingClientRect();
  return {top: r.top + scrollY, bottom: r.bottom + scrollY, left: r.left, right: r.right, text: h.innerText}; }
"""


async def shoot(ctx, key, url, phrases, headline=False, sub="docs"):
    pg = await ctx.new_page()
    rec = {"key": key, "url": url}
    try:
        r = await pg.goto(url, wait_until="domcontentloaded", timeout=45000)
        await pg.wait_for_timeout(3500)
        rec["status"] = r.status if r else None
        await pg.evaluate(HIDE_OVERLAYS)
        # Expand the viewport to the full document height BEFORE measuring, so the measured
        # phrase boxes and the captured pixels come from the same layout (no reflow).
        vw = pg.viewport_size["width"]
        for _ in range(2):
            hgt = await pg.evaluate("""() => { let m = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight);
                for (const e of document.querySelectorAll('body *')) { const r = e.getBoundingClientRect();
                  if (r.height > 0 && r.width > 0) m = Math.max(m, r.bottom + scrollY); }
                return Math.min(Math.ceil(m), 15000); }""")
            await pg.set_viewport_size({"width": vw, "height": int(hgt)})
            await pg.wait_for_timeout(1200)
            await pg.evaluate(HIDE_OVERLAYS)
        rec["title"] = await pg.title()
        rec["phrases"] = await pg.evaluate(FIND, phrases or [])
        rec["h1"] = await pg.evaluate(HEAD)
        await pg.screenshot(path=os.path.join(OUT, sub, f"{key}_full.png"), full_page=False)
        rec["text"] = (await pg.inner_text("body"))[:20000]
    except Exception as e:
        rec["error"] = str(e)[:300]
    await pg.close()
    print(key, rec.get("status"), rec.get("error", ""), (rec.get("h1") or {}).get("text", "")[:90], flush=True)
    return rec


async def main(which):
    recs = {}
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        sec = await b.new_context(user_agent=SEC_UA, viewport={"width": 900, "height": 1400}, device_scale_factor=2,
                                  extra_http_headers={"From": "baohung.clone@gmail.com"})
        gen = await b.new_context(viewport={"width": 600, "height": 1100}, device_scale_factor=2, locale="en-US")
        if which in ("all", "docs"):
            for key, url, ph in DOCS:
                if len(sys.argv) > 2 and key not in sys.argv[2:]:
                    continue
                recs[key] = await shoot(sec if "sec.gov" in url else gen, key, url, ph)
        if which in ("all", "headlines", "nyt"):
            for key, url in HEADLINES:
                if which == "nyt" and "nytimes" not in url:
                    continue
                recs[key] = await shoot(gen, key, url, ["$4.8 billion", "purchased $4.8 billion of Nvidia's advanced artificial intelligence equipment",
                                                         "closed at $166.19", "falling 4.34%", "testify"], headline=True, sub="headlines")
        if which in ("all", "nytdesk"):
            desk = await b.new_context(viewport={"width": 1280, "height": 1100}, device_scale_factor=2, locale="en-US")
            recs["hl_nyt_1029_desk"] = await shoot(desk, "hl_nyt_1029_desk", "https://www.nytimes.com/2026/10/29/us/politics/nvidia-china-jensen-huang-trump.html",
                                                   ["Nvidia Chief Seen as", "Target of Chinese Spy Plot", "Times Exclusive"], headline=True, sub="headlines")
        await b.close()
    path = os.path.join(OUT, "shots.json")
    old = json.load(open(path)) if os.path.exists(path) else {}
    old.update(recs)
    json.dump(old, open(path, "w"), indent=1)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "all"))
