"""Job-Quelle: Websuche der Claude API.

Claude sucht im Web nach Stellen (Karriereseiten, Bewerbungsportale) und gibt sie als JSON zurück.
Schutz vor erfundenen Stellen: Eine Stelle wird nur übernommen, wenn ihr Link
tatsächlich in den Suchergebnissen vorkam.
"""

from typing import List, Set
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import anthropic
from pydantic import BaseModel, Field

import config
from kosten import Verbrauch
from models import Stelle, SuchParameter
from sources.base import JobQuelle

MAX_FORTSETZUNGEN = 3  # wie oft eine pausierte Suche (pause_turn) fortgesetzt wird


class WebStelle(BaseModel):
    titel: str = Field(description="Titel der Stelle")
    firma: str = Field(description="Name der Firma")
    ort: str = Field(description="Arbeitsort, z. B. 'Berlin' oder 'Remote'")
    beschreibung: str = Field(description="2–4 Sätze: Aufgaben und Anforderungen laut Anzeige")
    link: str = Field(description="URL exakt so, wie sie in den Suchergebnissen stand")


class WebStellenListe(BaseModel):
    stellen: List[WebStelle]


ANWEISUNGEN = """Du suchst im Web nach aktuellen, konkreten Stellenanzeigen für eine Person.

Vorgehen:
- Nutze die Websuche mit gezielten Suchanfragen auf Deutsch (und ggf. Englisch).
- Bevorzuge Karriereseiten von Firmen und Startups sowie Bewerbungsportale wie
  jobs.personio.de, boards.greenhouse.io, jobs.ashbyhq.com, jobs.lever.co und join.com.
- Übernimm nur Stellen, die zur gesuchten Stellenart und zum Ort passen und die du in den
  Suchergebnissen tatsächlich gesehen hast.

Wichtig:
- Der Link muss EXAKT eine URL aus den Suchergebnissen sein. Erfinde oder verändere keine Links.
- Erfinde keine Stellen, Firmen oder Details. Lieber weniger Stellen als ungenaue.
- Höchstens {max_treffer} Stellen. Wenn du nichts Passendes findest, gib eine leere Liste zurück."""


class ClaudeWebsucheQuelle(JobQuelle):
    name = "Websuche"

    def suche(self, params: SuchParameter, max_treffer: int, verbrauch: Verbrauch) -> List[Stelle]:
        self.hinweise = []
        max_treffer = min(max_treffer, config.WEB_MAX_TREFFER)
        client = anthropic.Anthropic()

        tool = {
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": config.WEB_MAX_SUCHEN,
            "blocked_domains": config.WEB_GESPERRTE_DOMAINS,
            "user_location": {
                "type": "approximate",
                "city": params.ort,
                "country": "DE",
                "timezone": "Europe/Berlin",
            },
        }
        messages = [{"role": "user", "content": _suchauftrag(params)}]
        gefundene_urls: Set[str] = set()

        try:
            for _ in range(MAX_FORTSETZUNGEN + 1):
                antwort = client.messages.parse(
                    model=config.CLAUDE_MODELL,
                    max_tokens=8000,
                    system=ANWEISUNGEN.format(max_treffer=max_treffer),
                    tools=[tool],
                    messages=messages,
                    output_format=WebStellenListe,
                    output_config={"effort": "low"},
                )
                verbrauch.add(antwort.usage)
                gefundene_urls |= _urls_aus_suchergebnissen(antwort.content)
                if antwort.stop_reason != "pause_turn":
                    break
                # Suche wurde pausiert: Antwort unverändert zurückschicken, dann geht es weiter
                messages.append({"role": "assistant", "content": antwort.content})
        except anthropic.APIError as e:
            self.hinweise.append(f"Websuche fehlgeschlagen: {e}")
            return []

        if antwort.parsed_output is None:
            self.hinweise.append("Websuche: Claude hat keine gültige Liste geliefert.")
            return []

        stellen, verworfen = [], 0
        for w in antwort.parsed_output.stellen[:max_treffer]:
            if normalisiere_url(w.link) not in gefundene_urls:
                verworfen += 1  # Link kam nicht in den Suchergebnissen vor -> nicht vertrauenswürdig
                continue
            stellen.append(
                Stelle(
                    id=w.link,
                    titel=w.titel,
                    firma=w.firma,
                    ort=w.ort,
                    beschreibung=w.beschreibung,
                    link=w.link,
                    quelle=self.name,
                )
            )
        if verworfen:
            self.hinweise.append(
                f"Websuche: {verworfen} Treffer verworfen, weil der Link nicht in den Suchergebnissen vorkam."
            )
        return stellen


def _suchauftrag(params: SuchParameter) -> str:
    teile = [
        f"Gesuchte Stellenart: {params.stellenart} ({params.arbeitszeit})",
        f"Ort: {params.ort}, Umkreis {params.umkreis_km} km",
    ]
    if params.suchbegriff.strip():
        teile.append(f"Suchbegriff: {params.suchbegriff.strip()}")
    if params.interessen.strip():
        teile.append(f"Interessen/Branchen: {params.interessen.strip()}")
    return "Finde passende Stellenanzeigen.\n" + "\n".join(teile)


def _urls_aus_suchergebnissen(content) -> Set[str]:
    urls = set()
    for block in content:
        if block.type != "web_search_tool_result":
            continue
        if not isinstance(block.content, list):  # Fehler-Objekt statt Ergebnisliste
            continue
        for ergebnis in block.content:
            url = getattr(ergebnis, "url", None)
            if url:
                urls.add(normalisiere_url(url))
    return urls


def normalisiere_url(url: str) -> str:
    """Macht URLs vergleichbar: Host klein, ohne www., ohne / am Ende, ohne #… und utm_-Parameter."""
    teile = urlsplit(url.strip())
    host = teile.netloc.lower().removeprefix("www.")
    pfad = teile.path.rstrip("/")
    query = urlencode([(k, v) for k, v in parse_qsl(teile.query) if not k.lower().startswith("utm_")])
    return urlunsplit((teile.scheme.lower() or "https", host, pfad, query, ""))
