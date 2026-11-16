"""Job-Quelle: Offizielle Jobsuche-API der Bundesagentur für Arbeit.

Doku: https://jobsuche.api.bund.dev und https://github.com/bundesAPI/jobsuche-api
"""

import base64
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

import requests

import config
from kosten import Verbrauch
from models import Stelle, SuchParameter
from sources.base import JobQuelle

# Stellenart -> Angebotsart der API (1=Arbeit, 4=Ausbildung, 34=Praktikum/Trainee)
ANGEBOTSART = {
    "Vollzeitjob": 1,
    "Werkstudent": 1,  # keine eigene Angebotsart, daher Suchbegriff "Werkstudent"
    "Ausbildung": 4,
    "Praktikum": 34,
}
ARBEITSZEIT = {"Vollzeit": "vz", "Teilzeit": "tz"}

HEADERS = {"X-API-Key": config.BA_API_KEY}
TIMEOUT = 20  # Sekunden


class ArbeitsagenturQuelle(JobQuelle):
    name = "Arbeitsagentur"

    def suche(self, params: SuchParameter, max_treffer: int, verbrauch: Verbrauch) -> List[Stelle]:
        # Die BA-API ist kostenlos, daher wird `verbrauch` hier nicht gebraucht.
        treffer = self._suche_liste(params, max_treffer)
        # Details (Beschreibungstext) für alle Treffer parallel laden
        with ThreadPoolExecutor(max_workers=5) as pool:
            beschreibungen = list(pool.map(self._lade_beschreibung, treffer))
        return [self._zu_stelle(t, b) for t, b in zip(treffer, beschreibungen)]

    def _suche_liste(self, params: SuchParameter, max_treffer: int) -> List[dict]:
        suchbegriffe = []
        if params.stellenart == "Werkstudent":
            suchbegriffe.append("Werkstudent")
        if params.suchbegriff.strip():
            suchbegriffe.append(params.suchbegriff.strip())

        query = {
            "wo": params.ort,
            "umkreis": params.umkreis_km,
            "angebotsart": ANGEBOTSART[params.stellenart],
            "arbeitszeit": ARBEITSZEIT[params.arbeitszeit],
            "size": max_treffer,
            "page": 1,
        }
        if suchbegriffe:
            query["was"] = " ".join(suchbegriffe)

        antwort = requests.get(
            f"{config.BA_BASIS_URL}/pc/v6/jobs", params=query, headers=HEADERS, timeout=TIMEOUT
        )
        antwort.raise_for_status()
        return antwort.json().get("ergebnisliste", [])[:max_treffer]

    def _lade_beschreibung(self, treffer: dict) -> str:
        """Lädt den Anzeigentext. Bei Fehlern (z. B. externe Anzeigen) einfach leer lassen."""
        refnr = treffer.get("referenznummer", "")
        code = base64.b64encode(refnr.encode()).decode()
        try:
            antwort = requests.get(
                f"{config.BA_BASIS_URL}/pc/v4/jobdetails/{code}", headers=HEADERS, timeout=TIMEOUT
            )
            antwort.raise_for_status()
            return antwort.json().get("stellenangebotsBeschreibung", "") or ""
        except (requests.RequestException, ValueError):
            return ""

    def _zu_stelle(self, t: dict, beschreibung: str) -> Stelle:
        refnr = t.get("referenznummer", "")
        link = t.get("externeURL") or f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{refnr}"

        if not beschreibung:
            # Fallback: wenigstens die Berufsbezeichnungen mitgeben
            berufe = ", ".join(t.get("alleBerufe", []))
            beschreibung = f"(Kein Anzeigentext verfügbar.) Beruf(e): {berufe}"

        return Stelle(
            id=refnr,
            # Ausbildungsplätze haben oft keinen Titel -> dann den Beruf nehmen
            titel=t.get("stellenangebotsTitel") or t.get("hauptberuf") or "Ohne Titel",
            firma=t.get("firma", "Unbekannt"),
            ort=_ort_text(t),
            beschreibung=beschreibung[: config.MAX_BESCHREIBUNG_ZEICHEN],
            link=link,
            quelle=self.name,
            gehalt=_gehalt_text(t),
        )


def _ort_text(t: dict) -> str:
    orte = []
    for lok in t.get("stellenlokationen", []):
        adresse = lok.get("adresse", {})
        text = " ".join(x for x in [adresse.get("plz"), adresse.get("ort")] if x)
        if text and text not in orte:
            orte.append(text)
    return ", ".join(orte) or "Ort unbekannt"


def _gehalt_text(t: dict) -> Optional[str]:
    """Gehalt als Text, aber nur, wenn die Anzeige wirklich eins nennt."""
    einheit = {"JAHRESGEHALT": "€/Jahr", "MONATSGEHALT": "€/Monat", "STUNDENLOHN": "€/Stunde"}.get(
        t.get("verguetungsangabe", ""), "€"
    )
    if t.get("festgehalt"):
        return f"{t['festgehalt']:g} {einheit}"
    if t.get("gehaltsspanneVon") and t.get("gehaltsspanneBis"):
        return f"{t['gehaltsspanneVon']:g}–{t['gehaltsspanneBis']:g} {einheit}"
    return None
