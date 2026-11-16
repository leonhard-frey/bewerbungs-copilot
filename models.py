"""Datenmodelle: Welche Informationen die App herumreicht."""

from dataclasses import dataclass, field
from typing import List, Optional

from pydantic import BaseModel, Field

STELLENARTEN = ["Praktikum", "Werkstudent", "Vollzeitjob", "Ausbildung"]
ARBEITSZEITEN = ["Vollzeit", "Teilzeit"]


@dataclass
class SuchParameter:
    """Was du in der App eingibst."""

    stellenart: str
    arbeitszeit: str
    ort: str
    umkreis_km: int
    suchbegriff: str = ""  # optional, z. B. "Marketing" oder "Data Analyst"
    gehalt: Optional[int] = None  # Jahresgehalt in Euro, optional
    interessen: str = ""


@dataclass
class Stelle:
    """Eine Stellenanzeige – egal aus welcher Quelle sie kommt."""

    id: str
    titel: str
    firma: str
    ort: str
    beschreibung: str
    link: str
    quelle: str
    gehalt: Optional[str] = None  # nur gesetzt, wenn die Anzeige ein Gehalt nennt
    weitere_links: List[str] = field(default_factory=list)  # z. B. dieselbe Stelle aus der anderen Quelle


class Bewertung(BaseModel):
    """Die Antwort von Claude. Claude muss genau dieses JSON-Format liefern."""

    punktzahl: int = Field(description="Übereinstimmung von 1 (passt gar nicht) bis 100 (passt perfekt)")
    begruendung: str = Field(description="1–2 Sätze Begründung auf Deutsch")
    staerken: List[str] = Field(description="Was gut zur Stelle passt")
    luecken: List[str] = Field(description="Was fehlt oder nicht passt")


@dataclass
class Ergebnis:
    """Eine Stelle zusammen mit ihrer Bewertung (oder einer Fehlermeldung)."""

    stelle: Stelle
    bewertung: Optional[Bewertung] = None
    fehler: Optional[str] = None
