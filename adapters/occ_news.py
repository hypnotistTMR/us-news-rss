"""
OCC Newsroom スクレイパ
URL: https://www.occ.gov/news-events/newsroom/index.html
"""

import lxml.html as LH
from typing import Dict, Any, List


def scrape(session, source: Dict[str, Any], ua: str, timeout: int) -> List[Dict[str, Any]]:
    url = source.get("list_endpoint",
                     "https://www.occ.gov/news-events/newsroom/index.html")
    r = session.get(url, headers={"User-Agent": ua}, timeout=timeout)
    r.raise_for_status()
    root = LH.fromstring(r.text)
    out: List[Dict[str, Any]] = []
    seen = set()

    for a in root.cssselect(
        "a[href*='nr-occ-'], a[href*='news-issuances/news-releases/']"
    ):
        href = a.get("href", "")
        title = (a.text_content() or "").strip()
        if not href or not title or len(title) < 15:
            continue
        if not href.startswith("http"):
            href = "https://www.occ.gov" + href if href.startswith("/") else href
        if href in seen:
            continue
        seen.add(href)
        out.append({
            "title": title[:200],
            "link": href,
            "pubDate": "",
            "summary": "OCC Newsroom",
            "guid": href,
        })
        if len(out) >= 30:
            break
    return out