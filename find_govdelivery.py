"""
GovDelivery topic page から feed.rss URL を逆引きするツール
使い方: python find_govdelivery.py <agency_url>
"""

import sys
import re
import requests
import lxml.html as LH


def find_feed(agency_url):
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    # 1) その機関の "subscribe" ページを取る
    for cand in [
        agency_url,
        agency_url.rstrip("/") + "/newsroom",
        agency_url.rstrip("/") + "/about",
    ]:
        try:
            r = requests.get(cand, headers={"User-Agent": ua}, timeout=12)
            if r.status_code != 200:
                continue
        except Exception:
            continue
        root = LH.fromstring(r.text)
        # GovDelivery の subscribe リンク
        for a in root.cssselect("a[href*='govdelivery.com']"):
            href = a.get("href", "")
            # 例: https://public.govdelivery.com/accounts/USFDIC_26/subscriber/new
            m = re.search(r"accounts/(US[A-Z0-9_]+)/subscriber", href)
            if m:
                topic = m.group(1)
                # topic で feed URL を試す
                feed_url = f"https://public.govdelivery.com/topics/{topic}/feed.rss"
                # 動作確認
                fr = requests.get(feed_url, headers={"User-Agent": ua}, timeout=10)
                if fr.status_code == 200 and "<rss" in fr.text or "<feed" in fr.text:
                    print(f"FOUND  {topic}  →  {feed_url}  ({len(fr.text)} bytes)")
                    return feed_url, topic
                else:
                    print(f"  tried {feed_url}: {fr.status_code}")
    return None, None


if __name__ == "__main__":
    urls = [
        "https://www.fsis.usda.gov",
        "https://www.ferc.gov",
        "https://www.fmcsa.dot.gov",
        "https://www.nlrb.gov",
        "https://www.nlrb.gov/news-publications/news/news-releases",
        "https://www.fdic.gov/news",
        "https://www.fdic.gov",
        "https://about.usps.com/newsroom/",
    ]
    for u in urls:
        print(f"--- {u} ---")
        find_feed(u)