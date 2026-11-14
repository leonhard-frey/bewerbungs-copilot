"""Liest den Text aus einem Lebenslauf-PDF."""

from pypdf import PdfReader


def lies_pdf(datei) -> str:
    """Gibt den Text aller Seiten zurück. `datei` kann ein Pfad oder ein Upload-Objekt sein."""
    reader = PdfReader(datei)
    seiten = [seite.extract_text() or "" for seite in reader.pages]
    return "\n".join(seiten).strip()
