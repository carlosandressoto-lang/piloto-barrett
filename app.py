import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide")

# Estilo para fondo oscuro con texto legible
st.markdown("""
<style>
    .main { background-color: #0e1117; color: white !important; font-family: 'Helvetica Neue', sans-serif; }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stSelectbox label { color: white !important; }
    .stSelectbox div[data-baseweb="select"] { color: white !important; background-color: #1e293b; }
    .block-container { padding-top: 1rem; }
    h1 { color: #BFDBFE !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN IA SEGURA ---
try:
    # Leemos la clave desde los Secrets de Streamlit
    api_key_segura = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key_segura)
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error("Error: No se encontró la API Key en los Secrets de Streamlit.")
    st.info("Configura 'GEMINI_API_KEY' en Settings > Secrets de tu App en Streamlit Cloud.")

# --- 3. CARGA DE DATOS ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('Resultados_Gerentes.csv', sep=';', decimal=',')
        df.columns = df.columns.str.strip()
        df['Nombre_Lider'] = df['Nombre_Lider'].astype(str).str.strip()
        cols_check = [c for c in df.columns if 'L' in c and any(x in c for x in ['AUTO', 'INDIV', 'ORG'])]
        for col in cols_check:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Error crítico de datos: {e}")
        return None

df = load_data()

if df is not None:
    # --- 4. SELECCIÓN ---
    st.title("🏛️ Índice del equilibrio - Dashboard LDR Barrett")
    lideres = sorted(df['Nombre_Lider'].unique())
    lider_sel = st.selectbox("Seleccione el líder para el análisis detallado:", lideres)
    d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

    # --- 5. BARRAS ORIGINALES (%) ---
    st.divider()
    st.subheader("Distribución de Energía por Niveles de Conciencia (%)")
    c1, c2, c3 = st.columns(3)

    def dibujar_barras(vals, titulo, color):
        labels = ['L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 'L4 - Facilitador', 'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis']
        v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
        fig = go.Figure(go.Bar(x=v_plot, y=labels, orientation='h', marker_color=color, text=[f"{round(v,1)}%" for v in v_plot], textposition='inside'))
        fig.update_layout(title=dict(text=titulo, font=dict(color='white')), xaxis_range=[0, 105], height=350, template="plotly_dark", margin=dict(l=0, r=10, t=40, b=20), yaxis=dict(autorange="reversed", tickfont=dict(color='white')), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        return fig

    v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
    v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
    v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]

    with c1: st.plotly_chart(dibujar_barras(v_auto, "Autovaloración", "#3498db"), use_container_width=True)
    with c2: st.plotly_chart(dibujar_barras(v_ind, "Individual (360)", "#2ecc71"), use_container_width=True)
    with c3: st.plotly_chart(dibujar_barras(v_org, "Organizacional (Cultura)", "#95a5a6"), use_container_width=True)

    # --- 6. RELOJES DE ARENA PREMIUM ---
    st.divider()
    st.subheader("⏳ Relojes de Arena (Nivel de Desarrollo 1 a 4)")

    def a_escala_4(v):
        if v < 65: return 1
        if v < 75: return 2
        if v < 85: return 3
        return 4

    def dibujar_reloj_hourglass_visible(vals, titulo):
        levels = ['L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 'L4 - Facilitador', 'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis']
        anchos_hourglass = [5, 4, 3, 2.2, 3, 4, 5] 
        colors_barrett = ["#6F42C1", "#6F42C1", "#6F42C1", "#28A745", "#FD7E14", "#FD7E14", "#FD7E14"]
        v_hourglass_v4 = [f"Nivel {a_escala_4(vals[i])}" for i in [6, 5, 4, 3, 2, 1, 0]]

        fig = go.Figure(go.Funnel(y=levels, x=anchos_hourglass, text=v_hourglass_v4, textinfo="text", textfont=dict(color='white', size=14, family='Arial Black'), marker={"color": colors_barrett, "line": {"width": 2, "color": "white"}}, connector={"line": {"color": "white", "width": 1}, "fillcolor": "rgba(200, 200, 200, 0.1)"}))
        fig.update_layout(title=dict(text=titulo, x=0.5, font=dict(color='white')), height=500, margin=dict(l=150, r=20, t=50, b=50), yaxis=dict(autorange="reversed", tickfont=dict(color='white')), xaxis=dict(visible=False), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        return fig

    r1, r2, r3 = st.columns(3)
    with r1: st.plotly_chart(dibujar_reloj_hourglass_visible(v_auto, "Autopercepción Barrett"), use_container_width=True)
    with r2: st.plotly_chart(dibujar_reloj_hourglass_visible(v_ind, "Competencia Individual"), use_container_width=True)
    with r3: st.plotly_chart(dibujar_reloj_hourglass_visible(v_org, "Cultura Organizacional"), use_container_width=True)

    # --- 7. RADAR E INFORME IA ---
    st.divider()
    col_radar, col_ia = st.columns([1.5, 1])
    with col_radar:
        st.subheader("Radar de Alineación Estratégica (%)")
        fig_radar = go.Figure()
        cats = ['L1','L2','L3','L4','L5','L6','L7']
        fig_radar.add_trace(go.Scatterpolar(r=v_auto, theta=cats, fill='toself', name='Auto', line_color='#3498db'))
        fig_radar.add_trace(go.Scatterpolar(r=v_ind, theta=cats, fill='toself', name='Individual', line_color='#2ecc71'))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(color='white')), angularaxis=dict(tickfont=dict(color='white'))), height=450, template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_radar, use_container_width=True)

    with col_ia:
        if st.button("✨ GENERAR INFORME EJECUTIVO"):
            prompt = f"Analiza los resultados 360 de {lider_sel} bajo el modelo Barrett: {d.to_json()}. Usa rúbrica 0-100."
            try:
                with st.spinner('Analizando...'):
                    response = model.generate_content(prompt)
                    st.markdown(f"### Informe Ejecutivo: {lider_sel}")
                    st.write(response.text)
            except Exception as e:
                st.error(f"Error IA: {e}")
