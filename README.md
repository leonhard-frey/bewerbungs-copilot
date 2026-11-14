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

## Kosten

Bewertet wird mit **Claude Haiku 5.5** (`claude-haiku-5-5`), dem günstigsten Modell.
Ein Durchlauf mit 25 Stellen kostet nur wenige Cent. Modell und Trefferzahl
kannst du in `config.py` ändern.

## Aufbau

| Datei | Aufgabe |
|---|---|
| `app.py` | Oberfläche (Formular, Fortschritt, Ergebnisliste) |
| `config.py` | Einstellungen (Modell, Trefferzahl, …) |
| `models.py` | Datenformate (Suchparameter, Stelle, Bewertung) |
| `cv_reader.py` | Text aus dem PDF lesen |
| `matcher.py` | Bewertung durch Claude (JSON-Ausgabe) |
| `sources/` | Job-Quellen, aktuell nur `arbeitsagentur.py` |

**Neue Quelle hinzufügen** (z. B. Claude-Websuche): Eine Klasse in `sources/` anlegen,
die von `JobQuelle` erbt und eine Liste von `Stelle`-Objekten zurückgibt, und sie in
`sources/__init__.py` in `QUELLEN` eintragen. Der Rest der App bleibt gleich.
