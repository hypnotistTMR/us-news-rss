"""
US専門ニュース・制度変更トラッカー
全サイトのRSS/Atom集約器

Usage:
    python aggregator.py --list                    # 全ソース一覧
    python aggregator.py --fetch-all               # 全件を順次取得→feeds/へ書き出し
    python aggregator.py --fetch <source_id>       # 単体ソースを生成
    python aggregator.py --serve                   # HTTPで feeds/ を配信（テスト用）
"""

import argparse
import datetime as dt
import hashlib
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import feedgen.feed as fg_mod
import requests
import yaml
from dateutil import parser as dateparser

# --- パス設定 ---
ROOT = Path(__file__).resolve().parent
CFG_PATH = ROOT / "config" / "sources.yaml"
FEEDS_DIR = ROOT / "feeds"
LOGS_DIR = ROOT / "logs"
CACHE_DIR = ROOT / "cache"
for d in (FEEDS_DIR, LOGS_DIR, CACHE_DIR):
    d.mkdir(parents=True, exist_ok=True)

# --- ロギング ---
log = logging.getLogger("us-news-rss")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "aggregator.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

# --- HTTPセッション ---
SESSION = requests.Session()
UA = "Mozilla/5.0 (US-News-RSS-Aggregator; admin@example.com)"


# ============================================================
# 設定ロード
# ============================================================
def load_config() -> Dict[str, Any]:
    with open(CFG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ============================================================
# RSSパース (feedparserは依存追加になるので自前でXML軽量抽出)
# ============================================================
def parse_rss(xml: str) -> List[Dict[str, Any]]:
    """RSS 2.0 / Atom 1.0 両方に対応した軽量パーサ。"""
    import lxml.etree as ET
    out: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(xml.encode("utf-8"))
    except ET.XMLSyntaxError as e:
        log.warning("RSS parse failed: %s", e)
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "dc": "http://purl.org/dc/elements/1.1/",
    }

    # RSS 2.0
    items = root.findall(".//item")
    for it in items:
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = it.findtext("pubDate") or it.findtext("dc:date", namespaces=ns) or ""
        desc = it.findtext("description") or ""
        guid = it.findtext("guid") or link
        if link:
            out.append({"title": title, "link": link, "pubDate": pub,
                        "summary": _strip_html(desc), "guid": guid})

    # Atom 1.0
    for entry in root.findall(".//atom:entry", ns):
        title = (entry.findtext("atom:title", namespaces=ns) or "").strip()
        link_el = entry.find("atom:link", ns)
        link = link_el.get("href") if link_el is not None else ""
        pub = entry.findtext("atom:published", namespaces=ns) or \
              entry.findtext("atom:updated", namespaces=ns) or ""
        summary = entry.findtext("atom:summary", namespaces=ns) or \
                  entry.findtext("atom:content", namespaces=ns) or ""
        guid = entry.findtext("atom:id", namespaces=ns) or link
        if link:
            out.append({"title": title, "link": link, "pubDate": pub,
                        "summary": _strip_html(summary), "guid": guid})
    return out


def _strip_html(s: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", s).strip()


# ============================================================
# 各モードの実装
# ============================================================
def fetch_rss(url: str, timeout: int = 20) -> List[Dict[str, Any]]:
    """公式RSSをそのまま取得・パース."""
    r = SESSION.get(url, headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    # BOM除去（utf-8-sig decode で一度に変換してしまうのが確実）
    text = r.content.decode("utf-8-sig", errors="replace")
    return parse_rss(text)


def fetch_govdelivery(url: str, timeout: int = 20) -> List[Dict[str, Any]]:
    """GovDelivery形式のフィード。RSSと同じ."""
    return fetch_rss(url, timeout)


def fetch_api(source: Dict[str, Any], timeout: int = 20) -> List[Dict[str, Any]]:
    """JSON API → 正規化."""
    import json
    cfg = source.get("params", {})
    r = SESSION.get(
        source["endpoint"],
        headers={"User-Agent": UA, "Accept": "application/json"},
        params=cfg,
        timeout=timeout,
    )
    r.raise_for_status()
    data = r.json()

    # Federal Register API
    if "federalregister.gov" in source["endpoint"]:
        return [_normalize_fr(it) for it in data.get("results", [])]
    # SEC EDGAR full-text search
    if "efts.sec.gov" in source["endpoint"]:
        hits = data.get("hits", {}).get("hits", [])
        return [_normalize_edgar(h) for h in hits]
    return []


def _normalize_fr(item: Dict[str, Any]) -> Dict[str, Any]:
    agencies = item.get("agencies", [])
    if isinstance(agencies, list) and agencies:
        if isinstance(agencies[0], dict):
            agency_name = agencies[0].get("name", "")
        else:
            agency_name = str(agencies[0])
    else:
        agency_name = ""
    return {
        "title": item.get("title", ""),
        "link": item.get("html_url") or item.get("full_text_xml_url") or "",
        "pubDate": item.get("publication_date", ""),
        "summary": f"{agency_name} — {item.get('document_number', '')}",
        "guid": f"fr:{item.get('document_number', '')}",
    }


def _normalize_edgar(hit: Dict[str, Any]) -> Dict[str, Any]:
    src = hit.get("_source", {})
    cik = (src.get("ciks") or [""])[0]
    acc = src.get("adsh", "").replace("-", "")
    fname = src.get("display_name") or hit.get("_id", "")
    url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=8-K"
    return {
        "title": f"{src.get('display_names', ['?'])[0]} - {src.get('form', '')}",
        "link": url,
        "pubDate": src.get("file_date", ""),
        "summary": fname,
        "guid": f"edgar:{acc}",
    }


def fetch_scrape(source: Dict[str, Any], timeout: int = 20) -> List[Dict[str, Any]]:
    """
    HTMLをスクレイプしてニュース一覧を取り出す。
    サイトごとにselectorが違うのでadapters/<id>.pyを優先呼び出し、
    無ければ generic_scrape() にフォールバック。
    """
    adapter_name = source["id"]
    try:
        mod = __import__(f"adapters.{adapter_name}", fromlist=["scrape"])
        return mod.scrape(SESSION, source, UA, timeout)
    except ModuleNotFoundError:
        return generic_scrape(source, timeout)


def generic_scrape(source: Dict[str, Any], timeout: int) -> List[Dict[str, Any]]:
    """汎用スクレイパ: list_endpointから <a href> を拾うだけの最後に手段."""
    import lxml.html as LH
    url = source.get("list_endpoint") or source.get("endpoint")
    r = SESSION.get(url, headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    root = LH.fromstring(r.text)
    out: List[Dict[str, Any]] = []
    for a in root.cssselect("a[href]"):
        text = (a.text_content() or "").strip()
        href = a.get("href", "")
        if text and href and len(text) > 15:
            if not href.startswith("http"):
                href = requests.compat.urljoin(url, href)
            out.append({
                "title": text[:200],
                "link": href,
                "pubDate": "",
                "summary": f"[scrape from {url}]",
                "guid": hashlib.md5(href.encode()).hexdigest(),
            })
    return out[:30]


# ============================================================
# Atom生成
# ============================================================
def build_atom(source: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    fg = fg_mod.FeedGenerator()
    fg.id(f"urn:us-news-rss:{source['id']}")
    fg.title(source["title"])
    fg.subtitle(f"Category: {source['category']} / Mode: {source['mode']}")
    fg.link(href=f"file:///feeds/{source['id']}.xml", rel="self")
    fg.link(href=source.get("endpoint") or source.get("list_endpoint", ""), rel="alternate")
    fg.language("en")
    fg.updated(dt.datetime.now(dt.timezone.utc))

    seen = set()
    max_n = 30
    for it in items:
        if len(seen) >= max_n:
            break
        link = it.get("link", "")
        if not link or link in seen:
            continue
        seen.add(link)
        try:
            pub = dateparser.parse(it.get("pubDate", "")) if it.get("pubDate") else None
            if pub is None:
                pub = dt.datetime.now(dt.timezone.utc)
            elif pub.tzinfo is None:
                pub = pub.replace(tzinfo=dt.timezone.utc)
        except Exception:
            pub = dt.datetime.now(dt.timezone.utc)
        fe = fg.add_entry()
        fe.id(it.get("guid") or link)
        fe.title(it.get("title", "")[:200])
        fe.link(href=link)
        fe.published(pub)
        fe.summary(it.get("summary", "")[:500])
    return fg.atom_str(pretty=True).decode("utf-8")


# ============================================================
# メインロジック
# ============================================================
def fetch_one(source: Dict[str, Any]) -> Dict[str, Any]:
    mode = source["mode"]
    log.info("FETCH  %-22s  [%s]  %s", source["id"], mode,
             (source.get("endpoint") or source.get("list_endpoint") or "")[:80])
    t0 = time.time()
    try:
        if mode == "rss":
            items = fetch_rss(source["endpoint"])
        elif mode == "govdelivery":
            items = fetch_govdelivery(source["endpoint"])
        elif mode == "api":
            items = fetch_api(source)
        elif mode == "scrape":
            items = fetch_scrape(source)
        else:
            raise ValueError(f"unknown mode: {mode}")

        items = _dedup(items)
        log.info("  → %3d items in %.1fs", len(items), time.time() - t0)
        return {"ok": True, "items": items}

    except Exception as e:
        log.warning("  ✗ FAILED: %s", e)
        return {"ok": False, "items": [], "error": str(e)}


def _dedup(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for it in items:
        key = it.get("guid") or it.get("link")
        if key and key not in seen:
            seen.add(key)
            out.append(it)
    return out


def write_feed(source: Dict[str, Any], items: List[Dict[str, Any]]) -> Path:
    xml = build_atom(source, items)
    path = FEEDS_DIR / f"{source['id']}.xml"
    path.write_text(xml, encoding="utf-8")
    log.info("  → WROTE %s  (%d bytes)", path.name, path.stat().st_size)
    return path


def cmd_list(cfg: Dict[str, Any]):
    print(f"{'ID':<26} {'MODE':<12} {'CAT':<14} {'PRIO':<8} ENDPOINT")
    print("-" * 110)
    for s in cfg["sources"]:
        ep = (s.get("endpoint") or s.get("list_endpoint") or "")[:60]
        print(f"{s['id']:<26} {s['mode']:<12} {s['category']:<14} {s.get('priority','-'):<8} {ep}")


def cmd_fetch_all(cfg: Dict[str, Any]):
    ok = fail = 0
    for s in cfg["sources"]:
        r = fetch_one(s)
        if r["ok"] and r["items"]:
            write_feed(s, r["items"])
            ok += 1
        else:
            fail += 1
    log.info("=== done: %d ok, %d fail ===", ok, fail)


def cmd_fetch_one(cfg: Dict[str, Any], sid: str):
    for s in cfg["sources"]:
        if s["id"] == sid:
            r = fetch_one(s)
            if r["ok"] and r["items"]:
                write_feed(s, r["items"])
            return
    log.error("source id not found: %s", sid)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--fetch-all", action="store_true")
    ap.add_argument("--fetch", metavar="SOURCE_ID")
    args = ap.parse_args()

    cfg = load_config()
    if args.list:
        cmd_list(cfg)
    elif args.fetch_all:
        cmd_fetch_all(cfg)
    elif args.fetch:
        cmd_fetch_one(cfg, args.fetch)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()