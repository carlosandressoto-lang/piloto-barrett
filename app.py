import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide")

# Estilo CSS profesional (Fondo blanco, texto negro, estética Barrett)
st.markdown("""
<style>
    .main { background-color: white; color: black; font-family: 'Arial'; }
    h1, h2, h3, h4, h5, h6, p, label { color: black !important; }
    .stSelectbox label { color: black; font-weight: bold; }
    .stButton>button { width: 100%; background-color: #1E3A8A; color: white; height: 3em; border-radius: 8px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN IA ---
# REEMPLAZA CON TU API KEY
API_KEY = "TU_API_KEY_AQUI"

try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
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
st.subheader("Análisis de Diagnóstico 360°")
lider_sel = st.selectbox("Seleccione el líder para el análisis detallado:", df['Nombre_Lider'].unique())
d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

# --- 5. VISUALIZACIÓN ORIGINAL: BARRAS % (RECUPERADAS Y FUNCIONALES) ---
st.divider()
st.subheader("Distribución de Energía por Niveles de Conciencia (%)")
c1, c2, c3 = st.columns(3)

def dibujar_barras(vals, titulo, color):
    labels = ['L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 'L4 - Facilitador', 'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis']
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
        yaxis=dict(autorange="reversed") 
    )
    return fig

v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]

with c1: st.plotly_chart(dibujar_barras(v_auto, "Autovaloración", "#3498db"), use_container_width=True)
with c2: st.plotly_chart(dibujar_barras(v_ind, "Ponderado Individual", "#2ecc71"), use_container_width=True)
with c3: st.plotly_chart(dibujar_barras(v_org, "Promedio Organizacional", "#95a5a6"), use_container_width=True)


# --- 6. NUEVA VISUALIZACIÓN: RELOJES DE ARENA TEÓRICOS CON "SOMBRITAS" (ESTILO FOTO) ---
st.divider()
st.subheader("⏳ Modelo Teórico Barrett (Niveles de Madurez)")
r1, r2, r3 = st.columns(3)

def dibujar_reloj_ premium(vals, titulo, color_principal):
    # Niveles de Barrett (L7 arriba, L1 abajo)
    levels = ['L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 'L4 - Facilitador', 'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis']
    
    # Anchos fijos para simular la forma del reloj (Hourglass): L4 estrecho, L1/L7 anchos
    anchos_ hourglass = [5, 4, 3, 2.2, 3, 4, 5] 
    
    # Colores institucionales Barrett (L lider, T transicion, G gerencia)
    colors_barrett = ["#6F42C1", "#6F42C1", "#6F42C1", "#28A745", "#FD7E14", "#FD7E14", "#FD7E14"]
    
    fig = go.Figure(go.Funnel(
        y=levels,
        x=anchos_ hourglass,
        textinfo="none", # Ocultamos el valor numérico (son fijos)
        # Sombritas/Estilo: Plotly permite definir un gradiente de color para simular volumen
        marker={"color": colors_barrett, "line": {"width": 1, "color": "white"}},
        connector={"line": {"color": "white", "width": 1}, "fillcolor": "rgba(200, 200, 200, 0.1)"}
    ))
    
    fig.update_layout(
        title=dict(text=titulo, x=0.5), height=500, margin=dict(l=50, r=20, t=50, b=50),
        xaxis=dict(visible=False, range=[0, 7]), yaxis=dict(autorange="reversed")
    )
    return fig

# Usamos la misma lógica de los relojes simétricos pero con diseño Funnel para dar el efecto Hourglass
with r1: st.plotly_chart(dibujar_reloj_ premium(v_auto, "Forma Barrett Auto", "#3498db"), use_container_width=True)
with r2: st.plotly_chart(dibujar_reloj_ premium(v_ind, "Forma Barrett Individual", "#2ecc71"), use_container_width=True)
with r3: st.plotly_chart(dibujar_reloj_ premium(v_org, "Forma Barrett Org.", "#95a5a6"), use_container_width=True)


# --- 7. RADAR Y BOTÓN DE INFORME IA (PROMPT REFORZADO) ---
st.divider()
col_radar, col_ia = st.columns([1.5, 1])

with col_radar:
    st.subheader("Radar de Alineación Estratégica")
    fig_radar = go.Figure()
    categorias = ['L1','L2','L3','L4','L5','L6','L7']
    fig_radar.add_trace(go.Scatterpolar(r=v_auto, theta=categorias, fill='toself', name='Autovaloración', line_color='#3498db'))
    fig_radar.add_trace(go.Scatterpolar(r=v_ind, theta=categorias, fill='toself', name='Ponderado Individual', line_color='#2ecc71'))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=450)
    st.plotly_chart(fig_radar, use_container_width=True)

with col_ia:
    if st.button("✨ GENERAR INFORME EJECUTIVO CON IA (BARRETT EXPERTO)"):
        # PROMPT REFORZADO CON MARCO TEÓRICO Y RÚBRICA PROFESIONAL
        CONTEXTO_BARRETT = """
        Marco Teórico de Barrett (7 Niveles):
        L1 - CRISIS (Viabilidad): Salud financiera, seguridad.
        L2 - RELACIONES: Respeto, armonía, comunicación.
        L3 - DESEMPEÑO: Eficiencia, resultados, mejores prácticas.
        L4 - FACILITADOR (Evolución): Transformación, empoderamiento.
        L5 - AUTÉNTICO (Alineación): Confianza, integridad, valores.
        L6 - MENTOR (Colaboración): Desarrollo de otros, alianzas.
        L7 - VISIONARIO (Servicio): Visión global, ética, legado.
        """
        
        RÚBRICA = """
        Rúbrica de evaluación (0-100%):
        - 0 a 65%: Bajo
        - 65 a 75%: Medio
        - 75 a 85%: Alto
        - 85 a 100%: Superior
        """
        
        prompt_estricto = f"""
        Actúa como experto consultor senior en el modelo Barrett. Analiza los resultados de {lider_sel}.
        DATOS REALES: {d.to_json()}
        
        {CONTEXTO_BARRETT}
        {RÚBRICA}
        
        GENERAR INFORME PROFESIONAL (ESTRUCTURA OBLIGATORIA):
        1. Resumen Ejecutivo (Tono Comité Directivo).
        2. Descripción por Niveles (L1 Crisis a L7 Visionario): Usa el 'Ponderado Individual', puntaje y categoría de rúbrica. Analiza potencial y oportunidades de desarrollo basados en la teoría.
        3. Análisis de Autovaloración: Evalúa sesgos entre cómo se percibe el líder vs cómo lo ven.
        4. Matriz de Madurez (Alineación con Cultura): Cruza el desempeño individual con el promedio organizacional.
        5. Perfil de Liderazgo: Define UN estilo predominante y 3 metas tácticas de evolución para el equilibrio del reloj de arena del líder.
        """
        
        try:
            with st.spinner('Procesando análisis de alta dirección...'):
                response = model.generate_content(prompt_estricto)
                st.markdown(f"## Informe Ejecutivo de Liderazgo: {lider_sel}")
                st.write(response.text)
        except Exception as e:
            st.error(f"Error IA: {e}")
