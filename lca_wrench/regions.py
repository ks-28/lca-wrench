"""Locations for the search: free text to a location code, and the regions that contain it.

"Switzerland", "schweiz" or "CH" all become CH; the search then also accepts the regions around it, nearest first:
CH → Europe (ENTSO-E, UCTE, RER …) → GLO → RoW. ecoinvent and BAFU name the same regions differently (RER, "Europe
without Switzerland", ENTSO-E, UCTE, WEU …); all of them are listed here. RoW ("rest of the world") is specific to
each activity, so it comes last, as the generic fallback. A code this table does not know still matches exactly.
"""

from __future__ import annotations

import re

# code: (English name, German name, continent region)
COUNTRIES = {
    "CH": ("Switzerland", "Schweiz", "EU"), "DE": ("Germany", "Deutschland", "EU"), "AT": ("Austria", "Österreich", "EU"),
    "FR": ("France", "Frankreich", "EU"), "IT": ("Italy", "Italien", "EU"), "LI": ("Liechtenstein", "Liechtenstein", "EU"),
    "NL": ("Netherlands", "Niederlande", "EU"), "BE": ("Belgium", "Belgien", "EU"), "LU": ("Luxembourg", "Luxemburg", "EU"),
    "ES": ("Spain", "Spanien", "EU"), "PT": ("Portugal", "Portugal", "EU"), "GB": ("United Kingdom", "Grossbritannien", "EU"),
    "IE": ("Ireland", "Irland", "EU"), "DK": ("Denmark", "Dänemark", "EU"), "SE": ("Sweden", "Schweden", "EU"),
    "NO": ("Norway", "Norwegen", "EU"), "FI": ("Finland", "Finnland", "EU"), "IS": ("Iceland", "Island", "EU"),
    "PL": ("Poland", "Polen", "EU"), "CZ": ("Czechia", "Tschechien", "EU"), "SK": ("Slovakia", "Slowakei", "EU"),
    "HU": ("Hungary", "Ungarn", "EU"), "SI": ("Slovenia", "Slowenien", "EU"), "HR": ("Croatia", "Kroatien", "EU"),
    "RO": ("Romania", "Rumänien", "EU"), "BG": ("Bulgaria", "Bulgarien", "EU"), "GR": ("Greece", "Griechenland", "EU"),
    "EE": ("Estonia", "Estland", "EU"), "LV": ("Latvia", "Lettland", "EU"), "LT": ("Lithuania", "Litauen", "EU"),
    "RS": ("Serbia", "Serbien", "EU"), "BA": ("Bosnia and Herzegovina", "Bosnien und Herzegowina", "EU"),
    "ME": ("Montenegro", "Montenegro", "EU"), "MK": ("North Macedonia", "Nordmazedonien", "EU"),
    "AL": ("Albania", "Albanien", "EU"), "UA": ("Ukraine", "Ukraine", "EU"), "MT": ("Malta", "Malta", "EU"),
    "CY": ("Cyprus", "Zypern", "EU"), "TR": ("Turkey", "Türkei", "EU"), "RU": ("Russia", "Russland", "EU"),
    "US": ("United States", "USA", "NA"), "CA": ("Canada", "Kanada", "NA"), "MX": ("Mexico", "Mexiko", "LA"),
    "BR": ("Brazil", "Brasilien", "LA"), "AR": ("Argentina", "Argentinien", "LA"), "CL": ("Chile", "Chile", "LA"),
    "CO": ("Colombia", "Kolumbien", "LA"), "PE": ("Peru", "Peru", "LA"), "CN": ("China", "China", "AS"),
    "JP": ("Japan", "Japan", "AS"), "KR": ("South Korea", "Südkorea", "AS"), "IN": ("India", "Indien", "AS"),
    "ID": ("Indonesia", "Indonesien", "AS"), "TH": ("Thailand", "Thailand", "AS"), "VN": ("Vietnam", "Vietnam", "AS"),
    "MY": ("Malaysia", "Malaysia", "AS"), "PH": ("Philippines", "Philippinen", "AS"), "TW": ("Taiwan", "Taiwan", "AS"),
    "PK": ("Pakistan", "Pakistan", "AS"), "BD": ("Bangladesh", "Bangladesch", "AS"), "SG": ("Singapore", "Singapur", "AS"),
    "SA": ("Saudi Arabia", "Saudi-Arabien", "ME"), "AE": ("United Arab Emirates", "Vereinigte Arabische Emirate", "ME"),
    "IR": ("Iran", "Iran", "ME"), "IL": ("Israel", "Israel", "ME"), "QA": ("Qatar", "Katar", "ME"),
    "ZA": ("South Africa", "Südafrika", "AF"), "EG": ("Egypt", "Ägypten", "AF"), "NG": ("Nigeria", "Nigeria", "AF"),
    "MA": ("Morocco", "Marokko", "AF"), "KE": ("Kenya", "Kenia", "AF"), "AU": ("Australia", "Australien", "OC"),
    "NZ": ("New Zealand", "Neuseeland", "OC"),
}

# continent region: the names ecoinvent and BAFU use for it, nearest (smallest) first
REGIONS = {
    "EU": ["ENTSO-E", "ENTSO", "UCTE", "WEU", "RER w/o CH", "Europe without Switzerland", "Europe without Austria",
           "Europe, without Russia and Turkey", "RER w/o CH+DE", "RER"],
    "NA": ["RNA", "US-NPCC", "NAFTA"], "LA": ["RLA"], "AS": ["RAS"], "ME": ["RME"], "AF": ["RAF"], "OC": ["OCE"],
}
REGION_NAMES = {"europe": "RER", "europa": "RER", "global": "GLO", "world": "GLO", "welt": "GLO", "asia": "RAS",
                "asien": "RAS", "africa": "RAF", "afrika": "RAF", "north america": "RNA", "nordamerika": "RNA",
                "latin america": "RLA", "lateinamerika": "RLA", "middle east": "RME", "oceania": "OCE"}
# regions that do not contain a given country, although they are in its continent
_EXCLUDES = {"Europe without Switzerland": {"CH"}, "RER w/o CH": {"CH"}, "RER w/o CH+DE": {"CH", "DE"},
             "Europe without Austria": {"AT"}, "Europe, without Russia and Turkey": {"RU", "TR"}}
# grids that only part of Europe belongs to (UCTE/ENTSO-E: continental grid; NORDEL etc. are not listed)
_NOT_IN_UCTE = {"GB", "IE", "NO", "SE", "FI", "DK", "IS", "EE", "LV", "LT", "CY", "MT", "RU", "UA", "TR"}


def resolve(text: str | None) -> str | None:
    """A location code for free text: a code as it is ("CH", "RER", "ENTSO-E"), or a country or region name."""
    s = (text or "").strip()
    if not s:
        return None
    low = s.lower()
    if low in REGION_NAMES:
        return REGION_NAMES[low]
    for code, (en, de, _c) in COUNTRIES.items():
        if low in (en.lower(), de.lower(), code.lower()):
            return code
    for code, (en, de, _c) in COUNTRIES.items():  # a name started ("switz", "deutsch")
        if len(low) >= 4 and (en.lower().startswith(low) or de.lower().startswith(low)):
            return code
    return s.upper() if re.fullmatch(r"[A-Za-z]{2,3}", s) else s


def chain(code: str | None) -> list[str]:
    """The code and the regions containing it, nearest first, ending with GLO and RoW."""
    if not code:
        return []
    out = [code]
    cont = COUNTRIES.get(code, (None, None, None))[2]
    if cont is None:  # a region: itself, then the world
        for c, names in REGIONS.items():
            if code in names:
                out += names[names.index(code) + 1:]
    else:
        for r in REGIONS.get(cont, []):
            if code in _EXCLUDES.get(r, ()):
                continue
            if r in ("UCTE", "ENTSO", "WEU") and code in _NOT_IN_UCTE:
                continue
            out.append(r)
    for g in ("GLO", "RoW"):
        if g not in out:
            out.append(g)
    return out


def label(code: str | None) -> str:
    c = COUNTRIES.get(code or "")
    return f"{code} ({c[0]})" if c else (code or "")


def find_in_query(q: str) -> tuple[str, str | None]:
    """A location named at the end of the query ("electricity low voltage switzerland") taken out of it."""
    words = q.split()
    for n in (3, 2, 1):
        if len(words) > n:
            tail = " ".join(words[-n:])
            low = tail.lower()
            if low in REGION_NAMES or any(low in (en.lower(), de.lower()) for en, de, _c in COUNTRIES.values()) \
                    or (n == 1 and tail.isupper() and tail in COUNTRIES):
                return " ".join(words[:-n]), resolve(tail)
    return q, None
