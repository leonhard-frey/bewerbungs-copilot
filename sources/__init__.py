"""Alle Job-Quellen.

Neue Quelle hinzufügen:
  1. Datei in sources/ mit einer Klasse anlegen, die von JobQuelle erbt
  2. Hier importieren und in aktive_quellen() eintragen – fertig.
"""

from typing import List

from sources.arbeitsagentur import ArbeitsagenturQuelle
from sources.base import JobQuelle
from sources.claude_websuche import ClaudeWebsucheQuelle


def aktive_quellen(web: bool) -> List[JobQuelle]:
    """Arbeitsagentur immer, Websuche nur wenn gewünscht (kostet etwas)."""
    quellen: List[JobQuelle] = [ArbeitsagenturQuelle()]
    if web:
        quellen.append(ClaudeWebsucheQuelle())
    return quellen
