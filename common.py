#!/usr/bin/env python3
"""
Utilidades comunes para los generadores de precios.

Centraliza: descarga HTTP, limpieza de HTML, parsing de costes/versiones
y detección de modelos superados. Evita duplicación entre
gen-copilot-models.py y gen-opencode-go-models.py.
"""

import html as _html
import re
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def clean_text(s: str) -> str:
    """Elimina tags HTML, convierte <br> en espacio y decodifica entidades."""
    s = re.sub(r'<\s*br\s*\/?>', ' ', s, flags=re.IGNORECASE)
    s = re.sub(r'<.*?>', '', s, flags=re.S)
    return _html.unescape(s).strip()


def fetch_html(url: str, timeout: int = 15) -> str:
    """Descarga HTML con User-Agent y timeout."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset(failobj="utf-8")
        return resp.read().decode(charset, errors="ignore")


def parse_cost(val) -> float:
    """Convierte un precio string ('$3.00', '-', 'Not applicable') a float."""
    if not val or str(val).strip() in ("-", "None", "Not applicable"):
        return 0.0
    cleaned = re.sub(r"[^0-9.]", "", str(val))
    return float(cleaned or 0)


def parse_family_version(name: str) -> tuple[str, float]:
    """
    Separa familia y versión numérica.
    Ej: 'Claude Sonnet 4.5' -> ('claude sonnet', 4.5)
        'Grok 4.6' -> ('grok', 4.6)
    """
    clean = re.sub(r"\(.*?\)", "", name).strip()
    m_ver = re.search(r"(\d+(?:\.\d+)?)", clean)
    if m_ver:
        ver_num = float(m_ver.group(1))
        family = re.sub(r"\d+(?:\.\d+)?", "", clean)
        family = re.sub(r"[\s\-_]+", " ", family).strip().lower()
        return family, ver_num
    return clean.lower(), 0.0


def normalize_name(n: str) -> str:
    """Normaliza nombre para usar como clave de diccionario (sin paréntesis, alfanumérico)."""
    n = re.sub(r"\s*\(.*?\)", "", n)
    return re.sub(r"[^a-z0-9]", "", n.lower())


def resolve_transitive_superseded(models: list[dict], direct: dict[int, int]) -> None:
    """
    Resuelve cadenas transitivas A->B->C y marca _isDeprecated/_supersededBy
    en el modelo final no superado.
    Modifica `models` in-place.
    """
    for i in list(direct.keys()):
        curr = direct[i]
        visited = {i}
        while curr in direct and curr not in visited:
            visited.add(curr)
            curr = direct[curr]
        models[i]["_isDeprecated"] = True
        models[i]["_supersededBy"] = models[curr].get("name", "")


def build_header_cells(header_groups, cols) -> str:
    """Construye el HTML de 2 filas de cabecera a partir de HEADER_GROUPS y COLS."""
    label_of = dict(cols)
    top_cells, bot_cells = [], []
    for group, gcols in header_groups:
        if group and len(gcols) > 1:
            top_cells.append(f'<th colspan="{len(gcols)}" class="price-group">{group}</th>')
            for key, label in gcols:
                bot_cells.append(f'<th data-k="{label_of[key]}">{label} <span class="arrow"></span></th>')
        else:
            key, label = gcols[0]
            top_cells.append(f'<th rowspan="2" data-k="{label_of[key]}">{label} <span class="arrow"></span></th>')
    return "<tr>" + "".join(top_cells) + "</tr><tr>" + "".join(bot_cells) + "</tr>"
