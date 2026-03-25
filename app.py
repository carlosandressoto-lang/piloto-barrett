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

if "informe_cache" not in st.session_state:
    st.session_state.informe_cache = {}

st.markdown("""
<style>
    .main { font-family: 'Helvetica Neue', sans-serif; }
    .titulo-seccion { font-weight: bold; margin-bottom: 10px; font-size: 1.1rem; text-align: center; }
    .metric-box { 
        background-color: rgba(30, 41, 59, 0.05); 
        padding: 15px; 
        border-radius: 10px; 
        text-align: left; 
        border: 1px solid rgba(128, 128, 128, 0.3); 
    }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN IA SEGURA ---
try:
    api_key_segura = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key_segura)
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error("Error: Configure su API KEY en los Secrets.")

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
        st.error(f"Error crítico: {e}")
        return None

df = load_data()

# --- 4. LÓGICAS VISUALES ---
def obtener_cuadrante_confa(pot, des):
    if pot < 60: p_label = "BAJO"
    elif pot < 80: p_label = "MEDIO"
    else: p_label = "ALTO"
    if des <= 1: d_label = "BAJO"
    elif des <= 2: d_label = "MEDIO"
    else: d_label = "ALTO"
    mapping = {
        ("ALTO", "BAJO"): "ENIGMA: Diamante en bruto", ("ALTO", "MEDIO"): "FUTURA ESTRELLA EN CRECIMIENTO", ("ALTO", "ALTO"): "FUTUROS LIDERES: Superestrellas",
        ("MEDIO", "BAJO"): "DILEMA", ("MEDIO", "MEDIO"): "EMPLEADOS CLAVE", ("MEDIO", "ALTO"): "FUTURAS ESTRELLAS",
        ("BAJO", "BAJO"): "ICEBERG", ("BAJO", "MEDIO"): "EFECTIVOS", ("BAJO", "ALTO"): "PROFESIONALES CONFIABLES"
    }
    return mapping.get((p_label, d_label), "No clasificado")

def escalar_visual_potencial(val):
    if val <= 60: return (val / 60) * 33.33
    elif val <= 80: return 33.33 + ((val - 60) / 20) * 33.33
    else: return 66.66 + ((val - 80) / 20) * 33.33

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
    labels = ['L7-Visionario', 'L6-Mentor', 'L5-Auténtico', 'L4-Facilitador', 'L3-Desempeño', 'L2-Relaciones', 'L1-Crisis']
    v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
    fig = go.Figure(go.Bar(x=v_plot, y=labels, orientation='h', marker_color=color, text=[f"{round(v,1)}%" for v in v_plot], textposition='inside', insidetextfont=dict(color='white')))
    fig.update_layout(title=dict(text=titulo, x=0.5), xaxis_range=[0, 105], template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=10, t=40, b=20), height=350, yaxis=dict(autorange="reversed"))
    return fig

def generar_fig_reloj(vals, incluir_leyenda=False):
    anchos_base = [6, 5, 4, 3.2, 4, 5, 6] 
    v_rev = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
    colors_barrett = ["rgb(33,115,182)"]*3 + ["rgb(140,183,42)"] + ["rgb(241,102,35)"]*3
    labels_niveles = ["L7-Visionario", "L6-Mentor", "L5-Auténtico", "L4-Facilitador", "L3-Desempeño", "L2-Relaciones", "L1-Crisis"]
    fig = go.Figure()
    fig.add_trace(go.Funnel(y=labels_niveles if incluir_leyenda else [1,2,3,4,5,6,7], x=anchos_base, textinfo="none", hoverinfo="none", marker={"color": colors_barrett, "line": {"width": 1, "color": "white"}}, connector={"visible": False}))
    for i, (val, ancho) in enumerate(zip(v_rev, anchos_base)):
        fig.add_annotation(x=0, y=i if incluir_leyenda else i+1, text=obtener_etiqueta(val), showarrow=False, font=dict(color=obtener_color_desarrollo(val), size=11, family='Arial Black'), bgcolor="white", borderpad=4, width=ancho * 22.0)
    fig.update_layout(height=400, margin=dict(l=100 if incluir_leyenda else 10, r=10, t=10, b=10), xaxis=dict(visible=False), yaxis=dict(visible=incluir_leyenda), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', template="plotly_dark")
    return fig

# --- 5. RENDERIZADO PRINCIPAL ---
if df is not None:
    lideres = sorted(df['Nombre_Lider'].unique())
    lider_sel = st.selectbox("Seleccione el líder:", lideres)
    d = df[df['Nombre_Lider'] == lider_sel].iloc[0]
    es_gerencia = lider_sel.startswith("GER_")

    v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
    v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
    v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]
    liderazgo_prom = (d.INDIV_L5 + d.INDIV_L6 + d.INDIV_L7) / 3
    transicion_prom = d.INDIV_L4
    gerencia_prom = (d.INDIV_L1 + d.INDIV_L2 + d.INDIV_L3) / 3

    # DASHBOARD WEB (Omitido visual por brevedad, se asume igual)

    # BLOQUE 5: INFORME IA
    st.divider()
    if st.button("🚀 GENERAR INFORME"):
        if es_gerencia:
            contexto_ger = "ADAPTACIÓN GERENCIA: El evaluado es una GERENCIA. Habla de 'Capacidad instalada del talento' y 'Cultura grupal'."
        else:
            contexto_ger = "Evaluado: Líder Individual."

        prompt_maestro = f"""Actúa como consultor senior de Barrett. Genera reporte para {lider_sel}. DATOS: {d.to_json()}. {contexto_ger} 
        REGLAS: Sin anglicismos, feedback apreciativo, 5 puntos obligatorios. (Prompt Maestro Original Completo)"""
        try:
            with st.spinner('Analizando...'):
                res = model.generate_content(prompt_maestro)
                st.session_state.informe_cache[lider_sel] = res.text
                st.write(res.text)
        except Exception as e: st.error(e)

    # --- REPORTE PDF (SOLUCIÓN DE CLONES Y SYNTAX FIX) ---
    if lider_sel in st.session_state.informe_cache:
        if st.button("📄 DESCARGAR REPORTE PDF"):
            try:
                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                with tempfile.TemporaryDirectory() as tmp_dir:
                    def save_pdf_clones(fig, name, title=""):
                        fig.update_layout(template="plotly", paper_bgcolor='white', plot_bgcolor='white', font=dict(color='black'), title=dict(text=title, x=0.5, font=dict(size=14), y=0.95), margin=dict(t=60, b=40, l=60, r=20), autosize=False, width=500, height=350)
                        path = os.path.join(tmp_dir, name)
                        fig.write_image(path, engine="kaleido", scale=2)
                        return path

                    pdf.add_page()
                    pdf.set_font('Helvetica', 'B', 16); pdf.cell(0, 10, 'REPORTE ESTRATEGICO INTEGRAL', ln=True, align='C')
                    
                    # 1. BARRAS (CLONES)
                    pdf.set_font('Helvetica', 'B', 11); pdf.cell(0, 10, '1. Frecuencia de comportamientos por niveles (%)', ln=True)
                    img_b1 = save_pdf_clones(generar_fig_barras(v_auto, "", "#3498db"), "b1.png", title="Autovaloracion")
                    img_b2 = save_pdf_clones(generar_fig_barras(v_ind, "", "#2ecc71"), "b2.png", title="Individual")
                    img_b3 = save_pdf_clones(generar_fig_barras(v_org, "", "#e74c3c"), "b3.png", title="Org")
                    y_barras = pdf.get_y()
                    pdf.image(img_b1, x=10, y=y_barras, w=60); pdf.image(img_b2, x=75, y=y_barras, w=60); pdf.image(img_b3, x=140, y=y_barras, w=60)
                    
                    # 2. RADAR
                    pdf.ln(45); pdf.set_font('Helvetica', 'B', 11); pdf.cell(0, 10, '2. Alineacion de Consciencia', ln=True)
                    fig_radar.update_layout(template="plotly", paper_bgcolor='white', plot_bgcolor='white', font=dict(color='black'))
                    img_radar_path = os.path.join(tmp_dir, "radar.png"); fig_radar.write_image(img_radar_path, engine="kaleido", scale=2); pdf.image(img_radar_path, x=50, w=110)

                    # 3. RELOJES (CLONES)
                    pdf.add_page(); pdf.set_font('Helvetica', 'B', 11); pdf.cell(0, 10, '3. Niveles de Madurez Barrett (Relojes)', ln=True)
                    img_r1 = save_pdf_clones(generar_fig_reloj(v_auto, False), "r1.png", title="Auto")
                    img_r2 = save_pdf_clones(generar_fig_reloj(v_ind, False), "r2.png", title="Indiv")
                    img_r3 = save_pdf_clones(generar_fig_reloj(v_org, False), "r3.png", title="Org")
                    y_relojes = pdf.get_y()
                    pdf.image(img_r1, x=35, y=y_relojes, w=53); pdf.image(img_r2, x=88, y=y_relojes, w=53); pdf.image(img_r3, x=141, y=y_relojes, w=53)
                    
                    # LEYENDA MANUAL
                    pdf.set_font('Helvetica', '', 8); pdf.set_text_color(100, 100, 100)
                    niveles = ["L7-Visionario", "L6-Mentor", "L5-Autentico", "L4-Facilitador", "L3-Desempeno", "L2-Relaciones", "L1-Crisis"]
                    for i, txt in enumerate(niveles): pdf.text(10, y_relojes + 16 + (i * 5.15), txt)
                    pdf.set_text_color(0, 0, 0)

                    # PÁGINA FINAL: NineBox y Texto
                    pdf.add_page(); pdf.set_font('Helvetica', 'B', 11); pdf.cell(0, 10, '4. Mapa NineBox y Analisis', ln=True)
                    fig_nb.update_layout(template="plotly", paper_bgcolor='white', plot_bgcolor='white', font=dict(color='black'))
                    img_nb = os.path.join(tmp_dir, "nb.png"); fig_nb.write_image(img_nb, scale=4); pdf.image(img_nb, x=25, w=160)
                    pdf.ln(5); pdf.set_font('Helvetica', '', 10)
                    limpio = st.session_state.informe_cache[lider_sel].replace("**", "").encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(0, 6, limpio)

                st.download_button("📥 Guardar PDF", data=bytes(pdf.output()), file_name=f"Reporte_{lider_sel}.pdf", mime="application/pdf")
            except Exception as e: st.error(f"Error PDF: {e}")
