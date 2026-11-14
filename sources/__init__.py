"""Alle aktiven Job-Quellen.

Neue Quelle hinzufügen (z. B. Claude-Websuche):
  1. Datei sources/claude_websuche.py mit einer Klasse anlegen, die von JobQuelle erbt
  2. Hier importieren und in QUELLEN eintragen – fertig.
"""

from sources.arbeitsagentur import ArbeitsagenturQuelle

QUELLEN = [
    ArbeitsagenturQuelle(),
]
