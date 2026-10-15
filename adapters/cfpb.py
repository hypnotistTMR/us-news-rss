"""CFPB Newsroom スクレイパ"""

import lxml.html as LH
from typing import Dict, Any, List


def scrape(session, source, ua, timeout):
    url = source.get("list_endpoint", "https://www.cfpb.gov/about-us/newsroom")
    r = session.get(url, headers={"User-Agent": ua}, timeout=timeout)
    r.raise_for_status()
    root = LH.fromstring(r.text)
    out = []
    seen = set()
    for a in root.cssselect("a[href*='newsroom']"):
        href = a.get("href", "")
        title = (a.text_content() or "").strip()
        if not href or not title or len(title) < 25:
            continue
        if href.endswith("/newsroom") or href.endswith("/newsroom/"):
            continue
        if not href.startswith("http"):
            href = "https://www.cfpb.gov" + href if href.startswith("/") else href
        if href in seen:
            continue
        seen.add(href)
        out.append({"title": title[:200], "link": href,
                    "pubDate": "", "summary": "CFPB", "guid": href})
        if len(out) >= 30:
            break
    return out