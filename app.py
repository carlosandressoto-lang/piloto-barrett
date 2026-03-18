import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide")

# --- 2. CONEXIÓN IA (SOLUCIÓN 404) ---
# REEMPLAZA CON TU API KEY
API_KEY = "TU_API_KEY_AQUI"

try:
    genai.configure(api_key=API_KEY)
    # Nombre del modelo sin el prefijo 'models/' para evitar error 404 en Streamlit
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error(f"Error de configuración IA: {e}")

# --- 3. CARGA DE DATOS ---
try:
    df = pd.read_csv('Resultados_Gerentes.csv', sep=';', decimal=',')
    df.columns = df.columns.str.strip()
    df['Nombre_Lider'] = df['Nombre_Lider'].str.strip()
    
    # Limpieza de valores numéricos
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

# --- 5. VISUALIZACIÓN: RELOJES DE ARENA (BARRAS) ---
st.subheader("Distribución de Energía por Niveles de Conciencia")
c1, c2, c3 = st.columns(3)

def dibujar_barras(vals, titulo, color):
    # Definimos los niveles (L7 arriba, L1 abajo)
    labels = ['L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 'L4 - Facilitador', 'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis']
    # Invertimos el orden de los datos que vienen del CSV (L1 a L7) para que coincidan con la visual
    v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
    
    fig = go.Figure(go.Bar(
        x=v_plot, 
        y=labels, 
        orientation='h', 
        marker_color=color,
        text=[f"{round(v,1)}%" for v in v_plot],
        textposition='inside'
    ))
    fig.update_layout(
        title=titulo, 
        xaxis_range=[0, 105], 
        height=400, 
        margin=dict(l=0, r=10, t=40, b=20),
        yaxis=dict(autorange="reversed") # Asegura que L7 quede arriba
    )
    return fig

with c1:
    v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
    st.plotly_chart(dibujar_barras(v_auto, "Autovaloración", "#3498db"), use_container_width=True)
with c2:
    v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
    st.plotly_chart(dibujar_barras(v_ind, "Ponderado Individual", "#2ecc71"), use_container_width=True)
with c3:
    v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]
    st.plotly_chart(dibujar_barras(v_org, "Promedio Organizacional", "#95a5a6"), use_container_width=True)

# --- 6. RADAR DE ALINEACIÓN ---
st.divider()
st.subheader("Radar de Alineación Estratégica")
fig_radar = go.Figure()
categorias = ['L1','L2','L3','L4','L5','L6','L7']

fig_radar.add_trace(go.Scatterpolar(r=v_auto, theta=categorias, fill='toself', name='Autovaloración', line_color='#3498db'))
fig_radar.add_trace(go.Scatterpolar(r=v_ind, theta=categorias, fill='toself', name='Ponderado Individual', line_color='#2ecc71'))
fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=True, height=500)
st.plotly_chart(fig_radar, use_container_width=True)

# --- 7. BOTÓN DE INFORME IA ---
st.divider()
if st.button("✨ Generar Informe Ejecutivo con IA"):
    prompt = f"""
    Actúa como experto en el modelo de Barrett. Analiza los resultados de {lider_sel}.
    Datos: {d.to_json()}
    Genera un informe que incluya:
    1. Estilo predominante.
    2. Brechas entre Autovaloración e Individual.
    3. Recomendaciones de desarrollo.
    Responde en español, tono ejecutivo y profesional.
    """
    
    try:
        with st.spinner('Analizando con IA...'):
            # Llamada directa al modelo sin prefijos de versión
            response = model.generate_content(prompt)
            st.success("Análisis generado exitosamente")
            st.markdown("### Informe Ejecutivo")
            st.write(response.text)
    except Exception as e:
        st.error(f"Error de la IA: {e}")
        st.info("Nota: Si persiste el 404, asegúrate de que el archivo requirements.txt tenga 'google-generativeai>=0.7.2'")
