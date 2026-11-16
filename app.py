"""Job-Matcher – Streamlit-Oberfläche. Start: streamlit run app.py"""

import os
from urllib.parse import urlsplit

import requests
import streamlit as st
from dotenv import load_dotenv

import config
from cv_reader import lies_pdf
from kosten import Verbrauch
from matcher import bewerte_alle
from models import ARBEITSZEITEN, STELLENARTEN, SuchParameter
from sources import aktive_quellen
from zusammenfuehren import fuehre_zusammen

load_dotenv()  # lädt ANTHROPIC_API_KEY aus der .env-Datei

QUELLEN_LABEL = {
    "Arbeitsagentur": ":blue-background[🏛️ Arbeitsagentur]",
    "Websuche": ":violet-background[🌐 Websuche]",
}

st.set_page_config(page_title="Job-Matcher", page_icon="🎯", layout="wide")
st.title("🎯 Job-Matcher")
st.caption("Findet Stellen über die Jobsuche der Bundesagentur für Arbeit (und optional im Web) und lässt Claude sie mit deinem Lebenslauf abgleichen.")

api_key = os.getenv("ANTHROPIC_API_KEY", "")
if not api_key or api_key == "dein-schluessel-hier":
    st.error("Kein API-Schlüssel gefunden. Trage deinen Schlüssel in die Datei `.env` ein (ANTHROPIC_API_KEY=...) und starte die App neu.")
    st.stop()

# ---------- Eingabe ----------
with st.sidebar.form("eingabe"):
    st.header("Deine Angaben")
    pdf = st.file_uploader("Lebenslauf (PDF)", type="pdf")
    stellenart = st.selectbox("Art der Stelle", STELLENARTEN)
    arbeitszeit = st.radio("Arbeitszeit", ARBEITSZEITEN, horizontal=True)
    ort = st.text_input("Ort", placeholder="z. B. Berlin oder 80331")
    umkreis = st.slider("Umkreis (km)", 0, 200, 25, step=5)
    suchbegriff = st.text_input("Suchbegriff (optional)", placeholder="z. B. Marketing, Data Analyst")
    gehalt = st.number_input("Gehaltsvorstellung €/Jahr (optional, 0 = keine)", min_value=0, step=1000)
    interessen = st.text_area("Interessen / Branchen", placeholder="z. B. Nachhaltigkeit, Software, Startups")
    web = st.checkbox(
        "Auch im Web suchen (kostet etwas mehr)",
        value=False,
        help=f"Claude durchsucht Karriereseiten und Bewerbungsportale (max. {config.WEB_MAX_SUCHEN} Suchen, ca. 0,01 $ pro Suche plus Tokens).",
    )
    los = st.form_submit_button("Passende Stellen finden", type="primary")

if not los:
    st.info("Fülle links das Formular aus und klicke auf **Passende Stellen finden**.")
    st.stop()

if pdf is None or not ort.strip():
    st.warning("Bitte lade einen Lebenslauf hoch und gib einen Ort ein.")
    st.stop()

# ---------- 1. Lebenslauf lesen ----------
lebenslauf = lies_pdf(pdf)
if len(lebenslauf) < 50:
    st.error("Aus dem PDF konnte kaum Text gelesen werden. Ist es vielleicht ein eingescanntes Bild? Bitte ein PDF mit echtem Text verwenden.")
    st.stop()

params = SuchParameter(
    stellenart=stellenart,
    arbeitszeit=arbeitszeit,
    ort=ort.strip(),
    umkreis_km=umkreis,
    suchbegriff=suchbegriff,
    gehalt=int(gehalt) or None,
    interessen=interessen,
)
verbrauch = Verbrauch()  # zählt Tokens und Websuchen dieses Durchlaufs

# ---------- 2. Stellen suchen ----------
stellen = []
for quelle in aktive_quellen(web):
    with st.spinner(f"Suche bei: {quelle.name} …"):
        try:
            stellen += quelle.suche(params, config.MAX_TREFFER, verbrauch)
        except requests.RequestException as e:
            st.warning(f"Suche bei {quelle.name} fehlgeschlagen: {e}")
    for hinweis in quelle.hinweise:
        st.info(hinweis)
    bericht = getattr(quelle, "pruefbericht", None)  # nur die Websuche prüft ihre Treffer
    if bericht and bericht.geprueft:
        titel = (
            f"🔎 Web-Treffer geprüft: {bericht.geprueft} · ✅ bestätigt: {bericht.bestaetigt}"
            f" · ❌ verworfen: {len(bericht.verworfen)}"
        )
        with st.expander(titel):
            if bericht.direktlink_gefunden:
                st.markdown(f"Bei {bericht.direktlink_gefunden} Stelle(n) wurde über eine Sammelseite der direkte Link zur Anzeige gefunden.")
            for stelle_text, grund in bericht.verworfen:
                st.markdown(f"- **{stelle_text}**: {grund}")
            st.caption(f"Kosten der Prüfung: ca. {bericht.verbrauch.kosten_usd():.3f} $ ({bericht.verbrauch.web_abrufe} Seitenabrufe)".replace(".", ","))

anzahl_vorher = len(stellen)
stellen = fuehre_zusammen(stellen)
if anzahl_vorher > len(stellen):
    st.info(f"{anzahl_vorher - len(stellen)} doppelte Stelle(n) zusammengeführt.")

if not stellen:
    st.warning("Keine Stellen gefunden. Versuche einen größeren Umkreis oder einen anderen Suchbegriff.")
    st.stop()

# ---------- 3. Bewerten ----------
balken = st.progress(0.0, text=f"Claude bewertet {len(stellen)} Stellen …")
ergebnisse = bewerte_alle(
    lebenslauf,
    params,
    stellen,
    verbrauch,
    fortschritt=lambda i, n: balken.progress(i / n, text=f"Bewertet: {i} von {n}"),
)
balken.empty()

# ---------- 4. Anzeige ----------
st.subheader(f"{len(ergebnisse)} Stellen, sortiert nach Übereinstimmung")


def link_text(url: str, standard: str) -> str:
    """Kennzeichnet Links, die nur zur Jobübersicht einer Firma führen."""
    return f"{standard} (Jobübersicht der Firma)" if urlsplit(url).path in ("", "/") else standard


for e in ergebnisse:
    s = e.stelle
    with st.container(border=True):
        links, rechts = st.columns([1, 6])
        if e.bewertung:
            p = e.bewertung.punktzahl
            farbe = "green" if p >= 70 else "orange" if p >= 40 else "red"
            links.markdown(f"### :{farbe}[{p}]")
        else:
            links.markdown("### –")

        quellen = " ".join(QUELLEN_LABEL.get(q, q) for q in s.quelle.split(" + "))
        rechts.markdown(f"**{s.titel}** {quellen}  \n{s.firma} · {s.ort}" + (f" · 💶 {s.gehalt}" if s.gehalt else ""))
        if e.bewertung:
            rechts.write(e.bewertung.begruendung)
            with rechts.expander("Stärken & Lücken"):
                st.markdown("**Stärken**\n" + "\n".join(f"- {x}" for x in e.bewertung.staerken))
                st.markdown("**Lücken**\n" + "\n".join(f"- {x}" for x in e.bewertung.luecken))
        else:
            rechts.error(e.fehler)
        links_md = [f"[{link_text(s.link, 'Zur Anzeige ↗')}]({s.link})"]
        links_md += [f"[{link_text(l, 'Weitere Anzeige ↗')}]({l})" for l in s.weitere_links]
        rechts.markdown(" · ".join(links_md))

# ---------- 5. Verbrauch ----------
st.divider()
st.subheader("Verbrauch dieses Durchlaufs")
k1, k5, k2, k3, k4 = st.columns(5)
k1.metric("Websuchen", verbrauch.web_suchen)
k5.metric("Seitenabrufe", verbrauch.web_abrufe, help="Web-Fetch: kostet nichts extra, nur die Tokens des Seiteninhalts (in den Tokens enthalten).")
k2.metric("Eingabe-Tokens", f"{verbrauch.input_tokens + verbrauch.cache_write_tokens + verbrauch.cache_read_tokens:,}".replace(",", "."))
k3.metric("Ausgabe-Tokens", f"{verbrauch.output_tokens:,}".replace(",", "."))
k4.metric("Kosten (ca.)", f"{verbrauch.kosten_usd():.3f} $".replace(".", ","))
st.caption(
    f"Davon aus dem Zwischenspeicher gelesen: {verbrauch.cache_read_tokens:,} Tokens. ".replace(",", ".")
    + "Kosten sind eine Schätzung nach Listenpreis; die genaue Abrechnung steht in der Claude Console."
)
