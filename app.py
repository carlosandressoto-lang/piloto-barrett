import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide", page_icon="🏛️")

# Estilo CSS Corregido
st.markdown("""
<style>
    .reportview-container .main .block-container{ padding-top: 1rem; }
    h1 { color: #1E3A8A; text-align: center; }
    .stButton>button { width: 100%; background-color: #1E3A8A; color: white; height: 3em; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN IA (MODELO FLASH-8B) ---
API_KEY = "AIzaSyB_llfm1vZ7fZkubkkbMBwup5WCXVw36yY" 
try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-8b')
except Exception as e:
    st.error(f"Error de configuración IA: {e}")

# --- 3. CARGA DE DATOS ---
try:
    df = pd.read_csv('Resultados_Gerentes.csv', sep=';', decimal=',')
    df.columns = df.columns.str.strip()
    df['Nombre_Lider'] = df['Nombre_Lider'].str.strip()
    
    # Asegurar que los niveles sean numéricos
    cols_niveles = [c for c in df.columns if 'L' in c]
    for col in cols_niveles:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
except Exception as e:
    st.error(f"Error crítico en datos: {e}")
    st.stop()

# --- 4. INTERFAZ ---
st.title("🏛️ Plataforma de Liderazgo Barrett - Confa")
lider_sel = st.selectbox("👤 Seleccione el líder para el análisis:", df['Nombre_Lider'].unique())
d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

# --- 5. RADAR DE ALINEACIÓN ---
st.subheader("🎯 Radar de Alineación Estratégica")
fig_radar = go.Figure()
cats = ['L1 Crisis','L2 Relac.','L3 Desemp.','L4 Facil.','L5 Autént.','L6 Mentor','L7 Vision.']
v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]

fig_radar.add_trace(go.Scatterpolar(r=v_auto, theta=cats, fill='toself', name='Autovaloración', line_color='#3498db'))
fig_radar.add_trace(go.Scatterpolar(r=v_ind, theta=cats, fill='toself', name='Ponderado Individual', line_color='#2ecc71'))
fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=True, height=450)
st.plotly_chart(fig_radar, use_container_width=True)

# --- 6. LOS 3 RELOJES DE ARENA (BARRAS HORIZONTALES) ---
st.divider()
st.subheader("⏳ Distribución de Energía (Relojes de Arena)")
c1, c2, c3 = st.columns(3)

def dibujar_reloj(vals, titulo, color):
    # Definimos etiquetas: L7 arriba -> L1 abajo
    labels = ['L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 'L4 - Facilitador', 'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis']
    # Invertimos los valores para que el primero del gráfico (arriba) sea L7
    v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
    
    # Aplicamos rúbrica a los textos internos
    textos = []
    for v in v_plot:
        if v >= 85: r = "Superior"
        elif v >= 75: r = "Alto"
        elif v >= 65: r = "Medio"
        else: r = "Bajo"
        textos.append(f"{round(v,1)}% - {r}")

    fig = go.Figure(go.Bar(
        x=v_plot, 
        y=labels, 
        orientation='h', 
        marker_color=color,
        text=textos,
        textposition='inside'
    ))
    fig.update_layout(
        title=titulo, 
        xaxis_range=[0, 110], 
        height=450, 
        margin=dict(l=0, r=10, t=40, b=20),
        yaxis=dict(autorange="reversed") # Refuerza que L7 esté en el tope
    )
    return fig

with c1:
    st.plotly_chart(dibujar_reloj(v_auto, "Cómo se ve (AUTO)", "#3498db"), use_container_width=True)
with c2:
    st.plotly_chart(dibujar_reloj(v_ind, "Cómo lo ven (INDIV)", "#2ecc71"), use_container_width=True)
with c3:
    v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]
    st.plotly_chart(dibujar_reloj(v_org, "Organizacional (ORG)", "#95a5a6"), use_container_width=True)

# --- 7. BOTÓN E INFORME IA (PROMPT REFORZADO) ---
st.divider()
if st.button("✨ GENERAR INFORME ESTRATÉGICO"):
    
    PROMPT = f"""
    Actúa como Experto Consultor Barrett. Analiza los resultados 360 de {lider_sel}.
    DATOS REALES: {d.to_json()}
    
    REGLAS DE ORO:
    1. Rúbrica: 0-65 Bajo, 65-75 Medio, 75-85 Alto, 85-100 Superior.
    2. Usa el marco teórico de los 7 niveles de Richard Barrett.
    3. Tono ejecutivo para Comité y Gestión Humana.

    ESTRUCTURA OBLIGATORIA:
    1. DESCRIPCIÓN POR NIVELES: Analiza de L1 a L7 usando los datos INDIVIDUALES. Indica puntaje y categoría de rúbrica.
    2. ANÁLISIS DE AUTOVALORACIÓN: Compara cómo se percibe vs los datos reales.
    3. ANÁLISIS DE PONDERADO INDIVIDUAL: Competencia observada y valor estratégico.
    4. MATRIZ DE MADUREZ: Alineación entre el Ponderado Individual y el Promedio Organizacional.
    5. PERFIL DE LIDERAZGO: Define 1 estilo predominante y da 3 recomendaciones tácticas de equilibrio.
    """
    
    try:
        with st.spinner('Consultando al experto en Barrett...'):
            response = model.generate_content(PROMPT)
            st.markdown(f"### 📋 Informe de Liderazgo: {lider_sel}")
            st.write(response.text)
    except Exception as e:
        st.error(f"Error en IA: {e}")
