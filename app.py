import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide")

# Estilo para fondo blanco y texto legible (Estilo Jennifer García)
st.markdown("""
<style>
    .main { background-color: white !important; color: black !important; font-family: 'Arial'; }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown { color: black !important; }
    .stSelectbox label { color: black; font-weight: bold; }
    .stButton>button { width: 100%; background-color: #1E3A8A; color: white; height: 3em; border-radius: 8px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN IA ---
API_KEY = "AIzaSyB_llfm1vZ7fZkubkkbMBwup5WCXVw36yY"
try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Error de configuración IA: {e}")

# --- 3. CARGA DE DATOS ---
try:
    df = pd.read_csv('Resultados_Gerentes.csv', sep=';', decimal=',')
    df.columns = df.columns.str.strip()
    df['Nombre_Lider'] = df['Nombre_Lider'].astype(str).str.strip()
    
    cols_niveles = [c for c in df.columns if 'L' in c and any(x in c for x in ['AUTO', 'INDIV', 'ORG'])]
    for col in cols_niveles:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
except Exception as e:
    st.error(f"Error cargando el archivo: {e}")
    st.stop()

# --- 4. SELECCIÓN ---
st.title("🏛️ Dashboard de Liderazgo Barrett - Confa")
lider_sel = st.selectbox("Seleccione el líder para el análisis:", df['Nombre_Lider'].unique())
d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

# --- 5. BARRAS ORIGINALES (%) ---
st.divider()
st.subheader("Distribución de Energía por Niveles de Conciencia (%)")
c1, c2, c3 = st.columns(3)

def dibujar_barras(vals, titulo, color):
    labels = ['L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 'L4 - Facilitador', 'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis']
    v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
    fig = go.Figure(go.Bar(x=v_plot, y=labels, orientation='h', marker_color=color, text=[f"{round(v,1)}%" for v in v_plot], textposition='inside'))
    fig.update_layout(title=titulo, xaxis_range=[0, 105], height=400, margin=dict(l=0, r=10, t=40, b=20), yaxis=dict(autorange="reversed"))
    return fig

v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]

with c1: st.plotly_chart(dibujar_barras(v_auto, "Autovaloración", "#3498db"), use_container_width=True)
with c2: st.plotly_chart(dibujar_barras(v_ind, "Ponderado Individual", "#2ecc71"), use_container_width=True)
with c3: st.plotly_chart(dibujar_barras(v_org, "Promedio Organizacional", "#95a5a6"), use_container_width=True)

# --- 6. RELOJES DE ARENA PREMIUM (DIAMANTE/HOURGLASS) ---
st.divider()
st.subheader("⏳ Representación Visual del Reloj de Arena")

def dibujar_reloj_premium(vals, titulo):
    levels = ['L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 'L4 - Facilitador', 'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis']
    # Anchos para simular la forma del reloj
    anchos = [5, 4, 3, 2, 3, 4, 5] 
    colors_barrett = ["#6F42C1", "#6F42C1", "#6F42C1", "#28A745", "#FD7E14", "#FD7E14", "#FD7E14"]
    
    fig = go.Figure(go.Funnel(
        y=levels, x=anchos, textinfo="none",
        marker={"color": colors_barrett, "line": {"width": 1, "color": "white"}},
        connector={"line": {"color": "white", "width": 1}, "fillcolor": "rgba(200, 200, 200, 0.1)"}
    ))
    fig.update_layout(title=dict(text=titulo, x=0.5), height=450, margin=dict(l=100, r=20), yaxis=dict(autorange="reversed"))
    return fig

r1, r2, r3 = st.columns(3)
with r1: st.plotly_chart(dibujar_reloj_premium(v_auto, "Forma Auto"), use_container_width=True)
with r2: st.plotly_chart(dibujar_reloj_premium(v_ind, "Forma Individual"), use_container_width=True)
with r3: st.plotly_chart(dibujar_reloj_premium(v_org, "Forma Organizacional"), use_container_width=True)

# --- 7. RADAR E INFORME IA ---
st.divider()
col_radar, col_ia = st.columns([1.5, 1])

with col_radar:
    st.subheader("Radar de Alineación Estratégica")
    fig_radar = go.Figure()
    cats = ['L1','L2','L3','L4','L5','L6','L7']
    fig_radar.add_trace(go.Scatterpolar(r=v_auto, theta=cats, fill='toself', name='Autovaloración', line_color='#3498db'))
    fig_radar.add_trace(go.Scatterpolar(r=v_ind, theta=cats, fill='toself', name='Individual', line_color='#2ecc71'))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=450)
    st.plotly_chart(fig_radar, use_container_width=True)

with col_ia:
    if st.button("✨ GENERAR INFORME EJECUTIVO"):
        prompt = f"""
        Actúa como consultor senior experto en Barrett. Analiza a {lider_sel}.
        DATOS: {d.to_json()}
        
        TEORÍA: L1 Viabilidad, L2 Relaciones, L3 Desempeño, L4 Evolución, L5 Alineación, L6 Colaboración, L7 Servicio.
        RÚBRICA: 0-65 Bajo, 66-75 Medio, 76-85 Alto, 86-100 Superior.
        
        ESTRUCTURA:
        1. Resumen Ejecutivo.
        2. Análisis por Niveles (Basado en INDIVIDUAL).
        3. Brechas Auto vs Individual.
        4. Alineación Cultural (INDIV vs ORG).
        5. Plan de Acción: Estilo predominante y 3 metas.
        """
        try:
            with st.spinner('Analizando...'):
                response = model.generate_content(prompt)
                st.markdown(f"## Informe: {lider_sel}")
                st.write(response.text)
        except Exception as e:
            st.error(f"Error IA: {e}")
