import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
from fpdf import FPDF
import io
import tempfile
import os
import re

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide")

st.markdown("""
<style>
    .main { font-family: 'Helvetica Neue', sans-serif; }
    h1 { color: #BFDBFE !important; text-align: center; }
    .titulo-col { text-align: center; font-weight: bold; margin-bottom: 10px; font-size: 1.1rem; }
    .leyenda-v3 { display: flex; flex-direction: column; justify-content: space-between; height: 340px; margin-top: 35px; padding-right: 10px; border-right: 1px solid #334155; }
    .item-ley { height: 48px; display: flex; align-items: center; justify-content: flex-end; font-size: 0.85rem; font-weight: bold; }
    .metric-box { background-color: rgba(30, 41, 59, 0.5); padding: 10px; border-radius: 10px; text-align: center; border: 1px solid #334155; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN IA SEGURA ---
try:
    api_key_segura = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key_segura)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error("Error: Configura 'GEMINI_API_KEY' en los Secrets.")

# --- 3. CARGA DE DATOS ---
@st.cache_data
def load_data():
    try:
        csv_url = st.secrets["GSHEET_URL"]
        df = pd.read_csv(csv_url, decimal=',')
        df.columns = df.columns.str.strip()
        df['Nombre_Lider'] = df['Nombre_Lider'].astype(str).str.strip()
        df = df[~df['Nombre_Lider'].isin(['0.0', 'nan', ''])]
        df = df.dropna(subset=['Nombre_Lider'])
        cols_to_fix = [c for c in df.columns if ('L' in c and any(x in c for x in ['AUTO', 'INDIV', 'ORG'])) or 'CANT_' in c or 'POT' in c or 'DES' == c]
        for col in cols_to_fix:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Error crítico al conectar con Google Sheets: {e}")
        return None

df = load_data()

# --- 4. LÓGICA NINEBOX ---
def obtener_cuadrante_confa(pot, des):
    if pot < 60: p_label = "BAJO"
    elif pot < 80: p_label = "MEDIO"
    else: p_label = "ALTO"
    if des <= 1: d_label = "BAJO"
    elif des <= 2: d_label = "MEDIO"
    else: d_label = "ALTO"
    mapping = {
        ("ALTO", "BAJO"): "ENIGMA DIAMANTE EN BRUTO", ("ALTO", "MEDIO"): "FUTURA ESTRELLA EN CRECIMIENTO", ("ALTO", "ALTO"): "FUTUROS LIDERES SUPERESTRELLAS",
        ("MEDIO", "BAJO"): "DILEMA", ("MEDIO", "MEDIO"): "EMPLEADOS CLAVES", ("MEDIO", "ALTO"): "FUTURAS ESTRELLAS",
        ("BAJO", "BAJO"): "ICEBERG", ("BAJO", "MEDIO"): "EFECTIVOS", ("BAJO", "ALTO"): "PROFESIONALES CONFIABLES"
    }
    return mapping.get((p_label, d_label), "No clasificado")

def escalar_visual_potencial(val):
    if val <= 60: return (val / 60) * 33.33
    elif val <= 80: return 33.33 + ((val - 60) / 20) * 33.33
    else: return 66.66 + ((val - 80) / 20) * 33.33

if df is not None:
    lideres = sorted(df['Nombre_Lider'].unique())
    lider_sel = st.selectbox("Seleccione el líder:", lideres)
    d = df[df['Nombre_Lider'] == lider_sel].iloc[0]
    
    v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
    v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
    v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]
    liderazgo_prom = (d.INDIV_L5 + d.INDIV_L6 + d.INDIV_L7) / 3
    transicion_prom = d.INDIV_L4
    gerencia_prom = (d.INDIV_L1 + d.INDIV_L2 + d.INDIV_L3) / 3

    # Funciones de estilo
    def obtener_color_desarrollo(v):
        if v < 65: return "#ff4b4b"
        if v < 75: return "#f1c40f"
        if v < 85: return "#2ecc71"
        return "rgb(33, 115, 182)"

    def obtener_etiqueta(v):
        if v < 65: return "Bajo"
        if v < 75: return "Medio"
        if v < 85: return "Alto"
        return "Superior"

    def generar_fig_barras(vals, titulo, color):
        labels = ['L7', 'L6', 'L5', 'L4', 'L3', 'L2', 'L1']
        v_plot = vals[::-1]
        fig = go.Figure(go.Bar(x=v_plot, y=labels, orientation='h', marker_color=color, text=[f"{v}%" for v in v_plot], textposition='inside'))
        fig.update_layout(title=titulo, xaxis_range=[0, 105], template="plotly_dark", height=350)
        return fig

    def generar_fig_reloj(vals, incluir_leyenda=False):
        anchos = [6, 5, 4, 3.2, 4, 5, 6]
        v_rev = vals[::-1]
        fig = go.Figure(go.Funnel(y=[1,2,3,4,5,6,7], x=anchos, textinfo="none", marker={"color": ["blue"]*3+["green"]+["orange"]*3}))
        for i, val in enumerate(v_rev):
            fig.add_annotation(x=0, y=i+1, text=obtener_etiqueta(val), showarrow=False, font=dict(color="white", size=12))
        fig.update_layout(height=400, showlegend=False, template="plotly_dark")
        return fig

    # --- NINEBOX DINÁMICA ---
    st.divider()
    cnb1, cnb2 = st.columns([2, 1])
    cuadrante = obtener_cuadrante_confa(d.IND_POT, d.DES)
    
    with cnb1:
        # Lógica de color dinámica por tema
        color_txt = "white" if st.get_option("theme.base") == "dark" else "black"
        
        fig_nb = go.Figure()
        cuadrantes = [
            (0.5, 1.5, 0, 33.33, "#440154", "ICEBERG"), (1.5, 2.5, 0, 33.33, "#482878", "EFECTIVOS"), (2.5, 3.5, 0, 33.33, "#3b528b", "PROF. CONFIABLES"),
            (0.5, 1.5, 33.33, 66.66, "#31688e", "DILEMA"), (1.5, 2.5, 33.33, 66.66, "#21918c", "EMP. CLAVE"), (2.5, 3.5, 33.33, 66.66, "#5ec962", "FUT. ESTRELLAS"),
            (0.5, 1.5, 66.66, 100, "#b5de2b", "ENIGMA"), (1.5, 2.5, 66.66, 100, "#fde725", "ESTRELLA CREC."), (2.5, 3.5, 66.66, 100, "#f89441", "SUPERESTRELLAS")
        ]
        for x0, x1, y0, y1, color, label in cuadrantes:
            fig_nb.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1, fillcolor=color, opacity=0.4)
            fig_nb.add_annotation(x=(x0+x1)/2, y=y1-2, text=label, showarrow=False, font=dict(color=color_txt, size=8))

        # Lógica de posición de etiqueta para que no tape líneas
        vp = d.IND_POT
        pos = "bottom center" if (55<=vp<=65 or 75<=vp<=85 or vp>=92) else "top center"

        fig_nb.add_trace(go.Scatter(
            x=[d.DES], y=[escalar_visual_potencial(d.IND_POT)],
            mode='markers+text',
            marker=dict(size=12, color='white', symbol='diamond', line=dict(width=2, color='black')),
            text=[f"<b>{lider_sel}</b><br>({round(d.IND_POT,2)}%)"],
            textposition=pos,
            textfont=dict(color=color_txt, size=10),
            hoverinfo="all",
            hovertemplate=f"Potencial: {d.IND_POT}%<br>Desempeño: {d.DES}<extra></extra>"
        ))
        fig_nb.update_layout(xaxis=dict(range=[0.5, 3.5]), yaxis=dict(range=[-5, 105]), template="plotly_dark" if color_txt=="white" else "plotly")
        st.plotly_chart(fig_nb, use_container_width=True)

    with cnb2:
        st.subheader(cuadrante)
        st.write(f"Potencial: {d.IND_POT}% | Desempeño: {d.DES}")

    # --- INFORME ---
    if st.button("🚀 GENERAR INFORME"):
        prompt = f"Actúa como consultor Barrett. Genera un reporte para {lider_sel}. DATOS: {d.to_json()}... (Prompts Barrett originales)"
        try:
            with st.spinner('Procesando...'):
                res = model.generate_content(prompt)
                st.session_state.informe = res.text
                st.write(res.text)
        except Exception as e: st.error(e)

    if "informe" in st.session_state:
        if st.button("📄 PDF"):
            try:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.cell(200, 10, txt="REPORTE ESTRATÉGICO", ln=1, align="C")
                pdf.multi_cell(0, 10, st.session_state.informe.encode('latin-1', 'replace').decode('latin-1'))
                st.download_button("Descargar", pdf.output(dest='S'), "reporte.pdf", "application/pdf")
            except Exception as e: st.error(f"Error PDF: {e}")
