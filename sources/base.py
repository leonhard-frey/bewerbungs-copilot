"""Gemeinsame Schnittstelle für alle Job-Quellen.

Jede Quelle (Arbeitsagentur, später z. B. Claude-Websuche) erbt von `JobQuelle`
und liefert eine Liste von `Stelle`-Objekten. So muss der Rest der App nicht wissen,
woher eine Stelle kommt.
"""

from abc import ABC, abstractmethod
from typing import List

from kosten import Verbrauch
from models import Stelle, SuchParameter


class JobQuelle(ABC):
    name: str = "Unbekannt"

    def __init__(self) -> None:
        self.hinweise: List[str] = []  # Meldungen für die App, z. B. "3 Treffer verworfen"

    @abstractmethod
    def suche(self, params: SuchParameter, max_treffer: int, verbrauch: Verbrauch) -> List[Stelle]:
        """Sucht Stellen passend zu den Parametern. Kosten werden in `verbrauch` mitgezählt."""
