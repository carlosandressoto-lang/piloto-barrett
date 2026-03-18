import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide")

# --- 2. CONEXIÓN CON GEMINI (PLAN GRATUITO) ---
# Reemplaza con tu API Key de Google AI Studio
genai.configure(api_key="AIzaSyBBlmnKRd0DGx7CKCXOiOWdiZUe1ocCWwk")
# Usamos el nombre base compatible con el plan gratuito
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 3. MARCO TEÓRICO INTEGRADO ---
MARCO_BARRETT = """
Modelo de Liderazgo de Barrett:
- Nivel 7: LÍDER VISIONARIO. Propósito de vivir, responsabilidad social[cite: 14, 15].
- Nivel 6: LÍDER MENTOR/SOCIO. Colaboración, desarrollo de otros, asociaciones[cite: 17, 18].
- Nivel 5: LÍDER AUTÉNTICO. Confianza, integridad, pasión, honestidad[cite: 22, 23].
- Nivel 4: FACILITADOR/INNOVADOR. Evolución de forma valiente, empoderamiento, toma de riesgos[cite: 25, 26].
- Nivel 3: GESTOR DE DESEMPEÑO. Logrando la excelencia, resultados, productividad[cite: 27, 29].
- Nivel 2: GESTOR DE RELACIONES. Escuchar, respetar, resolución de conflictos[cite: 32].
- Nivel 1: GESTOR DE CRISIS. Viabilidad, estabilidad financiera, consciencia de gastos[cite: 33, 34].
"""

# --- 4. CARGA Y LIMPIEZA DE DATOS ---
try:
    # Leemos con ';' y decimal ',' por el formato de Excel en español
    df = pd.read_csv('Resultados_Gerentes.csv', sep=';', decimal=',')
    
    # Limpieza de espacios en blanco en nombres y columnas
    df.columns = df.columns.str.strip()
    df['Nombre_Lider'] = df['Nombre_Lider'].str.strip()
    
    # Asegurar que los datos sean numéricos (por si acaso)
    cols_niveis = [c for c in df.columns if any(x in c for x in ['AUTO_', 'INDIV_', 'ORG_'])]
    for col in cols_niveis:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
except Exception as e:
    st.error(f"Error crítico al cargar 'Resultados_Gerentes.csv': {e}")
    st.stop()

# --- 5. INTERFAZ DE USUARIO ---
st.title("🏛️ Plataforma de Liderazgo Barrett")
st.markdown("### Informe de Conciencia y Potencial de Desarrollo")

# Selector de Líder
lider_nombre = st.selectbox("Seleccione el líder para visualizar el informe:", df['Nombre_Lider'].unique())
d = df[df['Nombre_Lider'] == lider_nombre].iloc[0]

# --- 6. GRÁFICOS: TRIPLE RELOJ DE ARENA ---
st.subheader("Distribución de Energía por Niveles de Conciencia")
c1, c2, c3 = st.columns(3)

def dibujar_reloj(valores, titulo, color):
    # Nombres de niveles en orden de Barrett (L7 arriba, L1 abajo) [cite: 13, 31]
    labels = ['L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 'L4 - Facilitador', 'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis']
    # Mapeo de datos: invertimos el orden de entrada (L1-L7) para que L7 sea el primero visualmente
    v_display = [valores[6], valores[5], valores[4], valores[3], valores[2], valores[1], valores[0]]
    
    fig = go.Figure(go.Bar(
        x=v_display, 
        y=labels, 
        orientation='h', 
        marker_color=color,
        text=[f"{round(v,1)}%" for v in v_display],
        textposition='inside'
    ))
    fig.update_layout(title=titulo, xaxis_range=[0,105], height=400, margin=dict(l=0, r=10, t=40, b=0))
    return fig

with c1:
    st.plotly_chart(dibujar_reloj([d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7], "Autovaloración", "#3498db"), use_container_width=True)
with c2:
    st.plotly_chart(dibujar_reloj([d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7], "Ponderado Individual", "#2ecc71"), use_container_width=True)
with c3:
    st.plotly_chart(dibujar_reloj([d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7], "Promedio Organización", "#95a5a6"), use_container_width=True)

# --- 7. RADAR DE ALINEACIÓN ---
st.divider()
st.subheader("Radar de Alineación Estratégica")
fig_radar = go.Figure()
cats = ['L1','L2','L3','L4','L5','L6','L7']
v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
v_indiv = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]

fig_radar.add_trace(go.Scatterpolar(r=v_auto, theta=cats, fill='toself', name='Autovaloración'))
fig_radar.add_trace(go.Scatterpolar(r=v_indiv, theta=cats, fill='toself', name='Ponderado Individual'))
fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=True)
st.plotly_chart(fig_radar)

# --- 8. GENERACIÓN DE INFORME IA ---
st.divider()
if st.button("✨ Generar Análisis Estratégico"):
    prompt = f"""
    {MARCO_BARRETT}
    
    INSTRUCCIONES:
    1. Analiza a {lider_nombre} como consultor experto.
    2. Rúbrica: 0-65 Bajo, 66-75 Medio, 76-85 Alto, 86-100 Superior.
    3. Compara Autovaloración (Cifras Auto) vs Ponderado Individual (Cifras Indiv).
    4. Compara Ponderado Individual vs Promedio Org (Cifras Org).
    5. Define el perfil basado en el nivel más fuerte.
    
    DATOS ACTUALES DEL LÍDER (JSON):
    {d.to_json()}
    """
    try:
        with st.spinner('La IA está procesando los niveles de conciencia...'):
            response = model.generate_content(prompt)
            st.markdown("## Informe Ejecutivo de Liderazgo")
            st.markdown(response.text)
    except Exception as e:
        st.error(f"Error al conectar con la IA: {e}")
