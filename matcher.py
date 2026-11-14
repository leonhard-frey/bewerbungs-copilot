"""Bewertung: Claude vergleicht jede Stelle mit Lebenslauf und Wünschen."""

from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List, Optional

import anthropic

import config
from models import Bewertung, Ergebnis, Stelle, SuchParameter

ANWEISUNGEN = """Du bist ein erfahrener Karriereberater. Du bewertest, wie gut eine Stellenanzeige
zu einer Person passt. Grundlage sind ihr Lebenslauf und ihre Wünsche.

Regeln:
- punktzahl: ganze Zahl von 1 (passt gar nicht) bis 100 (passt perfekt).
- Bewerte vor allem Qualifikationen, Erfahrung, Fähigkeiten und die Interessen/Branchen der Person.
- Gehalt: Berücksichtige es NUR, wenn in der Anzeige ein Gehalt genannt ist. Steht keins drin,
  ignoriere das Thema Gehalt komplett (keine Abzüge, nicht als Lücke nennen).
- begruendung: 1–2 kurze Sätze auf Deutsch.
- staerken und luecken: je 1–4 kurze Stichpunkte auf Deutsch.
- Sei ehrlich und realistisch, nicht übertrieben positiv."""


def _profil_text(lebenslauf: str, params: SuchParameter) -> str:
    gehalt = f"{params.gehalt} € pro Jahr" if params.gehalt else "keine Angabe"
    return f"""{ANWEISUNGEN}

## Wünsche der Person
- Gesuchte Stellenart: {params.stellenart}
- Arbeitszeit: {params.arbeitszeit}
- Ort: {params.ort} (Umkreis {params.umkreis_km} km)
- Gehaltsvorstellung: {gehalt}
- Interessen/Branchen: {params.interessen or "keine Angabe"}

## Lebenslauf
{lebenslauf}"""


def _stellen_text(stelle: Stelle) -> str:
    gehalt = stelle.gehalt or "nicht angegeben"
    return f"""Bewerte diese Stelle:

Titel: {stelle.titel}
Firma: {stelle.firma}
Ort: {stelle.ort}
Gehalt laut Anzeige: {gehalt}

Anzeigentext:
{stelle.beschreibung}"""


def bewerte_stelle(client: anthropic.Anthropic, profil: str, stelle: Stelle) -> Ergebnis:
    try:
        antwort = client.messages.parse(
            model=config.CLAUDE_MODELL,
            max_tokens=4000,
            # Profil + Lebenslauf sind bei allen Stellen gleich -> wird zwischengespeichert (günstiger)
            system=[{"type": "text", "text": profil, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": _stellen_text(stelle)}],
            output_format=Bewertung,
            output_config={"effort": "low"},  # wenig "Nachdenken" = schneller und billiger
        )
    except anthropic.AuthenticationError:
        return Ergebnis(stelle, fehler="API-Schlüssel ungültig – bitte .env prüfen.")
    except anthropic.RateLimitError:
        return Ergebnis(stelle, fehler="Zu viele Anfragen (Rate-Limit). Später erneut versuchen.")
    except anthropic.APIStatusError as e:
        return Ergebnis(stelle, fehler=f"API-Fehler {e.status_code}: {e.message}")
    except anthropic.APIConnectionError:
        return Ergebnis(stelle, fehler="Keine Verbindung zur Claude API.")

    if antwort.stop_reason == "refusal" or antwort.parsed_output is None:
        return Ergebnis(stelle, fehler="Claude hat keine gültige Bewertung geliefert.")

    bewertung = antwort.parsed_output
    bewertung.punktzahl = max(1, min(100, bewertung.punktzahl))  # sicherheitshalber begrenzen
    return Ergebnis(stelle, bewertung=bewertung)


def bewerte_alle(
    lebenslauf: str,
    params: SuchParameter,
    stellen: List[Stelle],
    fortschritt: Optional[Callable[[int, int], None]] = None,
) -> List[Ergebnis]:
    """Bewertet alle Stellen parallel und gibt sie nach Punktzahl sortiert zurück."""
    client = anthropic.Anthropic()  # liest ANTHROPIC_API_KEY aus der Umgebung
    profil = _profil_text(lebenslauf, params)

    ergebnisse: List[Ergebnis] = []
    with ThreadPoolExecutor(max_workers=config.PARALLELE_BEWERTUNGEN) as pool:
        for i, ergebnis in enumerate(pool.map(lambda s: bewerte_stelle(client, profil, s), stellen), 1):
            ergebnisse.append(ergebnis)
            if fortschritt:
                fortschritt(i, len(stellen))

    # Bewertete Stellen nach Punktzahl absteigend, Fehler ans Ende
    return sorted(ergebnisse, key=lambda e: e.bewertung.punktzahl if e.bewertung else -1, reverse=True)
