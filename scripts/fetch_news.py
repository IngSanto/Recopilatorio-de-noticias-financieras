#!/usr/bin/env python3
"""Descarga noticias de las fuentes configuradas y las relaciona con acciones/tickers.

Uso:
    python3 scripts/fetch_news.py

Lee:
    data/sources.json  -> lista de fuentes RSS
    data/tickers.json  -> diccionario empresa -> ticker

Escribe:
    data/news.json -> noticias agrupadas por ticker + las que no aplican a ninguna acción
"""
import json
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
USER_AGENT = "Mozilla/5.0 (compatible; RecopiladorNoticiasFinancieras/1.0)"
MAX_ITEMS_PER_TICKER = 10
MAX_SIN_ACCION_TOTAL = 40
REQUEST_TIMEOUT = 25

# Hueco más largo entre corridas programadas (07:30 -> 15:30 -> 22:30 CDMX).
# Si un feed abarca menos horas que esto, entre una corrida y otra se pierden
# noticias sin que nadie se entere. El script lo avisa.
HUECO_MAX_HORAS = 9


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_fecha(texto):
    """Los feeds no se ponen de acuerdo en el formato de fecha.

    Bloomberg Línea y CNBC usan RFC 2822 ('Mon, 07 Sep 2026 21:16:30 +0000'),
    Yahoo usa ISO 8601 ('2026-09-06T23:33:54Z') e Investing.com manda
    '2026-09-08 03:33:31' sin zona horaria. Se intentan los tres.
    """
    if not texto:
        return None
    texto = texto.strip()
    try:
        d = parsedate_to_datetime(texto)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        pass
    candidato = re.sub(r"Z$", "+00:00", texto)
    for intento in (candidato, candidato.replace(" ", "T", 1)):
        try:
            d = datetime.fromisoformat(intento)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def limpiar(texto):
    """Quita etiquetas HTML del resumen; varios feeds meten <p> e <img>."""
    if not texto:
        return ""
    sin_tags = re.sub(r"<[^>]+>", " ", texto)
    return re.sub(r"\s+", " ", unescape(sin_tags)).strip()


def fetch_rss(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        print(f"  ! error descargando: {exc}", file=sys.stderr)
        return []

    try:
        root = ElementTree.fromstring(raw)
    except ElementTree.ParseError as exc:
        print(f"  ! error parseando XML: {exc}", file=sys.stderr)
        return []

    items = []
    for item in root.findall(".//item"):
        title = limpiar(item.findtext("title"))
        link = (item.findtext("link") or "").strip()
        summary = limpiar(item.findtext("description"))
        fecha = parse_fecha(item.findtext("pubDate"))
        if title and link:
            items.append({
                "title": title,
                "link": link,
                "summary": summary,
                "published": fecha.astimezone(timezone.utc).isoformat() if fecha else None,
                "_fecha": fecha,
            })
    return items


def build_alias_pattern(alias):
    """Alias en MAYÚSCULAS y corto (BYD, AMD, UPS) se busca respetando mayúsculas.

    Sin esto, 'BP' pegaría dentro de cualquier palabra y 'AMD' aparecería por
    accidente. El resto se busca sin distinguir mayúsculas.
    """
    escaped = re.escape(alias.rstrip(","))
    es_sigla = alias.isupper() and len(alias) <= 5
    flags = 0 if es_sigla else re.IGNORECASE
    return re.compile(r"(?<!\w)" + escaped + r"(?!\w)", flags)


def compilar_patrones(companies):
    return [(c, [build_alias_pattern(a) for a in c["aliases"]]) for c in companies]


def match_tickers(texto, patrones):
    return [c for c, pats in patrones if any(p.search(texto) for p in pats)]


def orden_relevancia(bucket):
    """Ordena las acciones por qué tan pronto merecen tu atención.

    Ordenar solo por fecha deja arriba acciones con una sola nota y entierra a
    las que traen diez. Ordenar solo por cantidad esconde lo que acaba de pasar.
    Así que primero se agrupa por qué tan fresca es la nota más nueva (menos de
    6 h, menos de 24 h, menos de 72 h, más viejo) y dentro de cada grupo mandan
    las acciones con más cobertura.
    """
    mas_nueva = parse_fecha(bucket["news"][0]["published"])
    if mas_nueva is None:
        horas = float("inf")
    else:
        horas = (datetime.now(timezone.utc) - mas_nueva).total_seconds() / 3600
    grupo = 0 if horas < 12 else 1 if horas < 36 else 2 if horas < 96 else 3
    return (grupo, -len(bucket["news"]), horas)


def revisar_ventana(nombre, items):
    """Avisa si el feed abarca menos horas que el hueco entre corridas."""
    fechas = sorted(i["_fecha"] for i in items if i["_fecha"])
    if len(fechas) < 2:
        return None
    horas = (fechas[-1] - fechas[0]).total_seconds() / 3600
    if horas < HUECO_MAX_HORAS:
        print(f"  ! OJO: ventana de {horas:.1f} h < hueco de {HUECO_MAX_HORAS} h "
              f"entre corridas. '{nombre}' puede estar perdiendo noticias.", file=sys.stderr)
    return round(horas, 1)


def main():
    sources_cfg = load_json(DATA_DIR / "sources.json")["sources"]
    companies = load_json(DATA_DIR / "tickers.json")["companies"]
    patrones = compilar_patrones(companies)

    all_items = []
    sources_meta = []
    for source in sources_cfg:
        if not source.get("enabled", True):
            continue
        print(f"Descargando: {source['name']}")
        items = fetch_rss(source["url"])
        ventana = revisar_ventana(source["name"], items)
        print(f"  -> {len(items)} artículos"
              + (f", ventana {ventana} h" if ventana is not None else ""))
        for item in items:
            item["source_id"] = source["id"]
            item["source_name"] = source["name"]
            item["source_short"] = source.get("short_name", source["name"])
            item["source_scope"] = source.get("scope", "")
            item["max_sin_accion"] = source.get("max_sin_accion", 6)
        if not items:
            print(f"  ! '{source['name']}' no devolvió nada en esta corrida.", file=sys.stderr)
        all_items.extend(items)
        sources_meta.append({
            "id": source["id"],
            "name": source["name"],
            "short_name": source.get("short_name", source["name"]),
            "scope": source.get("scope", ""),
            "lang": source.get("lang", ""),
            "site_url": source.get("site_url", ""),
            "article_count": len(items),
            "ventana_horas": ventana,
            "ok": bool(items),
        })

    # dedupe por link
    vistos = set()
    deduped = []
    for item in all_items:
        if item["link"] in vistos:
            continue
        vistos.add(item["link"])
        deduped.append(item)

    deduped.sort(key=lambda i: i["published"] or "", reverse=True)

    ticker_buckets = {c["ticker"]: {**c, "news": []} for c in companies}
    sin_accion = []
    cupo_usado = {}

    for item in deduped:
        texto = f"{item['title']} {item['summary']}"
        encontrados = match_tickers(texto, patrones)
        nota = {
            "title": item["title"],
            "link": item["link"],
            "summary": item["summary"],
            "published": item["published"],
            "source_short": item["source_short"],
            "source_scope": item["source_scope"],
        }

        if encontrados:
            # Las notas que sí tocan una acción se guardan todas: son la señal.
            for company in encontrados:
                bucket = ticker_buckets[company["ticker"]]
                if len(bucket["news"]) < MAX_ITEMS_PER_TICKER:
                    bucket["news"].append(nota)
        else:
            # Las que no tocan ninguna acción son contexto: se limitan por fuente
            # para que un feed de alto volumen no se coma la sección.
            sid = item["source_id"]
            if cupo_usado.get(sid, 0) < item["max_sin_accion"]:
                cupo_usado[sid] = cupo_usado.get(sid, 0) + 1
                sin_accion.append({**nota, "tickers": []})

    tickers_out = [b for b in ticker_buckets.values() if b["news"]]
    tickers_out.sort(key=orden_relevancia)
    for b in tickers_out:
        b.pop("aliases", None)

    sin_accion = sin_accion[:MAX_SIN_ACCION_TOTAL]

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources_meta,
        "tickers": tickers_out,
        "sin_accion": sin_accion,
        "totales": {
            "articulos": len(deduped),
            "acciones_con_noticias": len(tickers_out),
            "sin_accion": len(sin_accion),
        },
    }

    out_path = DATA_DIR / "news.json"

    # Cortacircuitos: si un feed falla, esta corrida trae mucho menos de lo
    # normal. Publicar eso borraría de la página noticias que sí seguían
    # vigentes, así que se conserva lo anterior y se avisa.
    if out_path.exists():
        try:
            previo = load_json(out_path)["totales"]["articulos"]
        except (KeyError, ValueError):
            previo = 0
        if previo and len(deduped) < previo * 0.6:
            print(f"\n! Esta corrida trajo {len(deduped)} artículos contra {previo} de la anterior "
                  f"({len(deduped)/previo:.0%}). Parece falla de alguna fuente, no menos noticias.",
                  file=sys.stderr)
            print("! No se sobrescribe data/news.json. Se conserva lo anterior.", file=sys.stderr)
            return 1

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{len(deduped)} artículos únicos | {len(tickers_out)} acciones con noticias "
          f"| {len(sin_accion)} sin acción")
    print(f"Guardado en {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
