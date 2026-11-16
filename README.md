# 🎯 Job-Matcher

Lokale Web-App: Du lädst deinen Lebenslauf hoch, die App sucht Stellen über die
**offizielle Jobsuche-API der Bundesagentur für Arbeit**, und Claude bewertet jede Stelle
mit einer Punktzahl von 1–100.

## Einmalig einrichten

Im Terminal (die Zeilen nacheinander eingeben):

```bash
cd ~/Documents/bewerbungs-copilot
python3 -m venv .venv              # eigene "Werkzeugkiste" für dieses Projekt anlegen
source .venv/bin/activate          # Werkzeugkiste aktivieren (vorne steht dann "(.venv)")
pip install -r requirements.txt    # benötigte Pakete installieren
```

Dann die Datei `.env` öffnen (z. B. `open -e .env`) und den Platzhalter
`dein-schluessel-hier` durch deinen echten API-Schlüssel ersetzen.
Einen Schlüssel bekommst du unter https://console.anthropic.com.

> Die `.env` steht in der `.gitignore` und landet so nie in Git.

## App starten

```bash
cd ~/Documents/bewerbungs-copilot
source .venv/bin/activate
streamlit run app.py
```

Der Browser öffnet sich unter http://localhost:8501. Beenden mit `Strg + C` im Terminal.

## Websuche (optional)

Mit der Checkbox **„Auch im Web suchen (kostet etwas mehr)“** sucht Claude zusätzlich auf
Karriereseiten von Firmen und Startups sowie in Bewerbungsportalen (Personio, Greenhouse,
Ashby, Lever, Join). LinkedIn, Indeed, StepStone und Glassdoor sind gesperrt.

- Höchstens 5 Websuchen und 10 Web-Stellen pro Durchlauf (einstellbar in `config.py`).
- **Kein Erfinden:** Eine Web-Stelle wird nur übernommen, wenn ihr Link tatsächlich in den
  Suchergebnissen vorkam. Alles andere wird verworfen.
- **Jede Web-Stelle wird geprüft:** Claude öffnet den Link mit dem Web-Fetch-Tool
  (höchstens 3 Seiten pro Stelle, Inhalt auf ca. 4.000 Tokens pro Seite begrenzt):
  - Seite nicht erreichbar oder Anzeige gelöscht (z. B. 404/410) → Stelle wird verworfen.
  - Sammel- oder Übersichtsseite → Claude sucht dort den Link zur konkreten Anzeige und öffnet ihn.
    Gibt es keinen, wird die Stelle verworfen.
  - Anzeige offen → der **volle Anzeigentext** wird übernommen (wörtlich aus der Seite), dazu Titel,
    Firma, Ort und ggf. Gehalt laut Anzeige. Die Bewertung ist damit so genau wie bei der Arbeitsagentur.
  - Eine Stelle gilt nur als bestätigt, wenn die Anzeigen-Seite wirklich erfolgreich abgerufen wurde.
  - Die App zeigt, wie viele Web-Treffer geprüft, bestätigt und verworfen wurden (mit Grund).
- Doppelte Stellen (gleiche Firma + ähnlicher Titel) werden zusammengeführt.
- Grenzen: Web-Fetch speichert Seiten zwischen; selten kann eine gerade erst gelöschte Anzeige
  noch als offen erscheinen. Seiten, die ihren Inhalt nur per JavaScript laden, liefern keinen
  Text und werden verworfen.

## Kosten

Bewertet wird mit **Claude Haiku 5.5** (`claude-haiku-5-5`), dem günstigsten Modell.
Ein Durchlauf mit 25 Stellen kostet etwa 1–2 Cent, mit Websuche etwa 5–8 Cent
(Websuche: 0,01 $ pro Suche plus Tokens). Die Prüfung der Web-Treffer kostet etwa 0,1–0,2 Cent
pro Stelle: Web-Fetch selbst ist kostenlos, bezahlt werden nur die Tokens der abgerufenen Seiten.
Nach jedem Durchlauf zeigt die App unten, wie viele Suchen, Seitenabrufe und Tokens verbraucht
wurden und was das ungefähr gekostet hat.
Modell, Trefferzahl und Preise kannst du in `config.py` ändern.

## Aufbau

| Datei | Aufgabe |
|---|---|
| `app.py` | Oberfläche (Formular, Fortschritt, Ergebnisliste) |
| `config.py` | Einstellungen (Modell, Trefferzahl, …) |
| `models.py` | Datenformate (Suchparameter, Stelle, Bewertung) |
| `cv_reader.py` | Text aus dem PDF lesen |
| `matcher.py` | Bewertung durch Claude (JSON-Ausgabe) |
| `sources/` | Job-Quellen: `arbeitsagentur.py` und `claude_websuche.py` |
| `sources/web_pruefung.py` | Web-Treffer öffnen und prüfen (Web-Fetch) |
| `zusammenfuehren.py` | Doppelte Stellen zusammenführen |
| `kosten.py` | Tokens, Websuchen, Seitenabrufe und Kosten zählen |

**Neue Quelle hinzufügen** (z. B. eine weitere offizielle Job-API): Eine Klasse in `sources/` anlegen,
die von `JobQuelle` erbt und eine Liste von `Stelle`-Objekten zurückgibt, und sie in
`sources/__init__.py` in `aktive_quellen()` eintragen. Der Rest der App bleibt gleich.
