import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURATION ---
st.set_page_config(page_title="Hausbau Dashboard", page_icon="🏡", layout="wide")
st.title("🏡 Sanierung Kuchl: Kosten-Dashboard")

# --- SIDEBAR: FINANZIERUNG ---
st.sidebar.header("Finanzierungseinstellungen")
kredithoehe = st.sidebar.number_input("Verfügbarer Kreditrahmen (€)", min_value=0, value=250000, step=5000)

# --- DATEI UPLOAD ---
st.info("Bitte lade die aktuelle 'Hausbau Übersicht Kostenschätzung.xlsx' hoch.")
uploaded_file = st.file_uploader("Excel-Datei wählen", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Einlesen des Blatts "Übersicht". 
        # Da die Datei nun direkt mit der Header-Zeile startet (oder nur minimalen Versatz hat),
        # passen wir skiprows an. Falls die Tabelle direkt oben startet, ist skiprows=0 oder 1 richtig.
        # Basierend auf deiner Datei nutzen wir skiprows=0, da die Header erkannt werden sollen.
        df = pd.read_excel(uploaded_file, sheet_name="Übersicht")
        
        # Falls die erste Zeile leer ist oder Titel enthält, bereinigen wir das:
        if "Gewerk/Posten" not in df.columns:
            df = pd.read_excel(uploaded_file, sheet_name="Übersicht", skiprows=1)

        # Relevante Spalten filtern & Namen säubern
        df.columns = [c.strip() for c in df.columns]
        cols_to_use = ['Gewerk/Posten', 'Kostenschätzung', 'Bezahlt', 'Abgeschlossen']
        df = df[cols_to_use].copy()
        
        # Datenbereinigung: Zahlen konvertieren
        df['Kostenschätzung'] = pd.to_numeric(df['Kostenschätzung'], errors='coerce').fillna(0)
        df['Bezahlt'] = pd.to_numeric(df['Bezahlt'], errors='coerce').fillna(0)
        
        # Abgeschlossen-Logik: 'X' oder 'x' bedeutet fertig
        df['Abgeschlossen'] = df['Abgeschlossen'].fillna('').astype(str).str.strip().str.upper() == 'X'
        
        # Leere Zeilen (ohne Gewerk-Namen) entfernen
        df = df.dropna(subset=['Gewerk/Posten'])

        # --- BERECHNUNGEN ---
        ausgegeben_gesamt = df['Bezahlt'].sum()
        
        # Offene Kosten berechnen
        # Wir nehmen das Maximum aus Schätzung und bereits bezahlt, falls es teurer wurde
        df['Erwartet'] = df[['Kostenschätzung', 'Bezahlt']].max(axis=1)
        
        # Offene Posten: Alles, was nicht mit 'X' markiert ist
        df_offen = df[~df['Abgeschlossen']].copy()
        df_offen['Noch zu zahlen'] = (df_offen['Erwartet'] - df_offen['Bezahlt']).clip(lower=0)
        restkosten_offen = df_offen['Noch zu zahlen'].sum()

        # Finanzierungs-Logik
        kredit_verfügbar = max(0, kredithoehe - ausgegeben_gesamt)
        eigenmittel_nötig = max(0, restkosten_offen - kredit_verfügbar)

        # --- ANZEIGE DASHBOARD ---
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Bisher investiert", f"{ausgegeben_gesamt:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
        with col2:
            st.metric("Noch zu zahlen (offen)", f"{restkosten_offen:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
        with col3:
            # Eigenmittel werden rot hervorgehoben, wenn sie nötig sind
            st.metric("Nötige Eigenmittel", f"{eigenmittel_nötig:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."),
                      delta=f"Kreditrest: {kredit_verfügbar:,.0f} €", delta_color="normal" if eigenmittel_nötig == 0 else "inverse")

        st.markdown("---")
        
        # Layout: Tabelle links, Grafik rechts
        c_left, c_right = st.columns([1.2, 1])
        
        with c_left:
            st.subheader("Offene Posten (Details)")
            # Nur Posten anzeigen, die noch nicht abgeschlossen sind und noch Geld kosten
            anzeige_df = df_offen[df_offen['Noch zu zahlen'] > 0][['Gewerk/Posten', 'Erwartet', 'Bezahlt', 'Noch zu zahlen']]
            anzeige_df = anzeige_df.sort_values(by='Noch zu zahlen', ascending=False)
            
            st.dataframe(anzeige_df.style.format({
                'Erwartet': '{:,.2f} €',
                'Bezahlt': '{:,.2f} €',
                'Noch zu zahlen': '{:,.2f} €'
            }), use_container_width=True, hide_index=True)
            
        with c_right:
            if not anzeige_df.empty:
                st.subheader("Kostenverteilung (Top 10)")
                fig = px.pie(anzeige_df.head(10), values='Noch zu zahlen', names='Gewerk/Posten', 
                             hole=0.4, color_discrete_sequence=px.colors.sequential.Tealgrn)
                fig.update_traces(textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Hoppla! Das Script konnte die Tabelle nicht lesen. Fehler: {e}")
        st.info("Hinweis: Achte darauf, dass die Spalten 'Gewerk/Posten', 'Kostenschätzung', 'Bezahlt' und 'Abgeschlossen' heißen.")
else:
    st.warning("Bitte lade die Excel-Datei hoch, um die Analyse zu starten.")
