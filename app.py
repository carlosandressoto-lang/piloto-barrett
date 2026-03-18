import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide")

# Estilo para que el selector y los títulos se vean impecables
st.markdown("""
<style>
    .main { background-color: #0e1117; color: white; }
    h1 { text-align: center; color: #3b82f6; font-family: 'Arial'; }
    .stSelectbox { margin-bottom: 2rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN IA (MODELO 2.5) ---
API_KEY = "AIzaSyB_llfm1vZ7fZkubkkbMBwup5WCXVw36yY"
try:
    genai.configure(api_key=API_KEY)
    # Usamos el alias que te dio éxito (ajusta si es 1.5-flash-8b pero se identifica como 2.5)
    model = genai.GenerativeModel('gemini-2.5-flash-8b') 
except Exception as e:
    st.error(f"IA no conectada: {e}")

# --- 3. DATOS ---
@st.cache_data
def load_data():
    df = pd.read_csv('Resultados_Gerentes.csv', sep=';', decimal=',')
    df.columns = df.columns.str.strip()
    df['Nombre_Lider'] = df['Nombre_Lider'].str.strip()
    for col in [c for c in df.columns if 'L' in c]:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

df = load_data()

# --- 4. SELECTOR (FUERA DE COLUMNAS PARA EVITAR ERRORES) ---
st.title("🏛️ Consultoría de Liderazgo Barrett - Confa")
lider_sel = st.selectbox("👤 Seleccione el Líder para análisis profundo:", sorted(df['Nombre_Lider'].unique()))
d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

# --- 5. FUNCIÓN RELOJ DE ARENA (SILUETA DE DIAMANTE) ---
def render_barrett_hourglass(vals, titulo, color):
    # Convertir a escala 1-4
    def scale(v):
        if v < 65: return 1
        if v < 75: return 2
        if v < 85: return 3
        return 4
    
    v4 = [scale(x) for x in vals]
    # Niveles L1 a L7
    levels = ['L1 Crisis', 'L2 Relac.', 'L3 Desemp.', 'L4 Facil.', 'L5 Autént.', 'L6 Mentor', 'L7 Vision.']
    
    # Para crear la forma de reloj de arena simétrica:
    # x_neg son los valores negativos y x_pos los positivos para centrar
    x_pos = v4
    x_neg = [-x for x in v4]
    
    fig = go.Figure()
    # Dibujamos la silueta del reloj
    fig.add_trace(go.Scatter(
        x=x_pos + x_neg[::-1], 
        y=levels + levels[::-1],
        fill='toself',
        fillcolor=color,
        line=dict(color='white', width=2),
        name=titulo,
        hoverinfo='none'
    ))
    
    # Añadimos los números de nivel de desarrollo en el centro
    for i, val in enumerate(v4):
        fig.add_annotation(x=0, y=levels[i], text=f"Nivel {val}", showarrow=False, font=dict(color="white", size=12))

    fig.update_layout(
        title=dict(text=titulo, x=0.5, font=dict(size=16, color='white')),
        xaxis=dict(showgrid=False, zeroline=True, showticklabels=False, range=[-4.5, 4.5]),
        yaxis=dict(showgrid=True, gridcolor='#334155'),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=500,
        showlegend=False
    )
    return fig

# --- 6. VISUALIZACIÓN ---
st.divider()
st.subheader("⏳ Relojes de Arena (Nivel de Desarrollo 1-4)")
c1, c2, c3 = st.columns(3)

v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]

with c1: st.plotly_chart(render_barrett_hourglass(v_auto, "Auto-Desarrollo", "rgba(59, 130, 246, 0.6)"), use_container_width=True)
with c2: st.plotly_chart(render_barrett_hourglass(v_ind, "Desarrollo Individual", "rgba(16, 185, 129, 0.6)"), use_container_width=True)
with c3: st.plotly_chart(render_barrett_hourglass(v_org, "Nivel Organizacional", "rgba(148, 163, 184, 0.6)"), use_container_width=True)

# --- 7. RADAR Y BARRAS (PARA DETALLE NUMÉRICO) ---
st.divider()
col_radar, col_bars = st.columns([1, 1])

with col_radar:
    st.subheader("🎯 Radar de Alineación")
    fig_radar = go.Figure()
    cats = ['L1','L2','L3','L4','L5','L6','L7']
    fig_radar.add_trace(go.Scatterpolar(r=v_auto, theta=cats, fill='toself', name='Auto'))
    fig_radar.add_trace(go.Scatterpolar(r=v_ind, theta=cats, fill='toself', name='Indiv'))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=400, template="plotly_dark")
    st.plotly_chart(fig_radar, use_container_width=True)

with col_bars:
    st.subheader("📊 Resultados por Nivel (%)")
    fig_bars = go.Figure()
    fig_bars.add_trace(go.Bar(name='Individual', y=cats, x=[v_ind[0],v_ind[1],v_ind[2],v_ind[3],v_ind[4],v_ind[5],v_ind[6]], orientation='h', marker_color='#10b981'))
    fig_bars.update_layout(barmode='group', height=400, template="plotly_dark", yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_bars, use_container_width=True)

# --- 8. INFORME IA CONTECTUALIZADO ---
st.divider()
if st.button("🚀 GENERAR INFORME CONSULTIVO"):
    PROMPT = f"""
    Eres un Consultor Senior experto en Richard Barrett. Analiza a {lider_sel}.
    DATOS: {d.to_json()}
    
    INSTRUCCIONES TÉCNICAS:
    1. ANALIZA LA FORMA DEL RELOJ DE ARENA: Si el desarrollo 1-4 está concentrado en L1-L3 (Interés Propio) o L5-L7 (Bien Común).
    2. RÚBRICA: 0-65 Bajo, 66-75 Medio, 76-85 Alto, 86-100 Superior.
    3. ESTRUCTURA: 
       - Perfil General (Resumen Ejecutivo).
       - Análisis de los 7 Niveles (Teoría Barrett).
       - Brechas Autopercepción vs Observado.
       - Alineación con Cultura Organizacional.
       - Estilo predominante y 3 metas de evolución.
    
    Tono: Profesional, ejecutivo, estratégico.
    """
    try:
        with st.spinner('Articulando marco teórico...'):
            response = model.generate_content(PROMPT)
            st.markdown(response.text)
    except Exception as e:
        st.error(f"Error IA: {e}")
