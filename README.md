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
- Doppelte Stellen (gleiche Firma + ähnlicher Titel) werden zusammengeführt.
- Grenzen: Web-Links führen manchmal nur zur Jobübersicht einer Firma oder zu einer
  Sammelseite, und Anzeigen können schon abgelaufen sein. Die Bewertung stützt sich bei
  Web-Stellen auf eine kurze Beschreibung und ist daher ungenauer als bei der Arbeitsagentur.

## Kosten

Bewertet wird mit **Claude Haiku 5.5** (`claude-haiku-5-5`), dem günstigsten Modell.
Ein Durchlauf mit 25 Stellen kostet etwa 1–2 Cent, mit Websuche etwa 5–8 Cent
(Websuche: 0,01 $ pro Suche plus Tokens). Nach jedem Durchlauf zeigt die App unten,
wie viele Suchen und Tokens verbraucht wurden und was das ungefähr gekostet hat.
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
| `zusammenfuehren.py` | Doppelte Stellen zusammenführen |
| `kosten.py` | Tokens, Websuchen und Kosten zählen |

**Neue Quelle hinzufügen** (z. B. eine weitere offizielle Job-API): Eine Klasse in `sources/` anlegen,
die von `JobQuelle` erbt und eine Liste von `Stelle`-Objekten zurückgibt, und sie in
`sources/__init__.py` in `aktive_quellen()` eintragen. Der Rest der App bleibt gleich.
