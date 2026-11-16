"""Führt doppelte Stellen zusammen (gleiche Firma + ähnlicher Titel, z. B. aus beiden Quellen)."""

import re
from difflib import SequenceMatcher
from typing import List

from models import Stelle

AEHNLICHKEIT_AB = 0.8  # 0..1 – ab hier gelten zwei Titel als "dieselbe Stelle"

RECHTSFORMEN = r"\b(gmbh|ag|se|ug|kg|kgaa|ohg|gbr|e\.?\s?v|mbh|co|inc|ltd|haftungsbeschränkt)\b"
GENDER = r"\(\s*[mwfdxgn]\s*(/\s*[mwfdxgn]\s*)*\)|\b[mwfd]/[mwfd](/[mwfdx])?\b|\(\s*all genders?\s*\)|\(\s*gn\s*\)"


def _firma_key(firma: str) -> str:
    f = firma.lower()
    f = re.sub(RECHTSFORMEN, " ", f)
    f = re.sub(r"[^\wäöüß]+", " ", f)
    return " ".join(f.split())


def _titel_key(titel: str) -> str:
    t = re.sub(GENDER, " ", titel.lower())
    t = re.sub(r"[^\wäöüß]+", " ", t)
    return " ".join(t.split())


def ist_doppelt(a: Stelle, b: Stelle) -> bool:
    if _firma_key(a.firma) != _firma_key(b.firma):
        return False
    return SequenceMatcher(None, _titel_key(a.titel), _titel_key(b.titel)).ratio() >= AEHNLICHKEIT_AB


def _verschmelze(a: Stelle, b: Stelle) -> Stelle:
    """Behält die Stelle mit dem längeren Anzeigentext und merkt sich den anderen Link."""
    haupt, neben = (a, b) if len(a.beschreibung) >= len(b.beschreibung) else (b, a)
    quellen = list(dict.fromkeys(haupt.quelle.split(" + ") + neben.quelle.split(" + ")))
    haupt.quelle = " + ".join(quellen)
    for link in [neben.link] + neben.weitere_links:
        if link != haupt.link and link not in haupt.weitere_links:
            haupt.weitere_links.append(link)
    haupt.gehalt = haupt.gehalt or neben.gehalt
    return haupt


def fuehre_zusammen(stellen: List[Stelle]) -> List[Stelle]:
    ergebnis: List[Stelle] = []
    for stelle in stellen:
        for i, vorhanden in enumerate(ergebnis):
            if ist_doppelt(vorhanden, stelle):
                ergebnis[i] = _verschmelze(vorhanden, stelle)
                break
        else:
            ergebnis.append(stelle)
    return ergebnis
