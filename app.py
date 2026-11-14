"""Job-Matcher – Streamlit-Oberfläche. Start: streamlit run app.py"""

import os

import requests
import streamlit as st
from dotenv import load_dotenv

import config
from cv_reader import lies_pdf
from matcher import bewerte_alle
from models import ARBEITSZEITEN, STELLENARTEN, SuchParameter
from sources import QUELLEN

load_dotenv()  # lädt ANTHROPIC_API_KEY aus der .env-Datei

st.set_page_config(page_title="Job-Matcher", page_icon="🎯", layout="wide")
st.title("🎯 Job-Matcher")
st.caption("Findet Stellen über die Jobsuche der Bundesagentur für Arbeit und lässt Claude sie mit deinem Lebenslauf abgleichen.")

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
    interessen = st.text_area("Interessen / Branchen", placeholder="z. B. Nachhaltigkeit, Software, Medien")
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

# ---------- 2. Stellen suchen ----------
stellen = []
with st.spinner("Suche Stellen und lade Anzeigentexte …"):
    for quelle in QUELLEN:
        try:
            stellen += quelle.suche(params, config.MAX_TREFFER)
        except requests.RequestException as e:
            st.warning(f"Suche bei {quelle.name} fehlgeschlagen: {e}")

if not stellen:
    st.warning("Keine Stellen gefunden. Versuche einen größeren Umkreis oder einen anderen Suchbegriff.")
    st.stop()

# ---------- 3. Bewerten ----------
balken = st.progress(0.0, text=f"Claude bewertet {len(stellen)} Stellen …")
ergebnisse = bewerte_alle(
    lebenslauf,
    params,
    stellen,
    fortschritt=lambda i, n: balken.progress(i / n, text=f"Bewertet: {i} von {n}"),
)
balken.empty()

# ---------- 4. Anzeige ----------
st.subheader(f"{len(ergebnisse)} Stellen, sortiert nach Übereinstimmung")

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

        rechts.markdown(f"**{s.titel}**  \n{s.firma} · {s.ort}" + (f" · 💶 {s.gehalt}" if s.gehalt else ""))
        if e.bewertung:
            rechts.write(e.bewertung.begruendung)
            with rechts.expander("Stärken & Lücken"):
                st.markdown("**Stärken**\n" + "\n".join(f"- {x}" for x in e.bewertung.staerken))
                st.markdown("**Lücken**\n" + "\n".join(f"- {x}" for x in e.bewertung.luecken))
        else:
            rechts.error(e.fehler)
        rechts.markdown(f"[Zur Anzeige ↗]({s.link}) · Quelle: {s.quelle}")
