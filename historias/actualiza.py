"""Lee los RSS de los podcasts de historia y genera historias/historias.json.

Solo guarda título, podcast, duración y el enlace original al audio: la app
reproduce cada episodio directamente desde su fuente, no se copia nada.
Se ejecuta cada semana con GitHub Actions (.github/workflows/historias.yml).
"""
import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
MIN_SEG = 35 * 60      # "más o menos una hora"
MAX_SEG = 100 * 60
ITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"


def segundos(txt):
    if not txt:
        return None
    txt = txt.strip()
    try:
        if txt.isdigit():
            return int(txt)
        n = 0
        for p in txt.split(":"):
            n = n * 60 + int(float(p))
        return n
    except ValueError:
        return None


def leer_feed(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Lluvia PWA; lector RSS de podcasts)",
        "Accept": "application/rss+xml, application/xml, text/xml",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return ET.fromstring(r.read())


def main():
    podcasts = json.load(open(os.path.join(AQUI, "podcasts.json"), encoding="utf-8"))
    salida = os.path.join(AQUI, "historias.json")
    anterior = []
    if os.path.exists(salida):
        anterior = json.load(open(salida, encoding="utf-8"))

    episodios, fallos = [], []
    for pc in podcasts:
        try:
            raiz = leer_feed(pc["feed"])
        except Exception as e:  # un feed caído no tumba a los demás
            fallos.append(pc["nombre"])
            print(f"!! {pc['nombre']}: {e}", file=sys.stderr)
            # conserva lo que ya teníamos de ese podcast
            episodios += [x for x in anterior if x.get("p") == pc["nombre"]]
            continue
        n = 0
        for item in raiz.iter("item"):
            enc = item.find("enclosure")
            if enc is None or not enc.get("url"):
                continue
            d = segundos(item.findtext(f"{ITUNES}duration"))
            if d is None or not (MIN_SEG <= d <= MAX_SEG):
                continue
            fecha = ""
            try:
                fecha = parsedate_to_datetime(item.findtext("pubDate")).date().isoformat()
            except Exception:
                pass
            episodios.append({
                "t": (item.findtext("title") or "").strip(),
                "p": pc["nombre"],
                "u": enc.get("url"),
                "d": d,
                "f": fecha,
            })
            n += 1
        print(f"{pc['nombre']}: {n} episodios")

    # sin duplicados (mismo audio en dos feeds)
    vistos, unicos = set(), []
    for e in episodios:
        if e["u"] not in vistos:
            vistos.add(e["u"])
            unicos.append(e)

    if len(unicos) < 50:
        sys.exit(f"Solo {len(unicos)} episodios: algo ha fallado, no se sobrescribe la lista.")

    with open(salida, "w", encoding="utf-8") as f:
        json.dump(unicos, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Total: {len(unicos)} episodios. Fallos: {fallos or 'ninguno'}")


if __name__ == "__main__":
    main()
