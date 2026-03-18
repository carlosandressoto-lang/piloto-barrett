import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide")

# Estilo para fondo oscuro con texto legible (Blanco)
st.markdown("""
<style>
    .main { background-color: #0e1117; color: white !important; font-family: 'Helvetica Neue', sans-serif; }
    /* Corregimos todos los títulos y párrafos a blanco */
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stSelectbox label { color: white !important; }
    /* Ajuste para el color de Nelson Mauricio en el selector */
    .stSelectbox div[data-baseweb="select"] { color: white; }
    .block-container { padding-top: 1rem; }
    h1 { color: #BFDBFE; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN IA ---
# Usa tu clave real aquí
API_KEY = "TU_API_KEY_AQUI"
try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error(f"Error IA: {e}")

# --- 3. CARGA DE DATOS ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('Resultados_Gerentes.csv', sep=';', decimal=',')
        df.columns = df.columns.str.strip()
        df['Nombre_Lider'] = df['Nombre_Lider'].astype(str).str.strip()
        # Asegurar numéricos
        cols_check = [c for c in df.columns if 'L' in c and ('AUTO' in c or 'INDIV' in c or 'ORG' in c)]
        for col in cols_check:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Error crítico en base de datos: {e}")
        return None

df = load_data()

# --- 4. SELECCIÓN ---
st.title("🏛️ Índice del equilibrio - Dashboard LDR Barrett")
lideres = sorted(df['Nombre_Lider'].unique())
lider_sel = st.selectbox("Seleccione el líder para el análisis detallado:", lideres)
d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

# --- 5. BARRAS ORIGINALES (%) CON TEXTO LEGIBLE ---
st.divider()
st.subheader("Distribución de Energía por Niveles de Conciencia (%)")
c1, c2, c3 = st.columns(3)

def dibujar_barras(vals, titulo, color):
    labels = ['L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 'L4 - Facilitador', 'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis']
    v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
    fig = go.Figure(go.Bar(x=v_plot, y=labels, orientation='h', marker_color=color, text=[f"{round(v,1)}%" for v in v_plot], textposition='inside'))
    fig.update_layout(
        title=dict(text=titulo, font=dict(color='white')), 
        xaxis_range=[0, 105], height=400, template="plotly_dark",
        margin=dict(l=0, r=10, t=40, b=20), 
        yaxis=dict(autorange="reversed", tickfont=dict(color='white')), 
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig

v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]

with c1: st.plotly_chart(dibujar_barras(v_auto, "Autovaloración", "#3498db"), use_container_width=True)
with c2: st.plotly_chart(dibujar_barras(v_ind, "Individual (360)", "#2ecc71"), use_container_width=True)
with c3: st.plotly_chart(dibujar_barras(v_org, "Organizacional (Cultura)", "#95a5a6"), use_container_width=True)

# --- 6. RELOJES DE ARENA PREMIUM CON DATOS ADENTRO Y TEXTO LEGIBLE ---
st.divider()
st.subheader("⏳ Relojes de Arena (Nivel de Desarrollo 1 a 4)")

# Lógica para convertir puntaje a escala de madurez 1-4 (según rúbrica)
def a_escala_4(v):
    if v < 65: return 1
    if v < 75: return 2
    if v < 85: return 3
    return 4

def dibujar_reloj_hourglass_visible(vals, titulo):
    levels = ['L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 'L4 - Facilitador', 'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis']
    # Anchos para simular la forma simétrica del reloj de diamante
    anchos_hourglass = [5, 4, 3, 2.2, 3, 4, 5] 
    
    # Colores institucionales Barrett (L lider, T transicion, G gerencia)
    colors_barrett = ["#6F42C1", "#6F42C1", "#6F42C1", "#28A745", "#FD7E14", "#FD7E14", "#FD7E14"]
    
    # Calculamos la escala 1-4 para el texto de Nelson Mauricio
    textos_desarrollo = []
    for x in vals:
        textos_desarrollo.append(f"Nivel {a_escala_4(x)}")

    # Invertimos el orden para que coincida con el gráfico Funnel (L7 arriba)
    v_hourglass_v4 = [textos_desarrollo[6], textos_desarrollo[5], textos_desarrollo[4], textos_desarrollo[3], textos_desarrollo[2], textos_desarrollo[1], textos_desarrollo[0]]

    fig = go.Figure(go.Funnel(
        y=levels,
        x=anchos_hourglass,
        text=v_hourglass_v4, # Inyectamos el Nivel 1,2,3 o 4 como texto
        textinfo="text", # Ocultamos el ancho, solo queremos el Nivel
        textfont=dict(color='white', size=14, family='Arial Black'), # Texto legible y fuerte
        marker={"color": colors_barrett, "line": {"width": 2, "color": "white"}},
        connector={"line": {"color": "white", "width": 1}, "fillcolor": "rgba(200, 200, 200, 0.1)"}
    ))
    
    fig.update_layout(
        title=dict(text=titulo, x=0.5, font=dict(color='white')), 
        height=500, margin=dict(l=100, r=20, t=50, b=50), 
        yaxis=dict(autorange="reversed", tickfont=dict(color='white')),
        xaxis=dict(visible=False, range=[0, 6]), # Rango para simetría
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig

r1, r2, r3 = st.columns(3)
# Títulos corregidos (Ejecutivos)
with r1: st.plotly_chart(dibujar_hourglass_visible(v_auto, "Autopercepción Barrett"), use_container_width=True)
with r2: st.plotly_chart(dibujar_hourglass_visible(v_ind, "Competencia Individual"), use_container_width=True)
with r3: st.plotly_chart(dibujar_hourglass_visible(v_org, "Cultura Organizacional"), use_container_width=True)

# --- 7. RADAR Y INFORME IA CON PROMPT REFORZADO ---
st.divider()
col_radar, col_ia = st.columns([1.5, 1])

with col_radar:
    st.subheader("Radar de Alineación Estratégica (%)")
    fig_radar = go.Figure()
    cats = ['L1','L2','L3','L4','L5','L6','L7']
    fig_radar.add_trace(go.Scatterpolar(r=v_auto, theta=cats, fill='toself', name='Autovaloración', line_color='#3498db'))
    fig_radar.add_trace(go.Scatterpolar(r=v_ind, theta=cats, fill='toself', name='Individual', line_color='#2ecc71'))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=450)
    # Fondo transparente para integrar
    fig_radar.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_radar, use_container_width=True)

with col_ia:
    if st.button("✨ GENERAR INFORME EJECUTIVO"):
        prompt = f"""
        Actúa como consultor senior experto en Barrett. Analiza los resultados 360 de {lider_sel}.
        DATOS REALES: {d.to_json()}
        
        INSTRUCCIONES:
        1. Contextualiza cada nivel según Richard Barrett (L1 a L7).
        2. Aplica rúbrica estricta (0-100%): 0-65 Bajo, 66-75 Medio, 76-85 Alto, 86-100 Superior.
        3. Analiza la forma del Reloj de Arena (si el desarrollo está en la base o en la cima).
        4. Define estilo predominante y 3 acciones tácticas para Gestión Humana de Confa.
        Escribe en español profesional y analítico.
        """
        try:
            with st.spinner('Procesando análisis de alta dirección...'):
                response = model.generate_content(prompt)
                st.markdown(f"## Informe Ejecutivo de Liderazgo: {lider_sel}")
                st.write(response.text)
        except Exception as e:
            st.error(f"Error IA: {e}")
