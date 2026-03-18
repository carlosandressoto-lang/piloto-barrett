import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide")

# Estilo para imitar el reporte ejecutivo (Fondo blanco, texto negro)
st.markdown("""
<style>
    .main { background-color: white !important; color: black !important; font-family: 'Helvetica', sans-serif; }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown { color: black !important; }
    .block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN IA ---
API_KEY = "AIzaSyB_llfm1vZ7fZkubkkbMBwup5WCXVw36yY"
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
        df['Nombre_Lider'] = df['Nombre_Lider'].str.strip()
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

# --- 5. VISUALIZACIÓN TIPO REPORTE OFICIAL ---
st.divider()

v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]

levels_barrett = ['L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 'L4 - Facilitador', 'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis']

# Layout: Icono Teórico + 3 Gráficos de Resultados
col_icon, col1, col2, col3 = st.columns([0.8, 1, 1, 1])

# --- COLUMNA 0: ICONO RELOJ DE ARENA (SINTAXIS CORREGIDA) ---
with col_icon:
    # Variable corregida: sin espacio
    anchos_hourglass = [5, 4, 3, 2.2, 3, 4, 5] 
    colores_barrett = ["#6F42C1", "#6F42C1", "#6F42C1", "#28A745", "#FD7E14", "#FD7E14", "#FD7E14"]
    
    fig_icon = go.Figure(go.Funnel(
        y=levels_barrett,
        x=anchos_hourglass,
        textinfo="none",
        marker={"color": colores_barrett, "line": {"width": 1, "color": "white"}},
        connector={"line": {"color": "white", "width": 1}, "fillcolor": "rgba(200, 200, 200, 0.1)"}
    ))
    
    # Anotaciones laterales de agrupación (Liderazgo, Transición, Gerencia)
    fig_icon.add_annotation(x=5.5, y='L6 - Mentor', text="LIDERAZGO", showarrow=False, textangle=-90, font=dict(color="#6F42C1", size=12, weight="bold"))
    fig_icon.add_annotation(x=5.5, y='L4 - Facilitador', text="TRANSICIÓN", showarrow=False, textangle=-90, font=dict(color="#28A745", size=12, weight="bold"))
    fig_icon.add_annotation(x=5.5, y='L2 - Relaciones', text="GERENCIA", showarrow=False, textangle=-90, font=dict(color="#FD7E14", size=12, weight="bold"))

    fig_icon.update_layout(
        template="plotly_white", height=500, margin=dict(l=0, r=50, t=20, b=0),
        xaxis=dict(visible=False, range=[0, 7]),
        yaxis=dict(autorange="reversed", tickfont=dict(size=10, color='black')),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig_icon, use_container_width=True)

# --- COLUMNAS 1, 2, 3: RESULTADOS (SINTAXIS SEGURA) ---
def dibujar_barras_estilo(vals, titulo):
    labels_short = ['L7', 'L6', 'L5', 'L4', 'L3', 'L2', 'L1']
    v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
    colores = ["#6F42C1", "#6F42C1", "#6F42C1", "#28A745", "#FD7E14", "#FD7E14", "#FD7E14"]
    
    fig = go.Figure()
    for i in range(len(v_plot)):
        # Barra izquierda
        fig.add_trace(go.Bar(y=[labels_short[i]], x=[-v_plot[i]], orientation='h', marker_color=colores[i], hoverinfo='none', showlegend=False))
        # Barra derecha con texto %
        fig.add_trace(go.Bar(y=[labels_short[i]], x=[v_plot[i]], orientation='h', marker_color=colores[i], 
                             text=[f"{round(v_plot[i],1)}%"], textposition='inside', textfont=dict(color='white'), hoverinfo='none', showlegend=False))

    fig.update_layout(
        title=dict(text=titulo, x=0.5, font=dict(size=16, color='black')),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-110, 110]),
        yaxis=dict(showgrid=True, gridcolor='#F1F5F9', autorange="reversed", tickfont=dict(size=11, color='black')),
        barmode='overlay', height=500, margin=dict(l=0, r=0, t=40, b=0), template="plotly_white",
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig

with col1: st.plotly_chart(dibujar_barras_estilo(v_auto, "Auto-Percepción"), use_container_width=True)
with col2: st.plotly_chart(dibujar_barras_estilo(v_ind, "Valores Observados"), use_container_width=True)
with col3: st.plotly_chart(dibujar_barras_estilo(v_org, "Valores Organizacionales"), use_container_width=True)

# --- 6. INFORME IA ---
st.divider()
if st.button("🚀 GENERAR INFORME ESTRATÉGICO"):
    prompt = f"Actúa como consultor Barrett. Analiza a {lider_sel} con estos datos: {d.to_json()}. Usa los 7 niveles y la rúbrica de 0-100."
    try:
        with st.spinner('Procesando análisis...'):
            response = model.generate_content(prompt)
            st.markdown(f"## Informe Ejecutivo: {lider_sel}")
            st.write(response.text)
    except Exception as e:
        st.error(f"Error IA: {e}")
