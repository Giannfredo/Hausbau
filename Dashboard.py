import streamlit as st
import pandas as pd
import plotly.express as px

# --- KONFIGURATION ---
st.set_page_config(page_title="Hausbau Dashboard", page_icon="🏡", layout="wide")
st.title("🏡 Hausbau & Sanierung: Kosten-Check")

# --- SIDEBAR: FINANZIERUNG ---
st.sidebar.header("Finanzierungseinstellungen")
kredithoehe = st.sidebar.number_input("Verfügbarer Kreditrahmen (€)", min_value=0, value=200000, step=5000)

# --- DATEI UPLOAD ---
st.info("Lade hier deine Excel-Datei aus der iCloud hoch, um die Auswertung zu starten.")
uploaded_file = st.file_uploader("Excel-Datei wählen", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Daten einlesen (Blatt "Übersicht", die ersten 3 Zeilen überspringen)
        df = pd.read_excel(uploaded_file, sheet_name="Übersicht", skiprows=3)
        
        # Relevante Spalten auswählen und bereinigen
        df = df[['Gewerk/Posten', 'Kostenschätzung', 'Bezahlt', 'Abgeschlossen']].copy()
        df['Kostenschätzung'] = pd.to_numeric(df['Kostenschätzung'], errors='coerce').fillna(0)
        df['Bezahlt'] = pd.to_numeric(df['Bezahlt'], errors='coerce').fillna(0)
        df['Abgeschlossen'] = df['Abgeschlossen'].fillna('').astype(str).str.strip().str.upper() == 'X'
        df = df.dropna(subset=['Gewerk/Posten'])

        # --- BERECHNUNGEN ---
        bisher_ausgegeben = df['Bezahlt'].sum()
        
        # Offene Posten (nicht mit 'X' markiert)
        df_offen = df[~df['Abgeschlossen']].copy()
        df_offen['Noch zu zahlen'] = (df_offen['Kostenschätzung'] - df_offen['Bezahlt']).clip(lower=0)
        kosten_offen_gesamt = df_offen['Noch zu zahlen'].sum()

        # Eigenmittel-Logik
        kredit_verfuegbar = max(0, kredithoehe - bisher_ausgegeben)
        eigenmittel_noetig = max(0, kosten_offen_gesamt - kredit_verfuegbar)

        # --- ANZEIGE ---
        col1, col2, col3 = st.columns(3)
        col1.metric("Bisher bezahlt", f"{bisher_ausgegeben:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
        col2.metric("Offene Restkosten", f"{kosten_offen_gesamt:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
        
        # Farbe der Eigenmittel-Metrik (Rot, wenn Eigenmittel fließen müssen)
        st.sidebar.markdown("---")
        st.sidebar.subheader("Ergebnis Finanzierung")
        st.sidebar.write(f"Rest-Kredit: {kredit_verfuegbar:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))
        
        col3.metric("Nötige Eigenmittel", f"{eigenmittel_noetig:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."),
                    delta=f"{eigenmittel_noetig:,.2f} €", delta_color="inverse")

        st.markdown("---")
        
        # Visualisierung
        col_table, col_chart = st.columns([1.2, 1])
        
        with col_table:
            st.subheader("Offene Gewerke")
            show_df = df_offen[df_offen['Noch zu zahlen'] > 0][['Gewerk/Posten', 'Kostenschätzung', 'Bezahlt', 'Noch zu zahlen']].sort_values(by='Noch zu zahlen', ascending=False)
            st.dataframe(show_df.style.format("{:,.2f} €"), use_container_width=True, hide_index=True)
            
        with col_chart:
            if not show_df.empty:
                fig = px.bar(
                    show_df.head(12), 
                    x='Noch zu zahlen', 
                    y='Gewerk/Posten', 
                    orientation='h',
                    title="Größte offene Posten",
                    labels={"Noch zu zahlen": "Restbetrag (€)"},
                    color_discrete_sequence=['#2E8B57'] # Ein schönes Grün
                )
                fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Fehler beim Verarbeiten der Datei: {e}. Prüfe bitte, ob das Tabellenblatt 'Übersicht' heißt.")
else:
    st.write("Warte auf Datei-Upload...")
