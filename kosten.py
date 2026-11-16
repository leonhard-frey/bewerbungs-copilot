"""Zählt Tokens und Websuchen eines Durchlaufs und schätzt die Kosten."""

import threading
from dataclasses import dataclass, field

import config


@dataclass
class Verbrauch:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
    web_suchen: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, usage) -> None:
        """Nimmt `antwort.usage` einer Claude-Antwort auf. Fehlende Felder zählen als 0."""
        server = getattr(usage, "server_tool_use", None)
        with self._lock:  # mehrere Bewertungen laufen gleichzeitig
            self.input_tokens += getattr(usage, "input_tokens", 0) or 0
            self.output_tokens += getattr(usage, "output_tokens", 0) or 0
            self.cache_write_tokens += getattr(usage, "cache_creation_input_tokens", 0) or 0
            self.cache_read_tokens += getattr(usage, "cache_read_input_tokens", 0) or 0
            self.web_suchen += getattr(server, "web_search_requests", 0) or 0

    def kosten_usd(self) -> float:
        p_in = config.PREIS_INPUT_PRO_MIO / 1_000_000
        p_out = config.PREIS_OUTPUT_PRO_MIO / 1_000_000
        return (
            self.input_tokens * p_in
            + self.cache_write_tokens * p_in * config.PREIS_CACHE_SCHREIBEN_FAKTOR
            + self.cache_read_tokens * p_in * config.PREIS_CACHE_LESEN_FAKTOR
            + self.output_tokens * p_out
            + self.web_suchen * config.PREIS_PRO_WEBSUCHE
        )
