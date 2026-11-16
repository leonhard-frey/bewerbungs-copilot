"""Hilfsfunktion zum Vergleichen von Links."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def normalisiere_url(url: str) -> str:
    """Macht URLs vergleichbar: Host klein, ohne www., ohne / am Ende, ohne #… und utm_-Parameter."""
    teile = urlsplit(url.strip())
    host = teile.netloc.lower().removeprefix("www.")
    pfad = teile.path.rstrip("/")
    query = urlencode([(k, v) for k, v in parse_qsl(teile.query) if not k.lower().startswith("utm_")])
    return urlunsplit((teile.scheme.lower() or "https", host, pfad, query, ""))
