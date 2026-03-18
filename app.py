import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="LDR Barrett - Informe Ejecutivo", layout="wide")

# --- CONEXIÓN CON GEMINI ---
# He cambiado el nombre del modelo a 'gemini-1.5-flash-latest' que es más estable
genai.configure(api_key="AIzaSyBBlmnKRd0DGx7CKCXOiOWdiZUe1ocCWwk")
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# --- MARCO TEÓRICO ---
MARCO_BARRETT = """
Modelo de Liderazgo de Barrett:
- Nivel 7: LÍDER VISIONARIO. Propósito, responsabilidad social.
- Nivel 6: LÍDER MENTOR/SOCIO. Colaboración, desarrollo de otros.
- Nivel 5: LÍDER AUTÉNTICO. Confianza, integridad, honestidad.
- Nivel 4: FACILITADOR/INNOVADOR. Evolución, empoderamiento, toma de riesgos.
- Nivel 3: GESTOR DE DESEMPEÑO. Resultados, excelencia, eficiencia.
- Nivel 2: GESTOR DE RELACIONES. Escuchar, respeto, resolución de conflictos.
- Nivel 1: GESTOR DE CRISIS. Viabilidad, estabilidad financiera.
"""

# --- CARGA Y LIMPIEZA DE DATOS ---
try:
    # Leemos con separador ';' porque es Excel en español
    df = pd.read_csv('Resultados_Gerentes.csv', sep=';')
    
    # LIMPIEZA CRÍTICA: Convertimos "94,67" a número real 94.67
    cols_numericas = [c for c in df.columns if any(x in c for x in ['AUTO_', 'INDIV_', 'ORG_'])]
    for col in cols_numericas:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
        
    df = df.fillna(0) # Si hay huecos, ponemos 0 para que no falle el gráfico
except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    st.stop()

# --- INTERFAZ ---
st.title("🏛️ Plataforma de Liderazgo Barrett")
lider_nombre = st.selectbox("Seleccione el líder:", df['Nombre_Lider'].unique())
d = df[df['Nombre_Lider'] == lider_nombre].iloc[0]

# --- LOS 3 RELOJES DE ARENA ---
st.subheader("Distribución de Energía (Reloj de Arena)")
c1, c2, c3 = st.columns(3)

def dibujar_reloj(valores, titulo, color):
    niveles = ['L7', 'L6', 'L5', 'L4', 'L3', 'L2', 'L1']
    # Los valores se invierten para que L7 esté en la cima
    v_plot = [valores[6], valores[5], valores[4], valores[3], valores[2], valores[1], valores[0]]
    
    fig = go.Figure(go.Bar(
        x=v_plot, 
        y=niveles, 
        orientation='h', 
        marker_color=color,
        text=[f"{round(v,1)}%" for v in v_plot],
        textposition='auto'
    ))
    fig.update_layout(title=titulo, xaxis_range=[0,110], height=400)
    return fig

with c1:
    st.plotly_chart(dibujar_reloj([d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7], "Autovaloración", "#3498db"), use_container_width=True)
with c2:
    st.plotly_chart(dibujar_reloj([d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7], "Ponderado Individual", "#2ecc71"), use_container_width=True)
with c3:
    st.plotly_chart(dibujar_reloj([d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7], "Promedio Org.", "#95a5a6"), use_container_width=True)

# --- RADAR ---
st.divider()
st.subheader("Radar de Alineación Estratégica")
fig_radar = go.Figure()
cats = ['L1','L2','L3','L4','L5','L6','L7']
v_radar = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
v_indiv = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]

fig_radar.add_trace(go.Scatterpolar(r=v_radar, theta=cats, fill='toself', name='Autovaloración'))
fig_radar.add_trace(go.Scatterpolar(r=v_indiv, theta=cats, fill='toself', name='Ponderado Individual'))
fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
st.plotly_chart(fig_radar)

# --- BOTÓN DE IA ---
if st.button("✨ Generar Informe con IA"):
    prompt = f"{MARCO_BARRETT}\nAnaliza a {lider_nombre} con estos datos: {d.to_json()}"
    try:
        with st.spinner('Redactando análisis estratégico...'):
            res = model.generate_content(prompt)
            st.markdown(res.text)
    except Exception as e:
        st.error(f"Error de la IA: {e}. Intenta revisar tu API Key o el nombre del modelo.")
