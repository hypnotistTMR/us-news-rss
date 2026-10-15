"""OCC Bulletins スクレイパ"""

import lxml.html as LH
from typing import Dict, Any, List


def scrape(session, source, ua, timeout):
    url = source.get("list_endpoint", "https://www.occ.gov/news-issuances/bulletins/")
    r = session.get(url, headers={"User-Agent": ua}, timeout=timeout)
    r.raise_for_status()
    root = LH.fromstring(r.text)
    out = []
    for a in root.cssselect("a[href]"):
        text = (a.text_content() or "").strip()
        href = a.get("href", "")
        if text and href and "bulletin" in href.lower() and len(text) > 15:
            if not href.startswith("http"):
                href = "https://www.occ.gov" + href if href.startswith("/") else href
            out.append({"title": text[:200], "link": href, "pubDate": "",
                        "summary": "OCC Bulletin", "guid": href})
            if len(out) >= 30:
                break
    return out