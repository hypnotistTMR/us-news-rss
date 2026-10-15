"""
Reddit サブレディット束 → Atom 2.0 フィード
複数サブレディットを `r/sub1+sub2+.../.rss?limit=100` で1リクエストに集約し、
レート制限（1分/リクエスト）を回避しながら効率的にAtom生成。

バンドル定義:
- money: 個人金融・税・奨学金
- law_work: 法律・雇用・消費者トラブル
- housing: 住宅・不動産
- health: 医療
- tech_privacy: テック・プライバシー
- politics: 政治・市民
- immigration: 移民・VISA
"""

import datetime as dt
import hashlib
import lxml.etree as ET
from typing import Dict, Any, List

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"


# バンドル定義（複数のサブレディットを + で連結）
BUNDLES = {
    "money": [
        "personalfinance",
        "tax",
        "taxes",
        "Frugal",
        "povertyfinance",
        "studentloans",
        "CreditCards",
        "debt",
    ],
    "law_work": [
        "legaladvice",
        "insurance",
        "Scams",
        "Jobs",
        "antiwork",
        "workreform",
        "layoffs",
        "unemployment",
        "AskHR",
    ],
    "housing": [
        "realestate",
        "FirstTimeHomeBuyer",
        "HomeImprovement",
        "Mortgages",
        "Tenant",
        "renters",
    ],
    "health": [
        "HealthInsurance",
        "medicare",
        "medicaid",
        "americashealthcare",
        "EatCheapAndHealthy",
        "diabetes",
    ],
    "tech_privacy": [
        "technology",
        "privacy",
        "netsec",
        "cybersecurity",
        "T-Mobile",
        "ATT",
        "Comcast_Xfinity",
        "verizon",
        "FrontierCommunications",
    ],
    "politics": [
        "politics",
        "AskPolitics",
        "news",
        "law",
        "bluemelaw",
        "Libertarian",
        "conservatives",
        "centrist",
    ],
    "immigration": [
        "immigration",
        "uscis",
        "h1b",
        "j1visa",
        "expats",
        "IWantOut",
    ],
}

NS = {"atom": "http://www.w3.org/2005/Atom"}


def fetch(session, source: Dict[str, Any], timeout: int) -> List[Dict[str, Any]]:
    """
    Reddit RSSから取得・パース。`reddit_url` が config にあればそれを使う、
    無ければバンドル名から URL を構築。
    """
    url = source.get("endpoint")
    if not url:
        bundle = source["id"].replace("reddit_", "")
        subs = BUNDLES.get(bundle, [])
        if not subs:
            return []
        url = (
            f"https://www.reddit.com/r/{'+'.join(subs)}/hot/.rss?limit=100"
        )
    r = session.get(url, headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    return parse_atom(r.text)


def parse_atom(xml: str) -> List[Dict[str, Any]]:
    """Reddit RSS (Atom形式) をパース."""
    out: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(xml.encode("utf-8"))
    except ET.XMLSyntaxError:
        return out
    for entry in root.findall(".//atom:entry", NS):
        title = (entry.findtext("atom:title", namespaces=NS) or "").strip()
        link_el = entry.find("atom:link", NS)
        link = link_el.get("href") if link_el is not None else ""
        # content or summary
        content = entry.findtext("atom:content", namespaces=NS) or ""
        summary = entry.findtext("atom:summary", namespaces=NS) or ""
        body = content or summary
        pub = entry.findtext("atom:updated", namespaces=NS) or \
              entry.findtext("atom:published", namespaces=NS) or ""
        author_el = entry.find("atom:author", NS)
        author = ""
        if author_el is not None:
            name_el = author_el.find("atom:name", NS)
            if name_el is not None and name_el.text:
                author = name_el.text.replace("/u/", "")
        category = entry.findtext("atom:category", namespaces=NS) or ""
        # タイトル先頭に "/r/sub" が入っている場合がある
        clean_title = title.split(": ", 1)[-1] if title.startswith("/r/") and ": " in title else title
        out.append({
            "title": clean_title[:200],
            "link": link,
            "pubDate": pub,
            "summary": body[:500],
            "guid": hashlib.md5(link.encode()).hexdigest(),
            "subreddit": category,
            "author": author,
        })
    return out