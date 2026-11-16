"""Zentrale Einstellungen der App. Hier kannst du Dinge ändern, ohne im restlichen Code zu suchen."""

# Claude-Modell für die Bewertung: Haiku ist das günstigste und schnellste Modell.
CLAUDE_MODELL = "claude-haiku-5-5"

# Wie viele Stellen pro Suche geladen und bewertet werden.
MAX_TREFFER = 25

# Wie viele Bewertungen gleichzeitig an Claude geschickt werden.
PARALLELE_BEWERTUNGEN = 5

# Stellenbeschreibungen werden auf diese Länge gekürzt, damit die Kosten klein bleiben.
MAX_BESCHREIBUNG_ZEICHEN = 6000

# Öffentliche Jobsuche-API der Bundesagentur für Arbeit
BA_BASIS_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service"
BA_API_KEY = "jobboerse-jobsuche"  # öffentlicher Schlüssel laut offizieller Doku

# ---------- Websuche (Claude) ----------
WEB_MAX_SUCHEN = 5     # höchstens so viele Websuchen pro Durchlauf (je ca. 0,01 $)
WEB_MAX_TREFFER = 10   # höchstens so viele Stellen aus dem Web
# Prüfung der Web-Treffer mit Web-Fetch (jede Stelle wird geöffnet)
WEB_FETCH_MAX_PRO_STELLE = 3   # Seitenabrufe pro Stelle (Treffer + ggf. Link von einer Sammelseite)
WEB_FETCH_MAX_TOKENS = 4000    # Inhalt pro Seite wird auf ca. so viele Tokens gekürzt (Kosten)
WEB_GESPERRTE_DOMAINS = [
    "linkedin.com",
    "indeed.com",
    "de.indeed.com",
    "stepstone.de",
    "glassdoor.de",
    "glassdoor.com",
]

# ---------- Preise für die Kostenanzeige (US-Dollar, Stand Nov. 2026, ungefähr) ----------
PREIS_INPUT_PRO_MIO = 0.10        # Haiku 5.5, Eingabe-Tokens
PREIS_OUTPUT_PRO_MIO = 0.50       # Haiku 5.5, Ausgabe-Tokens
PREIS_CACHE_SCHREIBEN_FAKTOR = 1.25
PREIS_CACHE_LESEN_FAKTOR = 0.10
PREIS_PRO_WEBSUCHE = 0.01         # 10 $ pro 1.000 Suchen
