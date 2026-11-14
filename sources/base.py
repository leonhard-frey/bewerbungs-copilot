"""Gemeinsame Schnittstelle für alle Job-Quellen.

Jede Quelle (Arbeitsagentur, später z. B. Claude-Websuche) erbt von `JobQuelle`
und liefert eine Liste von `Stelle`-Objekten. So muss der Rest der App nicht wissen,
woher eine Stelle kommt.
"""

from abc import ABC, abstractmethod
from typing import List

from models import Stelle, SuchParameter


class JobQuelle(ABC):
    name: str = "Unbekannt"

    @abstractmethod
    def suche(self, params: SuchParameter, max_treffer: int) -> List[Stelle]:
        """Sucht Stellen passend zu den Parametern."""
