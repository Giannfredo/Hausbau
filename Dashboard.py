import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURATION ---
st.set_page_config(page_title="Hausbau Dashboard", page_icon="🏡", layout="wide")
st.title("🏡 Kosten- & Finanzierungscheck")

# --- SIDEBAR: FINANZIERUNG ---
st.sidebar.header("Finanzierung")
# Hier gibst du den gesamten Kreditbetrag ein, den du von der Bank hast
kredithoehe = st.sidebar.number_input("Gesamter Kreditrahmen (€)", min_value=0, value=250000, step=5000)

# --- DATEI UPLOAD ---
st.info("Lade die Excel-Datei hoch, um die Berechnung mit deinem Kreditrahmen zu starten.")
uploaded_file = st.file_uploader("Excel-Datei wählen", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Einlesen und Spalten säubern
        df = pd.read_excel(uploaded_file, sheet_name="Übersicht")
        if "Gewerk/Posten" not in df.columns:
            df = pd.read_excel(uploaded_file, sheet_name="Übersicht", skiprows=1)

        df.columns = [c.strip() for c in df.columns]
        df = df[['Gewerk/Posten', 'Kostenschätzung', 'Bezahlt', 'Abgeschlossen']].copy()
        
        # Daten-Typen korrigieren
        df['Kostenschätzung'] = pd.to_numeric(df['Kostenschätzung'], errors='coerce').fillna(0)
        df['Bezahlt'] = pd.to_numeric(df['Bezahlt'], errors='coerce').fillna(0)
        df['Abgeschlossen'] = df['Abgeschlossen'].fillna('').astype(str).str.strip().str.upper() == 'X'
        df = df.dropna(subset=['Gewerk/Posten'])

        # --- FINANZ-LOGIK ---
        bisher_ausgegeben = df['Bezahlt'].sum()
        
        # Berechnung der noch offenen Beträge
        df['Max_Kosten'] = df[['Kostenschätzung', 'Bezahlt']].max(axis=1)
        df_offen = df[~df['Abgeschlossen']].copy()
        df_offen['Restbetrag'] = (df_offen['Max_Kosten'] - df_offen['Bezahlt']).clip(lower=0)
        offene_gesamtkosten = df_offen['Restbetrag'].sum()

        # DIE KREDIT-RECHNUNG:
        # 1. Wie viel vom Kredit ist noch da?
        verfuegbarer_kredit = max(0, kredithoehe - bisher_ausgegeben)
        
        # 2. Reicht der restliche Kredit für die offenen Kosten?
        # Wenn die offenen Kosten höher sind als der Rest-Kredit, brauchen wir Eigenmittel.
        eigenmittel_noetig = max(0, offene_gesamtkosten - verfuegbarer_kredit)

        # --- DASHBOARD ANZEIGE ---
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Bisher ausgegeben", f"{bisher_ausgegeben:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
        
        with col2:
            # Zeigt an, wie viel Puffer noch im Kredit ist
            st.metric("Verfügbarer Kreditrest", f"{verfuegbarer_kredit:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."),
                      delta=f"von {kredithoehe:,.0f} € gesamt", delta_color="normal")
        
        with col3:
            # Eigenmittel-Bedarf
            status_farbe = "normal" if eigenmittel_noetig == 0 else "inverse"
            st.metric("Zusätzliche Eigenmittel nötig", f"{eigenmittel_noetig:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."),
                      delta="Finanzierungslücke" if eigenmittel_noetig > 0 else "Gedeckt durch Kredit", 
                      delta_color=status_farbe)

        st.markdown("---")
        
        # Visualisierung der größten "Brocken"
        c1, c2 = st.columns([1.2, 1])
        
        with c1:
            st.subheader("Offene Zahlungen nach Gewerk")
            anzeige_df = df_offen[df_offen['Restbetrag'] > 0][['Gewerk/Posten', 'Restbetrag']].sort_values(by='Restbetrag', ascending=False)
            st.dataframe(anzeige_df.style.format({'Restbetrag': '{:,.2f} €'}), use_container_width=True, hide_index=True)
            
        with c2:
            if not anzeige_df.empty:
                fig = px.bar(anzeige_df.head(10), x='Restbetrag', y='Gewerk/Posten', orientation='h',
                             title="Top 10 verbleibende Kosten",
                             color='Restbetrag', color_continuous_scale='Teals')
                fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Fehler: {e}")
else:
    st.info("Warte auf Excel-Upload...")
