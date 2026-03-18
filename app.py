import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- CONFIGURACIÓN ESTÉTICA ---
st.set_page_config(page_title="LDR Barrett - Informe Ejecutivo", layout="wide")

# --- CONEXIÓN CON EL CEREBRO (GEMINI) ---
genai.configure(api_key="AIzaSyCvoIkCyad19aAxLdIt7JF-3k_kc6btJts")
model = genai.GenerativeModel('gemini-1.5-flash')

# --- MARCO TEÓRICO INTEGRADO (Basado en tus fuentes) ---
MARCO_BARRETT = """
Modelo de Liderazgo de Barrett:
- Nivel 7: LÍDER VISIONARIO. Propósito de vivir, responsabilidad social[cite: 14, 15].
- Nivel 6: LÍDER MENTOR/SOCIO. Colaboración, desarrollo de otros, asociaciones[cite: 17, 18].
- Nivel 5: LÍDER AUTÉNTICO. Confianza, integridad, pasión, honestidad[cite: 22, 23].
- Nivel 4: FACILITADOR/INNOVADOR. Evolución valiente, empoderamiento, toma de riesgos[cite: 25, 26].
- Nivel 3: GESTOR DE DESEMPEÑO. Logrando la excelencia, resultados, mejores prácticas[cite: 27, 29].
- Nivel 2: GESTOR DE RELACIONES. Escuchar, respeto, resolución de conflictos[cite: 32].
- Nivel 1: GESTOR DE CRISIS. Viabilidad, estabilidad financiera, consciencia de gastos[cite: 33, 34].
"""

# --- CARGA DE DATOS ---
try:
    df = pd.read_csv('Resultados_Gerentes.csv', sep=';', decimal=',') # Agregamos el separador y el decimal
except Exception as e:
    st.error(f"Error real detectado: {e}") # Esto nos mostrará el error verdadero si persiste
    st.stop()

# --- INTERFAZ DE USUARIO ---
st.title("🏛️ Plataforma de Liderazgo Barrett")
st.markdown("### Diagnóstico 360° - Nivel Directivo")

# Selector de Líder
lider_nombre = st.selectbox("Seleccione el líder para visualizar el informe:", df['Nombre_Lider'].unique())
d = df[df['Nombre_Lider'] == lider_nombre].iloc[0]

# --- GRÁFICOS: TRIPLE RELOJ DE ARENA ---
st.subheader("Comparativa de Energía por Niveles de Conciencia")
c1, c2, c3 = st.columns(3)

def dibujar_reloj(valores, titulo, color):
    niveles = ['L7', 'L6', 'L5', 'L4', 'L3', 'L2', 'L1']
    # Invertimos valores para que L7 esté arriba visualmente
    fig = go.Figure(go.Bar(x=valores[::-1], y=niveles, orientation='h', marker_color=color))
    fig.update_layout(title=titulo, xaxis_range=[0,105], height=400, margin=dict(l=10, r=10, t=40, b=10))
    fig.update_traces(text=[f"{v}%" for v in valores[::-1]], textposition='outside')
    return fig

with c1:
    st.plotly_chart(dibujar_reloj([d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7], "Autovaloración", "#3498db"), use_container_width=True)
with c2:
    st.plotly_chart(dibujar_reloj([d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7], "Ponderado Individual", "#2ecc71"), use_container_width=True)
with c3:
    st.plotly_chart(dibujar_reloj([d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7], "Ponderado Organizacional", "#95a5a6"), use_container_width=True)

# --- RADAR DE ALINEACIÓN ---
st.divider()
st.subheader("Radar de Alineación Estratégica")
fig_radar = go.Figure()
categorias = ['L1','L2','L3','L4','L5','L6','L7']
fig_radar.add_trace(go.Scatterpolar(r=[d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7], theta=categorias, fill='toself', name='Autovaloración'))
fig_radar.add_trace(go.Scatterpolar(r=[d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7], theta=categorias, fill='toself', name='Ponderado Individual'))
fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=True)
st.plotly_chart(fig_radar)

# --- BOTÓN DE INFORME CON IA ---
if st.button("✨ Generar Análisis Estratégico (IA)"):
    prompt = f"""
    {MARCO_BARRETT}
    
    INSTRUCCIONES:
    1. Analiza a {lider_nombre} usando los datos adjuntos.
    2. Rúbrica: 0-65 Bajo, 66-75 Medio, 76-85 Alto, 86-100 Superior.
    3. Compara Autovaloración vs Ponderado Individual (Brechas de percepción).
    4. Compara Ponderado Individual vs Organizacional (Potencial de Mentoría).
    5. Define 1 estilo de liderazgo predominante.
    
    DATOS DEL LÍDER:
    {d.to_json()}
    """
    with st.spinner('Procesando niveles de conciencia...'):
        res = model.generate_content(prompt)
        st.markdown("### Informe Ejecutivo Personalizado")
        st.markdown(res.text)
