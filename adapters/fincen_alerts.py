"""FinCEN Advisories & Notices スクレイパ"""

import lxml.html as LH
from typing import Dict, Any, List


def scrape(session, source, ua, timeout):
    url = source.get("list_endpoint",
                     "https://fincen.gov/resources/advisoriesbulletinsfact-sheets")
    r = session.get(url, headers={"User-Agent": ua}, timeout=timeout)
    r.raise_for_status()
    root = LH.fromstring(r.text)
    out = []
    # FinCENページはテーブル形式: <tr><td>Date</td><td>Title</td></tr>
    for tr in root.cssselect("tr"):
        tds = tr.cssselect("td")
        if len(tds) < 2:
            continue
        a = tds[1].cssselect("a[href]")
        if not a:
            continue
        link = a[0].get("href", "")
        title = (a[0].text_content() or "").strip()
        date_text = (tds[0].text_content() or "").strip()
        if not link.startswith("http"):
            link = "https://fincen.gov" + link if link.startswith("/") else link
        if title and "FIN-" in title.upper() or "Advisory" in title or "Alert" in title:
            out.append({"title": title, "link": link, "pubDate": date_text,
                        "summary": f"FinCEN - {date_text}", "guid": link})
            if len(out) >= 30:
                break

    if not out:
        # フォールバック
        for a in root.cssselect("a[href]"):
            text = (a.text_content() or "").strip()
            href = a.get("href", "")
            if text and href and len(text) > 15:
                if not href.startswith("http"):
                    href = "https://fincen.gov" + href if href.startswith("/") else href
                out.append({"title": text[:200], "link": href,
                            "pubDate": "", "summary": "FinCEN", "guid": href})
                if len(out) >= 30:
                    break
    return out