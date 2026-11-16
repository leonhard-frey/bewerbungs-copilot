"""Prüft Web-Treffer: Jede Stelle wird mit dem Web-Fetch-Tool der Claude API geöffnet.

- Seite nicht erreichbar oder Anzeige gelöscht (z. B. 404/410)  -> verwerfen
- Sammel- oder Übersichtsseite -> Claude sucht den Link zur konkreten Anzeige und öffnet ihn;
  klappt das nicht -> verwerfen
- Anzeige offen -> der volle Anzeigentext wird übernommen (wörtlich aus dem Abruf, nicht von Claude
  umformuliert), damit die Bewertung so genau wird wie bei der Arbeitsagentur.

Schutz vor Fehlern: Eine Stelle gilt nur als bestätigt, wenn ihre Anzeigen-URL in diesem Durchlauf
tatsächlich erfolgreich abgerufen wurde. Claudes Einschätzung allein reicht nicht.
"""

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import List, Literal, Optional, Tuple

import anthropic
from pydantic import BaseModel, Field

import config
from kosten import Verbrauch
from models import Stelle
from sources.urls import normalisiere_url

MAX_FORTSETZUNGEN = 2  # wie oft eine pausierte Prüfung (pause_turn) fortgesetzt wird
MIN_ANZEIGE_ZEICHEN = 400  # weniger Text = keine echte Anzeige (z. B. nur Cookie-Hinweis)


class PruefAntwort(BaseModel):
    status: Literal["offen", "geloescht", "sammelseite", "nicht_erreichbar", "kein_inhalt"]
    anzeigen_url: str = Field(description="Exakt die URL der konkreten Anzeige, die du geöffnet hast (sonst leer)")
    titel: str = Field(description="Titel laut Anzeige (sonst leer)")
    firma: str = Field(description="Firma laut Anzeige (sonst leer)")
    ort: str = Field(description="Arbeitsort laut Anzeige (sonst leer)")
    gehalt: Optional[str] = Field(description="Gehalt/Vergütung, nur wenn die Anzeige eins nennt, sonst null")
    grund: str = Field(description="Ein kurzer Satz auf Deutsch, warum du so entschieden hast")


ANWEISUNGEN = """Du prüfst einen Treffer aus einer Websuche nach Stellenanzeigen. Öffne die angegebene URL
mit dem Tool web_fetch und entscheide, was die Seite ist:

- offen: eine einzelne, noch offene Stellenanzeige für die gesuchte Stelle.
- geloescht: Die Seite sagt, dass die Stelle nicht mehr verfügbar, besetzt oder abgelaufen ist.
- sammelseite: eine Übersichts- oder Sammelseite (Jobliste, Karriereseite einer Firma, Suchergebnisse,
  Blogartikel). Suche dort den Link zur gesuchten Stelle (gleiche Firma, gleicher oder sehr ähnlicher
  Titel) und öffne ihn mit web_fetch. Entscheide dann anhand der geöffneten Anzeige (offen/geloescht/…).
  Nur wenn es keinen passenden Link gibt oder er nicht funktioniert, antworte mit sammelseite.
- nicht_erreichbar: Der Abruf ist fehlgeschlagen.
- kein_inhalt: Die Seite wurde geladen, enthält aber keinen lesbaren Anzeigentext.

Regeln:
- anzeigen_url ist exakt die URL der konkreten Anzeige, die du mit web_fetch geöffnet hast.
- titel, firma, ort und gehalt nur so, wie sie in der Anzeige stehen. Erfinde nichts.
- Öffne höchstens {max_abrufe} Seiten."""

FEHLER_GRUND = {
    "url_not_accessible": "Seite nicht erreichbar oder Anzeige gelöscht (HTTP-Fehler, z. B. 404/410)",
    "url_not_allowed": "Seite erlaubt keinen automatischen Abruf",
    "unsupported_content_type": "Seitentyp wird nicht unterstützt",
    "too_many_requests": "Seite vorübergehend nicht abrufbar (zu viele Anfragen)",
    "unavailable": "Seite vorübergehend nicht abrufbar",
    "url_too_long": "Link zu lang zum Abrufen",
}
STATUS_GRUND = {
    "geloescht": "Anzeige gelöscht oder abgelaufen",
    "sammelseite": "Sammel-/Übersichtsseite, konkrete Anzeige nicht gefunden",
    "nicht_erreichbar": "Seite nicht erreichbar",
    "kein_inhalt": "Seite enthält keinen lesbaren Anzeigentext",
}


@dataclass
class PruefBericht:
    """Ergebnis der Prüfung für die Anzeige in der App."""

    geprueft: int = 0
    bestaetigt: int = 0
    direktlink_gefunden: int = 0  # davon: über eine Sammelseite zur konkreten Anzeige gefunden
    verworfen: List[Tuple[str, str]] = field(default_factory=list)  # (Stelle, Grund)
    verbrauch: Verbrauch = field(default_factory=Verbrauch)


@dataclass
class _Abruf:
    url: str
    text: Optional[str] = None  # None = Fehler
    fehler: Optional[str] = None


def pruefe_web_stellen(stellen: List[Stelle], verbrauch: Verbrauch) -> Tuple[List[Stelle], PruefBericht]:
    """Prüft alle Web-Stellen parallel. Gibt die bestätigten Stellen und einen Bericht zurück."""
    bericht = PruefBericht(geprueft=len(stellen))
    if not stellen:
        return [], bericht

    client = anthropic.Anthropic()
    with ThreadPoolExecutor(max_workers=config.PARALLELE_BEWERTUNGEN) as pool:
        ergebnisse = list(pool.map(lambda s: _pruefe(client, s, bericht.verbrauch), stellen))

    bestaetigt = []
    for stelle, (neu, grund, ueber_sammelseite) in zip(stellen, ergebnisse):
        if neu is None:
            bericht.verworfen.append((f"{stelle.titel} – {stelle.firma}", grund))
        else:
            bestaetigt.append(neu)
            bericht.direktlink_gefunden += ueber_sammelseite
    bericht.bestaetigt = len(bestaetigt)
    verbrauch.plus(bericht.verbrauch)
    return bestaetigt, bericht


def _pruefe(client: anthropic.Anthropic, stelle: Stelle, verbrauch: Verbrauch) -> Tuple[Optional[Stelle], str, bool]:
    """Gibt (geprüfte Stelle oder None, Grund fürs Verwerfen, über Sammelseite gefunden) zurück."""
    tool = {
        "type": "web_fetch_20250910",  # einfache Version: liefert den Seitentext direkt, ohne Code-Ausführung
        "name": "web_fetch",
        "max_uses": config.WEB_FETCH_MAX_PRO_STELLE,
        "max_content_tokens": config.WEB_FETCH_MAX_TOKENS,  # begrenzt den Inhalt pro Seite (Kosten)
        "blocked_domains": config.WEB_GESPERRTE_DOMAINS,
    }
    auftrag = (
        f"Gesuchte Stelle: {stelle.titel}\nFirma: {stelle.firma}\nOrt: {stelle.ort}\n"
        f"URL: {stelle.link}"  # die URL muss in der Nachricht stehen, sonst darf web_fetch sie nicht öffnen
    )
    messages = [{"role": "user", "content": auftrag}]
    abrufe: List[_Abruf] = []

    try:
        for _ in range(MAX_FORTSETZUNGEN + 1):
            antwort = client.messages.parse(
                model=config.CLAUDE_MODELL,
                max_tokens=3000,
                system=ANWEISUNGEN.format(max_abrufe=config.WEB_FETCH_MAX_PRO_STELLE),
                tools=[tool],
                messages=messages,
                output_format=PruefAntwort,
                output_config={"effort": "low"},
            )
            verbrauch.add(antwort.usage)
            abrufe += _abrufe_aus(antwort.content)
            if antwort.stop_reason != "pause_turn":
                break
            messages.append({"role": "assistant", "content": antwort.content})
    except anthropic.APIError as e:
        return None, f"Prüfung fehlgeschlagen ({type(e).__name__})", False

    if not abrufe:
        return None, "Seite wurde nicht geöffnet", False
    erster = abrufe[0]
    if erster.fehler and len(abrufe) == 1:
        return None, FEHLER_GRUND.get(erster.fehler, f"Abruf fehlgeschlagen ({erster.fehler})"), False

    p = antwort.parsed_output
    if p is None:
        return None, "Claude hat kein gültiges Prüfergebnis geliefert", False
    if p.status != "offen":
        return None, STATUS_GRUND[p.status] + (f": {p.grund}" if p.grund else ""), False

    # Claude sagt "offen" -> nur glauben, wenn genau diese Anzeige wirklich abgerufen wurde
    ziel = normalisiere_url(p.anzeigen_url) if p.anzeigen_url else ""
    treffer = next((a for a in abrufe if a.text is not None and normalisiere_url(a.url) == ziel), None)
    if treffer is None:
        return None, "Anzeige-Link konnte nicht bestätigt werden (nicht erfolgreich abgerufen)", False

    text = bereinige_text(treffer.text)
    if len(text) < MIN_ANZEIGE_ZEICHEN:
        return None, STATUS_GRUND["kein_inhalt"], False

    ueber_sammelseite = normalisiere_url(treffer.url) != normalisiere_url(stelle.link)
    geprueft = Stelle(
        id=treffer.url,
        titel=p.titel.strip() or stelle.titel,
        firma=p.firma.strip() or stelle.firma,
        ort=p.ort.strip() or stelle.ort,
        beschreibung=text[: config.MAX_BESCHREIBUNG_ZEICHEN],
        link=treffer.url,
        quelle=stelle.quelle,
        gehalt=(p.gehalt or "").strip() or None,
    )
    return geprueft, "", ueber_sammelseite


def _abrufe_aus(content) -> List[_Abruf]:
    """Sammelt alle web_fetch-Aufrufe einer Antwort: angefragte URL + Text oder Fehlercode."""
    urls = {b.id: b.input.get("url", "") for b in content if b.type == "server_tool_use" and b.name == "web_fetch"}
    abrufe = []
    for b in content:
        if b.type != "web_fetch_tool_result":
            continue
        url = urls.get(b.tool_use_id, "")
        ergebnis = b.content
        if getattr(ergebnis, "type", "") != "web_fetch_result":  # Fehler-Objekt
            abrufe.append(_Abruf(url, fehler=getattr(ergebnis, "error_code", "unbekannt")))
            continue
        quelle = ergebnis.content.source
        if getattr(quelle, "type", "") != "text":  # z. B. PDF als base64 – wird nicht ausgewertet
            abrufe.append(_Abruf(url or ergebnis.url, fehler="unsupported_content_type"))
            continue
        abrufe.append(_Abruf(url or ergebnis.url, text=quelle.data))
    return abrufe


def bereinige_text(text: str) -> str:
    """Entfernt Metadaten-Kopf, Bilder und Link-Adressen aus dem abgerufenen Markdown."""
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)  # Metadaten-Kopf (canonical, meta-…)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)  # Bilder
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # [Linktext](url) -> Linktext
    text = re.sub(r"\n\s*\n+", "\n\n", text)  # mehrfache Leerzeilen
    return text.strip()
