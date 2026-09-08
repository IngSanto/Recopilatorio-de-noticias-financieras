#!/usr/bin/env python3
"""Descarga noticias de las fuentes configuradas y las relaciona con acciones/tickers.

Uso:
    python3 scripts/fetch_news.py

Lee:
    data/sources.json  -> lista de fuentes RSS
    data/tickers.json  -> diccionario empresa -> ticker

Escribe:
    data/news.json -> noticias agrupadas por ticker, listas para el front-end
"""
import json
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
USER_AGENT = "Mozilla/5.0 (compatible; RecopiladorNoticiasFinancieras/1.0; +https://github.com/)"
MAX_ITEMS_PER_TICKER = 8
MAX_LATEST = 20
REQUEST_TIMEOUT = 20


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_rss(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        print(f"  ! error descargando {url}: {exc}", file=sys.stderr)
        return []

    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError as exc:
        print(f"  ! error parseando XML de {url}: {exc}", file=sys.stderr)
        return []

    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = (item.findtext("description") or "").strip()
        pub_date_raw = (item.findtext("pubDate") or "").strip()

        published_iso = None
        if pub_date_raw:
            try:
                published_iso = parsedate_to_datetime(pub_date_raw).astimezone(timezone.utc).isoformat()
            except (TypeError, ValueError):
                published_iso = None

        if title and link:
            items.append({
                "title": title,
                "link": link,
                "summary": description,
                "published": published_iso,
            })
    return items


def build_alias_pattern(alias):
    escaped = re.escape(alias.rstrip(","))
    is_shouty = alias.isupper() and len(alias) <= 5
    flags = 0 if is_shouty else re.IGNORECASE
    return re.compile(r"(?<!\w)" + escaped + r"(?!\w)", flags)


def match_tickers(text, companies):
    matches = []
    for company in companies:
        for alias in company["aliases"]:
            pattern = build_alias_pattern(alias)
            if pattern.search(text):
                matches.append(company)
                break
    return matches


def main():
    sources_cfg = load_json(DATA_DIR / "sources.json")["sources"]
    tickers_cfg = load_json(DATA_DIR / "tickers.json")["companies"]

    all_items = []
    sources_meta = []
    for source in sources_cfg:
        if not source.get("enabled", True):
            continue
        print(f"Descargando: {source['name']} ({source['url']})")
        items = fetch_rss(source["url"])
        print(f"  -> {len(items)} artículos")
        for item in items:
            item["source_id"] = source["id"]
            item["source_name"] = source["name"]
        all_items.extend(items)
        sources_meta.append({
            "id": source["id"],
            "name": source["name"],
            "site_url": source.get("site_url", ""),
            "article_count": len(items),
        })

    # dedupe por link, conservando la primera aparición
    seen_links = set()
    deduped = []
    for item in all_items:
        if item["link"] in seen_links:
            continue
        seen_links.add(item["link"])
        deduped.append(item)

    # ordenar todo por fecha, más reciente primero (sin fecha va al final)
    deduped.sort(key=lambda i: i["published"] or "", reverse=True)

    ticker_buckets = {c["ticker"]: {**c, "news": []} for c in tickers_cfg}

    for item in deduped:
        text = f"{item['title']} {item['summary']}"
        matched = match_tickers(text, tickers_cfg)
        item_tickers = [m["ticker"] for m in matched]
        item["tickers"] = item_tickers
        for company in matched:
            bucket = ticker_buckets[company["ticker"]]
            if len(bucket["news"]) < MAX_ITEMS_PER_TICKER:
                bucket["news"].append({
                    "title": item["title"],
                    "link": item["link"],
                    "summary": item["summary"],
                    "published": item["published"],
                    "source_name": item["source_name"],
                })

    tickers_out = [b for b in ticker_buckets.values() if b["news"]]
    tickers_out.sort(key=lambda b: b["news"][0]["published"] or "", reverse=True)

    latest_out = [
        {
            "title": i["title"],
            "link": i["link"],
            "summary": i["summary"],
            "published": i["published"],
            "source_name": i["source_name"],
            "tickers": i["tickers"],
        }
        for i in deduped[:MAX_LATEST]
    ]

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources_meta,
        "latest": latest_out,
        "tickers": tickers_out,
    }

    out_path = DATA_DIR / "news.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nListo: {len(tickers_out)} acciones con noticias, {len(deduped)} artículos únicos.")
    print(f"Guardado en {out_path}")


if __name__ == "__main__":
    main()
