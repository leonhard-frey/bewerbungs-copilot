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
