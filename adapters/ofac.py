"""OFAC Recent Actions スクレイパ（RSS廃止済み）"""

import lxml.html as LH
from typing import Dict, Any, List


def scrape(session, source, ua, timeout):
    url = source.get("list_endpoint", "https://ofac.treasury.gov/recent-actions")
    r = session.get(url, headers={"User-Agent": ua}, timeout=timeout)
    r.raise_for_status()
    root = LH.fromstring(r.text)
    out = []
    # Recent Actionsは日付リンクのリスト
    for a in root.cssselect(".field--name-field-pub-date a, .recent-actions-list a, a[href*='/recent-actions/']"):
        text = (a.text_content() or "").strip()
        href = a.get("href", "")
        if not href.startswith("http"):
            href = "https://ofac.treasury.gov" + href if href.startswith("/") else href
        if text and href:
            out.append({"title": text[:200], "link": href,
                        "pubDate": "", "summary": "OFAC Recent Action",
                        "guid": href})
            if len(out) >= 30:
                break
    return out