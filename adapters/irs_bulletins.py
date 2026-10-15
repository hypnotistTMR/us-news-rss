"""IRS IRB スクレイパ"""

import lxml.html as LH
from typing import Dict, Any, List


def scrape(session, source, ua, timeout):
    url = source.get("list_endpoint", "https://www.irs.gov/irb")
    r = session.get(url, headers={"User-Agent": ua}, timeout=timeout)
    r.raise_for_status()
    root = LH.fromstring(r.text)
    out = []
    seen = set()
    for a in root.cssselect("a[href*='/irb/20']"):
        href = a.get("href", "")
        title = (a.text_content() or "").strip()
        if not href or not title or len(title) < 10:
            continue
        if not href.startswith("http"):
            href = "https://www.irs.gov" + href if href.startswith("/") else href
        if href in seen:
            continue
        seen.add(href)
        out.append({"title": title[:200], "link": href,
                    "pubDate": "", "summary": "IRS Internal Revenue Bulletin",
                    "guid": href})
        if len(out) >= 30:
            break
    return out