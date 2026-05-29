import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURATION ---
st.set_page_config(page_title="Hausbau Dashboard", page_icon="🏡", layout="wide")
st.title("🏡 Sanierung Kuchl: Kostenübersicht")

# --- SIDEBAR: KREDITHÖHE ---
st.sidebar.header("Finanzierung")
kredithoehe = st.sidebar.number_input("Angenommene Kredithöhe (€)", min_value=0, value=250000, step=5000)

# --- DATEI UPLOAD ---
st.info("Bitte lade die aktuelle Excel-Datei hoch.")
uploaded_file = st.file_uploader("Excel-Datei wählen", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Einlesen der Excel
        df = pd.read_excel(uploaded_file, sheet_name="Übersicht")
        if "Gewerk/Posten" not in df.columns:
            df = pd.read_excel(uploaded_file, sheet_name="Übersicht", skiprows=1)

        # Spalten säubern
        df.columns = [c.strip() for c in df.columns]
        df = df[['Gewerk/Posten', 'Kostenschätzung', 'Bezahlt', 'Abgeschlossen']].copy()
        
        # Datentypen korrigieren
        df['Kostenschätzung'] = pd.to_numeric(df['Kostenschätzung'], errors='coerce').fillna(0)
        df['Bezahlt'] = pd.to_numeric(df['Bezahlt'], errors='coerce').fillna(0)
        df['Abgeschlossen'] = df['Abgeschlossen'].fillna('').astype(str).str.strip().str.upper() == 'X'
        df = df.dropna(subset=['Gewerk/Posten'])

        # --- BERECHNUNGEN ---
        # 1. Bislang bezahlte Kosten
        bisher_bezahlt = df['Bezahlt'].sum()
        
        # 2. Noch offene Kosten berechnen
        # Wir nehmen das Maximum aus Schätzung und bereits bezahlt (falls teurer geworden)
        df['Max_Kosten'] = df[['Kostenschätzung', 'Bezahlt']].max(axis=1)
        df_offen = df[~df['Abgeschlossen']].copy()
        df_offen['Noch zu zahlen'] = (df_offen['Max_Kosten'] - df_offen['Bezahlt']).clip(lower=0)
        offener_gesamtbetrag = df_offen['Noch zu zahlen'].sum()

        # 3. Noch offene Eigenmittel (Offene Kosten - Kredithöhe)
        eigenmittel_offen = max(0, offener_gesamtbetrag - kredithoehe)

        # --- ANZEIGE METRIKEN ---
        col1, col2, col3 = st.columns(3)
        
        col1.metric("Bislang bezahlt", f"{bisher_bezahlt:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
        col2.metric("Offener Gesamtbetrag", f"{offener_gesamtbetrag:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
        col3.metric("Noch offene Eigenmittel", f"{eigenmittel_offen:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."),
                    help="Berechnung: Offener Gesamtbetrag minus eingegebene Kredithöhe")

        st.markdown("---")
        
        # --- GRAFIK & TABELLE (RESTORED VERSION) ---
        c_table, c_chart = st.columns([1.2, 1])
        
        with c_table:
            st.subheader("Details: Offene Posten")
            # Tabelle der Gewerke, die noch nicht abgeschlossen sind
            anzeige_df = df_offen[df_offen['Noch zu zahlen'] > 0][['Gewerk/Posten', 'Noch zu zahlen']]
            anzeige_df = anzeige_df.sort_values(by='Noch zu zahlen', ascending=False)
            
            st.dataframe(anzeige_df.style.format({'Noch zu zahlen': '{:,.2f} €'}), 
                         use_container_width=True, hide_index=True)
            
        with c_chart:
            if not anzeige_df.empty:
                st.subheader("Top 10 verbleibende Kosten")
                fig = px.bar(
                    anzeige_df.head(10), 
                    x='Noch zu zahlen', 
                    y='Gewerk/Posten', 
                    orientation='h',
                    labels={"Noch zu zahlen": "Restbetrag in €", "Gewerk/Posten": ""},
                    color='Noch zu zahlen',
                    color_continuous_scale='Greens' # Angenehmes Grün-Design
                )
                fig.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Fehler beim Verarbeiten: {e}")
else:
    st.info("Bitte lade deine Excel-Datei hoch, um das Dashboard zu aktualisieren.")
