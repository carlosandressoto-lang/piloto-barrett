import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide")

# --- 2. CONEXIÓN CON GEMINI (PLAN GRATUITO - NOMBRE OFICIAL) ---
# REEMPLAZA CON TU API KEY
genai.configure(api_key="AIzaSyBBlmnKRd0DGx7CKCXOiOWdiZUe1ocCWwk")

# Usamos el nombre de modelo más estable para el plan gratuito
# Si este falla, el bloque de abajo tiene un respaldo automático
MODEL_NAME = 'gemini-1.5-flash'
model = genai.GenerativeModel(MODEL_NAME)

# --- 3. MARCO TEÓRICO INTEGRADO ---
MARCO_BARRETT = """
Modelo de Liderazgo de Barrett (7 Niveles):
- L7 (Visionario): Servicio, responsabilidad social, perspectiva a largo plazo.
- L6 (Mentor/Socio): Colaboración, desarrollo de liderazgo, alianzas.
- L5 (Auténtico): Integridad, confianza, pasión, honestidad.
- L4 (Facilitador): Evolución, empoderamiento, adaptabilidad, toma de riesgos.
- L3 (Desempeño): Resultados, excelencia, eficiencia, sistemas.
- L2 (Relaciones): Escuchar, respeto, resolución de conflictos.
- L1 (Crisis): Viabilidad, estabilidad financiera, manejo de recursos.
"""

# --- 4. CARGA Y LIMPIEZA DE DATOS (EXCEL ESPAÑOL) ---
try:
    # Leemos con punto y coma y decimales como comas
    df = pd.read_csv('Resultados_Gerentes.csv', sep=';', decimal=',')
    
    # Limpiar nombres de columnas y datos
    df.columns = df.columns.str.strip()
    df['Nombre_Lider'] = df['Nombre_Lider'].str.strip()
    
    # Asegurar que los niveles sean números (L1 a L7 para cada categoría)
    cols_check = [c for c in df.columns if 'L' in c and ('AUTO' in c or 'INDIV' in c or 'ORG' in c)]
    for col in cols_check:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
except Exception as e:
    st.error(f"Error cargando datos: {e}. Revisa que el archivo sea 'Resultados_Gerentes.csv'")
    st.stop()

# --- 5. INTERFAZ ---
st.title("🏛️ Plataforma de Liderazgo Barrett")
st.markdown("### Diagnóstico 360° - Análisis de Conciencia")

lider_sel = st.selectbox("Seleccione el líder:", df['Nombre_Lider'].unique())
d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

# --- 6. GRÁFICOS: TRIPLE RELOJ DE ARENA ---
st.subheader("Distribución de Energía por Niveles")
c1, c2, c3 = st.columns(3)

def dibujar_reloj(vals, titulo, color):
    # Nombres de niveles (Barrett pide L7 arriba)
    labels = ['L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 'L4 - Facilitador', 'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis']
    # Los datos vienen en orden L1, L2... L7. Los invertimos:
    v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
    
    fig = go.Figure(go.Bar(
        x=v_plot, 
        y=labels, 
        orientation='h', 
        marker_color=color,
        text=[f"{round(v,1)}%" for v in v_plot],
        textposition='inside'
    ))
    fig.update_layout(title=titulo, xaxis_range=[0,105], height=400, margin=dict(l=0, r=10, t=40, b=0))
    return fig

with c1:
    st.plotly_chart(dibujar_reloj([d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7], "Autovaloración", "#3498db"), use_container_width=True)
with c2:
    st.plotly_chart(dibujar_reloj([d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7], "Ponderado Individual", "#2ecc71"), use_container_width=True)
with c3:
    st.plotly_chart(dibujar_reloj([d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7], "Promedio Org.", "#95a5a6"), use_container_width=True)

# --- 7. RADAR ---
st.divider()
st.subheader("Radar de Alineación Estratégica")
fig_radar = go.Figure()
cats = ['L1','L2','L3','L4','L5','L6','L7']
v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]

fig_radar.add_trace(go.Scatterpolar(r=v_auto, theta=cats, fill='toself', name='Autovaloración'))
fig_radar.add_trace(go.Scatterpolar(r=v_ind, theta=cats, fill='toself', name='Ponderado Individual'))
fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
st.plotly_chart(fig_radar)

# --- 8. BOTÓN DE INFORME IA ---
st.divider()
if st.button("✨ Generar Informe Ejecutivo con IA"):
    # Prompt optimizado para evitar errores de contenido
    prompt = f"""
    Como experto en Barrett, analiza a {lider_sel}.
    Marco: {MARCO_BARRETT}
    Rúbrica: 0-65 Bajo, 66-75 Medio, 76-85 Alto, 86-100 Superior.
    Datos: {d.to_json()}
    Genera un análisis de brechas y estilo de liderazgo.
    """
    
    try:
        with st.spinner('Conectando con Google AI Studio...'):
            # Intentamos generar contenido
            response = model.generate_content(prompt)
            st.markdown("### Resultado del Análisis")
            st.write(response.text)
    except Exception as e:
        st.error(f"Error de la IA: {e}")
        st.info("Nota: Si recibes un error 404, asegúrate de haber aceptado los términos en Google AI Studio para el modelo Gemini 1.5 Flash.")
