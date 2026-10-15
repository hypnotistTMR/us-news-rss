"""USTR Press Releases スクレイパ"""

import lxml.html as LH
from typing import Dict, Any, List


def scrape(session, source, ua, timeout):
    url = source.get("list_endpoint",
                     "https://ustr.gov/about/policy-offices/press-office/press-releases")
    r = session.get(url, headers={"User-Agent": ua}, timeout=timeout)
    r.raise_for_status()
    root = LH.fromstring(r.text)
    out = []
    seen = set()
    for a in root.cssselect("a[href*='press-releases/']"):
        href = a.get("href", "")
        title = (a.text_content() or "").strip()
        if not href or not title or len(title) < 15:
            continue
        # 年別インデックスのリンクは除外
        if href.rstrip("/").endswith(tuple(["2026", "2025", "2024", "2023", "press-releases"])):
            continue
        if not href.startswith("http"):
            href = "https://ustr.gov" + href if href.startswith("/") else href
        if href in seen:
            continue
        seen.add(href)
        out.append({"title": title[:200], "link": href,
                    "pubDate": "", "summary": "USTR", "guid": href})
        if len(out) >= 30:
            break
    return out