import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTILO (SOLUCIÓN DE DISEÑO) ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide")

# Estilo CSS para imitar el reporte de Jennifer: Colores limpios y layout estructurado
st.markdown("""
<style>
    .main { background-color: white; color: black; font-family: 'Arial'; }
    h1, h2, h3, h4, h5, h6, p, label { color: black !important; }
    .reportview-container .main .block-container{ padding-top: 1rem; }
    h1 { color: #2C3E50; font-family: 'Helvetica'; border-bottom: 2px solid #ECF0F1; padding-bottom: 10px; }
    h3 { color: #7F8C8D; margin-top: 2rem; }
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
        niv_cols = [c for c in df.columns if 'L' in c and any(x in c for x in ['AUTO', 'INDIV', 'ORG'])]
        for col in niv_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Error cargando CSV: {e}")
        return None

df = load_data()

# --- 4. INTERFAZ Y SELECCIÓN ---
st.title("🏛️ Índice del equilibrio - Dashboard LDR")
lideres = sorted(df['Nombre_Lider'].unique())
lider_sel = st.selectbox("Seleccione el líder para visualizar:", lideres)
d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

# --- 5. LÓGICA DE VISUALIZACIÓN (SOLUCIÓN DE DISEÑO BARRETT) ---
st.divider()

# Extraemos valores para simplificar
v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]

# Definimos etiquetas simétricas: Barrett usa "Reloj de Arena" (Hourglass), L7 arriba
levels_ hourglass = ['L7 Vision', 'L6 Mentor', 'L5 Autént.', 'L4 Facil.', 'L3 Desemp.', 'L2 Relac.', 'L1 Crisis']
levels_short = ['L7', 'L6', 'L5', 'L4', 'L3', 'L2', 'L1']

# Agrupaciones oficiales de Barrett
agrupaciones = {
    'Liderazgo (Nivel 5-7)': {'labels': ['L7', 'L6', 'L5'], 'indices': [6, 5, 4], 'color': '#6F42C1'}, # Morado Jennifer
    'Transición (Nivel 4)': {'labels': ['L4'], 'indices': [3], 'color': '#28A745'}, # Verde Jennifer
    'Gerencia (Nivel 1-3)': {'labels': ['L3', 'L2', 'L1'], 'indices': [2, 1, 0], 'color': '#FD7E14'} # Naranja Jennifer
}

# Creamos una columna para el reloj de arena a la izquierda (como en el reporte de Jennifer)
col_ hourglass, col_auto, col_ind, col_org = st.columns([0.8, 1, 1, 1])

with col_ hourglass:
    # Creamos un gráfico "Funnel" simplificado para imitar la silueta del reloj a la izquierda
    st.write("") # Espaciador
    fig_hourglass = go.Figure(go.Funnel(
        y = levels_short,
        x = [1, 1, 1, 1, 1, 1, 1], # Ancho constante para silueta pura
        textinfo = "none",
        marker = {"color": ["#6F42C1", "#6F42C1", "#6F42C1", "#28A745", "#FD7E14", "#FD7E14", "#FD7E14"]},
        connector = {"line": {"color": "white", "width": 1}},
        showlegend=False
    ))
    fig_hourglass.update_layout(height=400, margin=dict(l=30, r=0, t=10, b=10), xaxis=dict(visible=False), yaxis=dict(visible=False))
    st.plotly_chart(fig_hourglass, use_container_width=True)
    
    # Texto de categorías
    st.markdown("<p style='text-align:right; color:#6F42C1; font-weight:bold;'>Liderazgo</p>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:right; color:#28A745; font-weight:bold; margin-top:55px;'>Transición</p>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:right; color:#FD7E14; font-weight:bold; margin-top:55px;'>Gerencia</p>", unsafe_allow_html=True)


# Función para dibujar las barras mariposa simétricas (como Valores Personales en Jennifer García)
def dibujar_barras_mariposa(vals, titulo):
    # Invertimos los datos para L7 arriba
    v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
    
    # Simetría: Creamos datos negativos y positivos para centrar
    v_neg = [-x for x in v_plot]
    v_pos = v_plot
    
    fig = go.Figure()
    
    # Dibujamos las 3 agrupaciones de colores
    for cat_name, info in agrupaciones.items():
        indices_grafico = []
        for i in info['indices']:
            indices_grafico.append(labels_ hourglass[i]) # Buscamos la etiqueta correcta
            
        # Filtramos valores por categoría (L1-L3 Gerencia, etc.)
        vals_neg = []
        vals_pos = []
        for idx in info['indices']:
            vals_neg.append(-vals[idx])
            vals_pos.append(vals[idx])

        # Barra izquierda (negativa)
        fig.add_trace(go.Bar(
            y=labels_ hourglass[i],
            x=vals_neg,
            orientation='h',
            marker_color=info['color'],
            hoverinfo='none',
            showlegend=False
        ))
        # Barra derecha (positiva)
        fig.add_trace(go.Bar(
            y=labels_ hourglass[i],
            x=vals_pos,
            orientation='h',
            marker_color=info['color'],
            text=[f"{round(vals[idx],1)}%" for idx in info['indices']],
            textposition='inside',
            textfont=dict(color='white'),
            hoverinfo='none',
            showlegend=False
        ))

    fig.update_layout(
        title=dict(text=titulo, x=0.5, font=dict(color='black', size=16)),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-105, 105]),
        yaxis=dict(showgrid=True, gridcolor='#ECF0F1', tickfont=dict(color='black'), autorange="reversed"),
        height=400,
        margin=dict(l=0, r=0, t=30, b=0),
        barmode='overlay', # Overlay para el efecto mariposa
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig

# Dibujamos las 3 columnas simétricas
with col_auto: st.plotly_chart(dibujar_barras_mariposa(v_auto, "Auto-Percepción"), use_container_width=True)
with col_ind: st.plotly_chart(dibujar_barras_mariposa(v_ind, "Individual (360)"), use_container_width=True)
with col_org: st.plotly_chart(dibujar_barras_mariposa(v_org, "Organizacional (Cultura)"), use_container_width=True)


# --- 6. RADAR Y BOTÓN (Mantenemos tu lógica funcional) ---
st.divider()
col_radar, col_button = st.columns([2, 1])

with col_radar:
    st.subheader("Radar de Alineación Estratégica")
    fig_radar = go.Figure()
    cats = ['L1','L2','L3','L4','L5','L6','L7']
    fig_radar.add_trace(go.Scatterpolar(r=v_auto, theta=cats, fill='toself', name='Autovaloración', line_color='#3498db'))
    fig_radar.add_trace(go.Scatterpolar(r=v_ind, theta=cats, fill='toself', name='Ponderado Individual', line_color='#2ecc71'))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=450)
    st.plotly_chart(fig_radar, use_container_width=True)

with col_button:
    st.write("") # Espaciador
    st.write("") # Espaciador
    if st.button("✨ Generar Informe Ejecutivo con IA"):
        prompt = f"""
        Actúa como experto en Barrett. Analiza los resultados de {lider_sel}.
        DATOS JSON: {d.to_json()}
        INFORME: Resumen ejecutivo, Estilo predominante, Brechas Auto vs Indiv, Recomendaciones estratégicas para Confa.
        Escribe profesionalmente, español ejecutivo.
        """
        try:
            with st.spinner('Procesando análisis de alta gerencia...'):
                response = model.generate_content(prompt)
                st.markdown("### Informe Ejecutivo")
                st.write(response.text)
        except Exception as e:
            st.error(f"Error IA: {e}")
