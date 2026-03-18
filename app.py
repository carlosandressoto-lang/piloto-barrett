import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide", page_icon="🏛️")

# Estilo CSS para ajustar márgenes y fuentes (opcional)
st.markdown("""
<style>
    .reportview-container .main .block-container{ padding-top: 1rem; }
    h1 { color: #1E3A8A; }
    h2 { color: #1E40AF; border-bottom: 2px solid #BFDBFE; }
</style>
""", unsafe_with_stdio=True)

# --- 2. CONEXIÓN IA (SOLUCIÓN DEFINITIVA) ---
# Usamos el modelo que te funcionó: gemini-1.5-flash-8b (o flash-latest)
API_KEY = "AIzaSyB_llfm1vZ7fZkubkkbMBwup5WCXVw36yY" 
try:
    genai.configure(api_key=API_KEY)
    # Cambiado al modelo de alta compatibilidad que te funcionó
    model = genai.GenerativeModel('gemini-2.5-flash-8b')
except Exception as e:
    st.error(f"Error de configuración IA: {e}")

# --- 3. CARGA Y LIMPIEZA DE DATOS (CSV) ---
try:
    df = pd.read_csv('Resultados_Gerentes.csv', sep=';', decimal=',')
    df.columns = df.columns.str.strip()
    df['Nombre_Lider'] = df['Nombre_Lider'].str.strip()
    
    # Asegurar numéricos (L1 a L7 para AUTO, INDIV, ORG)
    cols_check = [c for c in df.columns if 'L' in c and ('AUTO' in c or 'INDIV' in c or 'ORG' in c)]
    for col in cols_check:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
except Exception as e:
    st.error(f"Error cargando datos: {e}")
    st.stop()

# --- 4. INTERFAZ Y SELECCIÓN ---
st.title("🏛️ Plataforma de Liderazgo Barrett - Confa")
st.markdown("### Diagnóstico 360° - Análisis de Conciencia Organizacional")
st.divider()

lider_sel = st.selectbox("Seleccione el líder para visualizar:", df['Nombre_Lider'].unique())
d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

# --- 5. GRÁFICO RADAR (ALINEACIÓN) ---
# Lo movemos arriba para ver la alineación primero
st.subheader("Radar de Alineación Estratégica")
fig_radar = go.Figure()
cats = ['L1 Crisis','L2 Relac.','L3 Desemp.','L4 Facil.','L5 Autént.','L6 Mentor','L7 Vision.']
v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]

fig_radar.add_trace(go.Scatterpolar(r=v_auto, theta=cats, fill='toself', name='Autovaloración', line_color='#3498db'))
fig_radar.add_trace(go.Scatterpolar(r=v_ind, theta=cats, fill='toself', name='Ponderado Individual', line_color='#2ecc71'))
fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=True, height=500)
st.plotly_chart(fig_radar, use_container_width=True)

# --- 6. VISUALIZACIÓN: TRIPLE RELOJ DE ARENA (SOLUCIÓN GRÁFICA) ---
# Debajo del radar, restauramos los 3 relojes con la lógica de Barrett (L7 arriba)
st.divider()
st.subheader("Distribución de Energía por Niveles de Conciencia")
c1, c2, c3 = st.columns(3)

def dibujar_reloj_hourglass(vals, titulo, color):
    # Nombres Barrett para los niveles
    labels = [
        'L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 
        'L4 - Facilitador', 
        'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis'
    ]
    # Los datos vienen en orden L1, L2... L7. Los invertimos para que L7 quede arriba.
    # [vals[6] es L7, vals[5] es L6... vals[0] es L1]
    v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
    
    # Rúbrica de colores (opcional, pero ayuda a la visual)
    text_labels = []
    for v in v_plot:
        if v >= 85: r = "Superior"
        elif v >= 75: r = "Alto"
        elif v >= 65: r = "Medio"
        else: r = "Bajo"
        text_labels.append(f"{round(v,1)}% ({r})")

    fig = go.Figure(go.Bar(
        x=v_plot, 
        y=labels, 
        orientation='h', 
        marker_color=color,
        text=text_labels,
        textposition='inside',
        textfont=dict(size=12, color='white')
    ))
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=18)),
        xaxis_range=[0, 105], 
        height=500, # Más alto para que se aprecie el "reloj"
        margin=dict(l=0, r=10, t=50, b=0),
        xaxis=dict(showgrid=False),
        # 'reversed' en yaxis NO se usa aquí, ya invertimos v_plot manualmente
    )
    return fig

with c1:
    st.plotly_chart(dibujar_reloj_hourglass(v_auto, "Autovaloración", "#3498db"), use_container_width=True)
with c2:
    st.plotly_chart(dibujar_reloj_hourglass(v_ind, "Ponderado Individual", "#2ecc71"), use_container_width=True)
with c3:
    v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]
    st.plotly_chart(dibujar_reloj_hourglass(v_org, "Promedio Organizacional", "#95a5a6"), use_container_width=True)


# --- 7. BOTÓN DE INFORME IA CON PROMPT REFORZADO (SOLUCIÓN DE CONTENIDO) ---
st.divider()
if st.button("✨ Generar Informe Ejecutivo con IA (Prompt Barrett Experto)"):
    
    # EL PROMPT REFORZADO SIGUIENDO TUS REGLAS A RAJATABLA
    PROMPT_ESTRICTO = f"""
    --- PROPÓSITO Y METAS ---
    Actúa como un experto consultor de desarrollo de liderazgo senior, especializado exclusivamente en el modelo de los 7 niveles de conciencia de Richard Barrett. Tu objetivo es analizar los resultados del diagnóstico 360 del líder {lider_sel}. El informe está dirigido al comité ejecutivo y al gerente de gestión humana, exigiendo un tono profesional, ejecutivo, analítico y con conclusiones accionables de alto valor estratégico.

    --- FUENTE DE VERDAD Y COMPORTAMIENTOS ---
    1) Utiliza ÚNICAMENTE los siguientes datos en formato JSON proporcionados a continuación. No inventes datos ni asumas información fuera de esta tabla.
    Datos del Líder ({lider_sel}): {d.to_json()}
    2) Cíñete estrictamente a la teoría del modelo de Barrett. No uses otros marcos de referencia.

    --- RÚBRICA DE EVALUACIÓN OBLIGATORIA ---
    Aplica esta rúbrica para calificar cada nivel de conciencia (valores numéricos):
    - 0 a 65: Bajo
    - 65 a 75: Medio
    - 75 a 85: Alto
    - 85 a 100: Superior

    --- ESTRUCTURA DEL INFORME (RESPETA EL ORDEN Y LOS TÍTULOS) ---
    Genera el informe con la siguiente estructura exacta:

    1. DESCRIPCIÓN POR NIVELES (LOS 7 NIVELES DE CONCIENCIA)
    Realiza un desglose analítico de los 7 niveles (L1 Crisis a L7 Visionario). Para cada nivel, menciona el puntaje (Individual), su calificación según rúbrica y describe brevemente el potencial observado y las oportunidades de desarrollo fundamentadas en la teoría de Barrett.

    2. ANÁLISIS DE AUTOVALORACIÓN
    Evalúa cómo se percibe el líder a sí mismo comparando sus puntajes AUTO L1-L7. ¿Hay sesgos? ¿Dónde está su mayor enfoque?

    3. ANÁLISIS DE PONDERADO INDIVIDUAL
    Evalúa la competencia real observada en el individuo (Puntajes INDIV L1-L7). ¿Cómo impacta su comportamiento al equipo según la rúbrica?

    4. MATRIZ DE MADUREZ (ALINEACIÓN Y CULTURA)
    Cruza el Ponderado Individual (cómo actúa) con el Ponderado Organizacional (la cultura de la empresa, Puntajes ORG L1-L7). Determina la alineación del líder con la cultura de Confa y su potencial de crecimiento dentro de esta.

    5. PERFIL DE LIDERAZGO
    Define UN (1) estilo de liderazgo predominante para {lider_sel} basado en su nivel INDIVIDUAL más desarrollado (ej. "Líder Facilitador" si L4 es Superior) y ofrece recomendaciones concretas de gran valor estratégico para buscar el equilibrio en los 7 niveles.
    """
    
    try:
        with st.spinner('Analizando datos como consultor Barrett...'):
            response = model.generate_content(PROMPT_ESTRICTO)
            st.success("Informe ejecutivo generado.")
            st.markdown(f"## Informe Ejecutivo de Liderazgo: {lider_sel}")
            st.markdown(response.text)
    except Exception as e:
        st.error(f"Error al generar el informe con Gemini-1.5-Flash-8b: {e}")
        st.info("Revisa la conexión de red o la validez de tu API Key.")
