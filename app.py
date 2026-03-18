import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide")

# Estilo para imitar el reporte blanco de Jennifer
st.markdown("""
<style>
    .main { background-color: white !important; color: black !important; }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown { color: black !important; }
    .stSelectbox div[data-baseweb="select"] { color: black; }
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
        # Asegurar numéricos
        niv_cols = [c for c in df.columns if 'L' in c]
        for col in niv_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Error cargando CSV: {e}")
        return None

df = load_data()

# --- 4. INTERFAZ Y SELECCIÓN ---
st.title("🏛️ Índice del equilibrio - Dashboard LDR")
lider_sel = st.selectbox("Seleccione el líder:", df['Nombre_Lider'].unique())
d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

# --- 5. DISEÑO DE REPORTE ESTILO JENNIFER ---
st.divider()

# Preparación de datos (L1 a L7)
v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]

# Etiquetas para el eje Y (L7 arriba)
labels_y = ['L7 Vision.', 'L6 Mentor', 'L5 Autént.', 'L4 Facil.', 'L3 Desemp.', 'L2 Relac.', 'L1 Crisis']

# Layout de 4 columnas (Icono Barrett + 3 Gráficos)
col_icon, col_auto, col_ind, col_org = st.columns([0.6, 1, 1, 1])

with col_icon:
    st.write("") # Espaciado
    # Dibujamos una silueta de reloj de arena manual con Markdown/HTML para que sea fija
    st.markdown("""
    <div style="text-align: right; font-family: sans-serif;">
        <div style="color: #6F42C1; font-weight: bold; height: 120px;">LIDERAZGO<br><small>(L5-L7)</small></div>
        <div style="color: #28A745; font-weight: bold; height: 50px;">TRANSICIÓN<br><small>(L4)</small></div>
        <div style="color: #FD7E14; font-weight: bold; height: 120px; margin-top:20px;">GERENCIA<br><small>(L1-L3)</small></div>
    </div>
    """, unsafe_allow_html=True)

def dibujar_barras_centradas(vals, titulo):
    # Invertimos los valores para que L7 (índice 6) esté arriba
    v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
    
    # Colores por nivel (Barrett Jennifer)
    colores = ["#6F42C1", "#6F42C1", "#6F42C1", "#28A745", "#FD7E14", "#FD7E14", "#FD7E14"]
    
    fig = go.Figure()
    # Barra izquierda (negativa para centrar)
    fig.add_trace(go.Bar(
        y=labels_y, x=[-x for x in v_plot],
        orientation='h', marker_color=colores, hoverinfo='none', showlegend=False
    ))
    # Barra derecha (positiva con el texto)
    fig.add_trace(go.Bar(
        y=labels_y, x=v_plot,
        orientation='h', marker_color=colores,
        text=[f"{round(v,1)}%" for v in v_plot],
        textposition='inside', textfont=dict(color='white'),
        hoverinfo='none', showlegend=False
    ))

    fig.update_layout(
        title=dict(text=titulo, x=0.5, font=dict(size=16)),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-110, 110]),
        yaxis=dict(showgrid=False, tickfont=dict(size=10)),
        barmode='overlay', height=400, margin=dict(l=0, r=0, t=40, b=0),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig

with col_auto: st.plotly_chart(dibujar_barras_centradas(v_auto, "Auto-Percepción"), use_container_width=True)
with col_ind: st.plotly_chart(dibujar_barras_centradas(v_ind, "Valores Observados"), use_container_width=True)
with col_org: st.plotly_chart(dibujar_barras_centradas(v_org, "Valores Organizacionales"), use_container_width=True)

# --- 6. RADAR Y BOTÓN IA ---
st.divider()
if st.button("✨ Generar Informe Ejecutivo"):
    prompt = f"Analiza los resultados de {lider_sel} bajo el modelo Barrett: {d.to_json()}"
    try:
        with st.spinner('Analizando...'):
            response = model.generate_content(prompt)
            st.markdown(response.text)
    except Exception as e:
        st.error(f"Error IA: {e}")
