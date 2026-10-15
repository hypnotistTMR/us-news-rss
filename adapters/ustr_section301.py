"""USTR Section 301 Actions スクレイパ"""

import lxml.html as LH
from typing import Dict, Any, List


def scrape(session, source, ua, timeout):
    url = source.get("list_endpoint",
                     "https://ustr.gov/issue-areas/enforcement/section-301-investigations/tariff-actions")
    r = session.get(url, headers={"User-Agent": ua}, timeout=timeout)
    r.raise_for_status()
    root = LH.fromstring(r.text)
    out = []
    seen = set()
    for a in root.cssselect("main a[href], a[href*='301'], a[href*='tariff']"):
        href = a.get("href", "")
        title = (a.text_content() or "").strip()
        if not href or not title or len(title) < 20:
            continue
        if not href.startswith("http"):
            href = "https://ustr.gov" + href if href.startswith("/") else href
        if href in seen or "press-office" in href or "tariff-actions" == href.split("/")[-1]:
            continue
        seen.add(href)
        out.append({"title": title[:200], "link": href,
                    "pubDate": "", "summary": "USTR Section 301", "guid": href})
        if len(out) >= 30:
            break
    return out