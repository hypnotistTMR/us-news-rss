"""HUD News スクレイパ"""

import lxml.html as LH
from typing import Dict, Any, List


def scrape(session, source, ua, timeout):
    url = source.get("list_endpoint", "https://www.hud.gov/news")
    r = session.get(url, headers={"User-Agent": ua}, timeout=timeout)
    r.raise_for_status()
    root = LH.fromstring(r.text)
    out = []
    seen = set()
    for a in root.cssselect("a[href]"):
        href = a.get("href", "")
        title = (a.text_content() or "").strip()
        if not href or not title or len(title) < 20:
            continue
        if "/news" not in href and "press" not in href.lower() and "release" not in href.lower():
            continue
        if href.endswith("/news") or href.endswith("/news/"):
            continue
        if not href.startswith("http"):
            href = "https://www.hud.gov" + href if href.startswith("/") else href
        if href in seen:
            continue
        seen.add(href)
        out.append({"title": title[:200], "link": href,
                    "pubDate": "", "summary": "HUD", "guid": href})
        if len(out) >= 30:
            break
    return out