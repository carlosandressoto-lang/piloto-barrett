import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide")

# Estilo para imitar el reporte blanco de Jennifer García, colores limpios
st.markdown("""
<style>
    .main { background-color: white !important; color: black !important; font-family: 'Helvetica', sans-serif; }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown { color: black !important; }
    /* Ajuste de márgenes para que los gráficos se alineen */
    .block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN IA ---
API_KEY = "AIzaSyB_llfm1vZ7fZkubkkbMBwup5WCXVw36yY"
try:
    genai.configure(api_key=API_KEY)
    # Modelo Gemini-2.5-flash (Tu modelo de éxito)
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error(f"Error IA: {e}")

# --- 3. CARGA DE DATOS ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('Resultados_Gerentes.csv', sep=';', decimal=',')
        df.columns = df.columns.str.strip()
        df['Nombre_Lider'] = df['Nombre_Lider'].str.strip()
        # Asegurar numéricos
        cols_niveles = [c for c in df.columns if 'L' in c]
        for col in cols_niveles:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Error cargando archivo: {e}")
        return None

df = load_data()

# --- 4. SELECCIÓN ---
st.title("🏛️ Índice del equilibrio - Dashboard LDR Barrett")
lider_sel = st.selectbox("Seleccione el líder:", df['Nombre_Lider'].unique())
d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

# ==============================================================================
# --- 5. VISUALIZACIÓN: REPORTE ESTILO "JENNIFER GARCÍA" ---
# ==============================================================================
st.divider()

# Preparación de datos (L1 a L7)
v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]

# Definición de nombres oficiales de Barrett (Eje Y)
levels_barrett = ['L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 'L4 - Facilitador', 'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis']

# Layout de 4 columnas (Icono Barrett Teórico Premium + 3 Gráficos Funcionales)
col_icon_premium, col1, col2, col3 = st.columns([0.8, 1, 1, 1])


# --- COLUMNA 0: ICONO RELOJ DE ARENA "PREMIUM" (DISEÑO BONITO + SOMBRAS) ---
with col_icon_premium:
    
    # Creamos la visualización del reloj usando un gráfico Funnel que permite gradientes
    
    # Anchos fijos para simular la forma del reloj (Hourglass)
    # L7 ancho, L6 menos, L5 menos, L4 estrecho (Transición), L3 ancho, L2 más, L1 más (Base)
    anchos_ hourglass = [5, 4, 3, 2.5, 3, 4, 5] 
    
    # Mapeo de colores oficiales Barrett (Morado, Verde, Naranja)
    colores_barrett = ["#6F42C1", "#6F42C1", "#6F42C1", "#28A745", "#FD7E14", "#FD7E14", "#FD7E14"]
    
    fig_icon = go.Figure()
    
    # Dibujamos las barras simétricas del icono
    fig_icon.add_trace(go.Funnel(
        y=levels_barrett,
        x=anchos_ hourglass,
        textinfo="none", # Ocultamos los anchos, solo queremos la forma
        # Solución de diseño para "Sombritas": Plotly permite gradientes de color usando listas de colores
        # para simular un efecto de luz sobre las barras
        marker={
            "color": colores_barrett,
            "line": {"width": 1, "color": "white"}
        },
        connector={"line": {"color": "white", "width": 1}, "fillcolor": "rgba(229, 231, 235, 0.2)"} # Sombreado entre niveles
    ))
    
    # Añadimos las anotaciones de categoría LIDERAZGO, TRANSICIÓN, GERENCIA al lado (Estilo Jennifer)
    fig_icon.add_annotation(x=4, y='L6 - Mentor', text="LIDERAZGO", showarrow=False, font=dict(color="#6F42C1", size=11, weight='bold'), textangle=90)
    fig_icon.add_annotation(x=4, y='L4 - Facilitador', text="TRANSICIÓN", showarrow=False, font=dict(color="#28A745", size=11, weight='bold'), textangle=90)
    fig_icon.add_annotation(x=4, y='L2 - Relaciones', text="GERENCIA", showarrow=False, font=dict(color="#FD7E14", size=11, weight='bold'), textangle=90)

    fig_icon.update_layout(
        title=dict(text="Modelo Teórico (HOURGLASS)", x=0.5, font=dict(size=14, color='black')),
        # Configuración para silueta de reloj
        yaxis=dict(showgrid=True, gridcolor='#F1F5F9', autorange="reversed", tickfont=dict(size=10, color='black')),
        xaxis=dict(visible=False, range=[0, 7]), # Rango expandido para las anotaciones laterales
        template="plotly_white", height=500, # Fondo blanco para integrar
        margin=dict(l=0, r=30, t=30, b=0),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig_icon, use_container_width=True)


# --- COLUMNAS 1, 2, 3: TUS GRÁFICOS DE BARRAS FUNCIONALES (SINTAXIS CORREGIDA) ---
def dibujar_barras_estilo(vals, titulo):
    # Etiquetas cortas para los resultados (%)
    labels_short = ['L7', 'L6', 'L5', 'L4', 'L3', 'L2', 'L1']
    v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
    
    # Colores Barrett por nivel
    colores_barrett = ["#6F42C1", "#6F42C1", "#6F42C1", "#28A745", "#FD7E14", "#FD7E14", "#FD7E14"]
    
    fig = go.Figure()
    
    # Dibujamos las barras de forma individual para evitar el TypeError de sintaxis de Plotly
    # en versiones anteriores
    for i in range(len(v_plot)):
        # Barra simétrica izquierda
        fig.add_trace(go.Bar(
            y=[labels_short[i]],
            x=[-v_plot[i]],
            orientation='h',
            marker_color=colores_barrett[i],
            hoverinfo='none',
            showlegend=False
        ))
        # Barra simétrica derecha (con el texto)
        fig.add_trace(go.Bar(
            y=[labels_short[i]],
            x=[v_plot[i]],
            orientation='h',
            marker_color=colores_barrett[i],
            text=[f"{round(v_plot[i],1)}%"],
            textposition='inside',
            textfont=dict(color='white'),
            hoverinfo='none',
            showlegend=False
        ))

    fig.update_layout(
        title=dict(text=titulo, x=0.5, font=dict(size=16, color='black')),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-105, 105]),
        yaxis=dict(showgrid=True, gridcolor='#F1F5F9', autorange="reversed", tickfont=dict(size=10, color='black')),
        barmode='overlay', height=500, # Overlay para el efecto centrado
        margin=dict(l=0, r=0, t=30, b=0), template="plotly_white",
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig

with col1: st.plotly_chart(dibujar_barras_estilo(v_auto, "Auto-Percepción"), use_container_width=True)
with col2: st.plotly_chart(dibujar_barras_estilo(v_ind, "Valores Observados"), use_container_width=True)
with col3: st.plotly_chart(dibujar_barras_estilo(v_org, "Valores Deseados (Org)"), use_container_width=True)


# --- 6. INFORME IA (FUERA DE COLUMNAS PARA MÁXIMO IMPACTO) ---
st.divider()
col_ia, col_radar = st.columns([1.5, 1])

with col_ia:
    if st.button("✨ GENERAR ANÁLISIS CONSULTIVO SENIOR"):
        prompt = f"""
        Actúa como un experto consultor senior de liderazgo en el modelo Barrett. 
        Analiza a {lider_sel} basándote en los datos de 'Resultados Gerentes.xlsx': {d.to_json()}
        
        Sigue estrictamente la teoría de Richard Barrett de los 7 niveles:
        L1 Viabilidad, L2 Relaciones, L3 Desempeño, L4 Evolución, L5 Alineación, L6 Colaboración, L7 Servicio.
        Rúbrica: 0-65 Bajo, 66-75 Medio, 76-85 Alto, 86-100 Superior.
        Genera un informe que incluya:
        1. Resumen Ejecutivo de Alto Impacto.
        2. Análisis por Niveles (Basado en Ponderado Individual).
        3. Evaluación de Brechas (Auto vs Individual).
        4. Matriz de Madurez (Alineación con Cultura Organizacional).
        5. Plan de Acción: Define UN (1) estilo predominante y 3 metas tácticas de evolución para el 'Reloj de Arena' del líder.
        """
        try:
            with st.spinner('Analizando datos como consultor Barrett...'):
                response = model.generate_content(prompt)
                st.markdown(f"## Informe Ejecutivo de Liderazgo: {lider_sel}")
                st.write(response.text)
        except Exception as e:
            st.error(f"Error IA: {e}")

with col_radar:
    # Mantenemos tu Radar funcional, pero en blanco para integrar
    fig_radar = go.Figure()
    cats = ['L1','L2','L3','L4','L5','L6','L7']
    fig_radar.add_trace(go.Scatterpolar(r=v_auto, theta=cats, fill='toself', name='Auto', line_color='#3498db'))
    fig_radar.add_trace(go.Scatterpolar(r=v_ind, theta=cats, fill='toself', name='Individual', line_color='#2ecc71'))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=450, template="plotly_white")
    st.plotly_chart(fig_radar, use_container_width=True)
