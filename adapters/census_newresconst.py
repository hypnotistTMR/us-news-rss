"""Census New Residential Construction スクレイパ"""

import lxml.html as LH
from typing import Dict, Any, List


def scrape(session, source, ua, timeout):
    url = source.get("list_endpoint",
                     "https://www.census.gov/construction/nrc/current")
    r = session.get(url, headers={"User-Agent": ua}, timeout=timeout)
    r.raise_for_status()
    root = LH.fromstring(r.text)
    out = []
    seen = set()
    for a in root.cssselect("a[href*='newresconst']"):
        href = a.get("href", "")
        title = (a.text_content() or "").strip()
        if not href or not title or len(title) < 10:
            continue
        if not href.startswith("http"):
            href = "https://www.census.gov" + href if href.startswith("/") else href
        if href in seen:
            continue
        seen.add(href)
        out.append({"title": title[:200], "link": href,
                    "pubDate": "", "summary": "Census New Residential Construction",
                    "guid": href})
        if len(out) >= 30:
            break
    # フォールバック: PDFリンク
    if not out:
        for a in root.cssselect("a[href*='.pdf']"):
            href = a.get("href", "")
            title = (a.text_content() or "").strip()
            if href and title:
                if not href.startswith("http"):
                    href = "https://www.census.gov" + href if href.startswith("/") else href
                out.append({"title": title[:200], "link": href,
                            "pubDate": "", "summary": "Census PDF",
                            "guid": href})
                if len(out) >= 30:
                    break
    return out