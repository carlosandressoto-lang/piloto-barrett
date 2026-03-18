import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide")

# --- 2. CONEXIÓN IA ---
API_KEY = "AIzaSyB_llfm1vZ7fZkubkkbMBwup5WCXVw36yY"

try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error(f"Error de configuración IA: {e}")

# --- 3. CARGA DE DATOS ---
try:
    df = pd.read_csv('Resultados_Gerentes.csv', sep=';', decimal=',')
    df.columns = df.columns.str.strip()
    df['Nombre_Lider'] = df['Nombre_Lider'].str.strip()
    
    cols_niveles = [c for c in df.columns if 'L' in c and any(x in c for x in ['AUTO', 'INDIV', 'ORG'])]
    for col in cols_niveles:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
except Exception as e:
    st.error(f"Error cargando el archivo: {e}")
    st.stop()

# --- 4. INTERFAZ Y SELECCIÓN ---
st.title("🏛️ Dashboard de Liderazgo Barrett - Confa")
lider_sel = st.selectbox("Seleccione el líder para el análisis:", df['Nombre_Lider'].unique())
d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

# --- 5. VISUALIZACIÓN: BARRAS ORIGINALES ---
st.subheader("Distribución de Energía por Niveles de Conciencia (%)")
c1, c2, c3 = st.columns(3)

def dibujar_barras(vals, titulo, color):
    labels = ['L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 'L4 - Facilitador', 'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis']
    v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
    fig = go.Figure(go.Bar(x=v_plot, y=labels, orientation='h', marker_color=color, text=[f"{round(v,1)}%" for v in v_plot], textposition='inside'))
    fig.update_layout(title=titulo, xaxis_range=[0, 105], height=350, margin=dict(l=0, r=10, t=40, b=20), yaxis=dict(autorange="reversed"))
    return fig

v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]

with c1: st.plotly_chart(dibujar_barras(v_auto, "Autovaloración", "#3498db"), use_container_width=True)
with c2: st.plotly_chart(dibujar_barras(v_ind, "Ponderado Individual", "#2ecc71"), use_container_width=True)
with c3: st.plotly_chart(dibujar_barras(v_org, "Promedio Organizacional", "#95a5a6"), use_container_width=True)

# --- 6. NUEVA VISUALIZACIÓN: RELOJES DE ARENA (DIAMANTE ESCALA 1-4) ---
st.divider()
st.subheader("⏳ Nivel de Desarrollo Barrett (Escala 1 a 4)")

def a_escala_4(v):
    if v < 65: return 1
    if v < 75: return 2
    if v < 85: return 3
    return 4

def dibujar_reloj_diamante(vals, titulo, color):
    v4 = [a_escala_4(x) for x in vals]
    labels = ['L1 Crisis', 'L2 Relac.', 'L3 Desemp.', 'L4 Facil.', 'L5 Autént.', 'L6 Mentor', 'L7 Vision.']
    # Crear simetría para forma de diamante
    fig = go.Figure(go.Scatter(x=v4 + [-x for x in v4[::-1]], y=labels + labels[::-1], fill='toself', fillcolor=color, line=dict(color='white', width=1)))
    for i, val in enumerate(v4):
        fig.add_annotation(x=0, y=labels[i], text=str(val), showarrow=False, font=dict(color="white"))
    fig.update_layout(title=dict(text=titulo, x=0.5), xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-5, 5]), height=400, margin=dict(l=20, r=20, t=40, b=20), template="plotly_dark")
    return fig

rd1, rd2, rd3 = st.columns(3)
with rd1: st.plotly_chart(dibujar_reloj_diamante(v_auto, "Desarrollo Auto", "rgba(52, 152, 219, 0.7)"), use_container_width=True)
with rd2: st.plotly_chart(dibujar_reloj_diamante(v_ind, "Desarrollo Individual", "rgba(46, 204, 113, 0.7)"), use_container_width=True)
with rd3: st.plotly_chart(dibujar_reloj_diamante(v_org, "Desarrollo Org.", "rgba(149, 165, 166, 0.7)"), use_container_width=True)

# --- 7. RADAR Y BOTÓN DE INFORME IA ---
st.divider()
st.subheader("Radar de Alineación Estratégica")
fig_radar = go.Figure()
categorias = ['L1','L2','L3','L4','L5','L6','L7']
fig_radar.add_trace(go.Scatterpolar(r=v_auto, theta=categorias, fill='toself', name='Autovaloración', line_color='#3498db'))
fig_radar.add_trace(go.Scatterpolar(r=v_ind, theta=categorias, fill='toself', name='Ponderado Individual', line_color='#2ecc71'))
fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=450)
st.plotly_chart(fig_radar, use_container_width=True)

if st.button("✨ Generar Informe Ejecutivo con IA"):
    prompt = f"""
    Actúa como un experto consultor senior en el modelo de los 7 niveles de conciencia de Richard Barrett. 
    Analiza los resultados del diagnóstico 360 del líder {lider_sel} para el comité ejecutivo de Confa.

    DATOS: {d.to_json()}

    TEORÍA DE REFERENCIA:
    L1 (Crisis/Viabilidad): Salud financiera, seguridad. | L2 (Relaciones): Armonía, respeto. | L3 (Desempeño): Eficiencia, sistemas.
    L4 (Evolución/Facilitador): Empoderamiento, cambio. | L5 (Alineación/Auténtico): Confianza, integridad.
    L6 (Colaboración/Mentor): Alianzas, desarrollo de otros. | L7 (Servicio/Visionario): Ética, legado.

    RÚBRICA DE EVALUACIÓN:
    0-65: Bajo | 65-75: Medio | 75-85: Alto | 85-100: Superior

    ESTRUCTURA DEL INFORME:
    1. DESCRIPCIÓN POR NIVELES: Analiza de L1 a L7 usando el Ponderado Individual bajo la teoría de Barrett.
    2. ANÁLISIS DE AUTOVALORACIÓN: Evalúa sesgos entre cómo se percibe el líder vs cómo lo ven.
    3. ANÁLISIS DE PONDERADO INDIVIDUAL: Competencia real observada según rúbrica.
    4. MATRIZ DE MADUREZ: Alineación entre el líder y la cultura organizacional.
    5. PERFIL DE LIDERAZGO: Define el estilo predominante y 3 acciones estratégicas para el equilibrio de los niveles.
    """
    try:
        with st.spinner('Procesando análisis de alto impacto...'):
            response = model.generate_content(prompt)
            st.success("Análisis completado")
            st.markdown(response.text)
    except Exception as e:
        st.error(f"Error de la IA: {e}")
