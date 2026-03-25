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

# --- 2. CONEXIÓN IA ---
try:
    api_key_segura = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key_segura)
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error("Error de API KEY.")

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
        ("ALTO", "BAJO"): "ENIGMA: DIAMANTE EN BRUTO", ("ALTO", "MEDIO"): "FUTURA ESTRELLA EN CRECIMIENTO", ("ALTO", "ALTO"): "FUTUROS LIDERES: SUPERESTRELLAS",
        ("MEDIO", "BAJO"): "DILEMA", ("MEDIO", "MEDIO"): "EMPLEADOS CLAVE", ("MEDIO", "ALTO"): "FUTURAS ESTRELLAS",
        ("BAJO", "BAJO"): "ICEBERG", ("BAJO", "MEDIO"): "EFECTIVOS", ("BAJO", "ALTO"): "PROFESIONALES CONFIABLES"
    }
    return mapping.get((p_label, d_label), "No clasificado")

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
    fig.update_layout(title=dict(text=titulo, x=0.5), xaxis_range=[0, 105], template="plotly_dark", height=350, yaxis=dict(autorange="reversed"))
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

    v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
    v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
    v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]
    liderazgo_prom = (d.INDIV_L5 + d.INDIV_L6 + d.INDIV_L7) / 3
    transicion_prom = d.INDIV_L4
    gerencia_prom = (d.INDIV_L1 + d.INDIV_L2 + d.INDIV_L3) / 3

    # (Lógica Web omitida para ir directo al PDF corregido)
    st.divider()
    if st.button("🚀 GENERAR INFORME"):
        # Prompt Original de 5 puntos aquí...
        pass

    if st.button("📄 DESCARGAR PDF"):
        try:
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            with tempfile.TemporaryDirectory() as tmp_dir:
                def save_pdf_chart_final(fig, name, title="", l_marg=10):
                    fig.update_layout(template="plotly", paper_bgcolor='white', plot_bgcolor='white', font=dict(color='black'), title=dict(text=title, x=0.5, font=dict(size=14), y=0.95), margin=dict(t=60, b=20, l=l_marg, r=10))
                    path = os.path.join(tmp_dir, name)
                    fig.write_image(path, engine="kaleido", scale=2)
                    return path

                # --- PÁGINA 1: DASHBOARD COMPACTO ---
                pdf.add_page()
                pdf.set_font('Helvetica', 'B', 16); pdf.cell(0, 10, 'REPORTE ESTRATÉGICO INTEGRAL', ln=True, align='C')
                pdf.set_font('Helvetica', 'B', 10); pdf.cell(0, 8, f'Evaluado: {lider_sel} | Evaluadores: {int(d.CANT_EVAL)}', ln=True, align='C')
                
                # 1. Frecuencia
                pdf.ln(2); pdf.set_font('Helvetica', 'B', 11); pdf.cell(0, 10, '1. Frecuencia de comportamientos por niveles (%)', ln=True)
                img_b1 = save_pdf_chart_final(generar_fig_barras(v_auto, "", "#3498db"), "b1.png", title="Autovaloración")
                img_b2 = save_pdf_chart_final(generar_fig_barras(v_ind, "", "#2ecc71"), "b2.png", title="Individual")
                img_b3 = save_pdf_chart_final(generar_fig_barras(v_org, "", "#e74c3c"), "b3.png", title="Org")
                y_frec = pdf.get_y(); pdf.image(img_b1, x=10, y=y_frec, w=60); pdf.image(img_b2, x=75, y=y_frec, w=60); pdf.image(img_b3, x=140, y=y_frec, w=60)
                
                # 2. Radar y Equilibrio
                pdf.set_y(y_frec + 43); pdf.set_font('Helvetica', 'B', 11); pdf.cell(0, 10, '2. Alineación de Consciencia e Índice de Equilibrio', ln=True)
                # Radar se guarda normal, Índice de equilibrio se dibuja
                img_radar = save_pdf_chart_final(generar_fig_barras(v_ind, "", "#2ecc71"), "radar_temp.png") # Ejemplo
                y_radar = pdf.get_y(); pdf.image(img_radar, x=10, y=y_radar, w=95)
                
                # 3. RELOJES (ESTRATEGIA NATIVA: ADIÓS AL DESFASE)
                pdf.set_y(y_radar + 63); pdf.set_font('Helvetica', 'B', 11); pdf.cell(0, 10, '3. Niveles de Madurez Barrett (Relojes)', ln=True)
                
                # LA CLAVE: El primero lleva leyenda nativa (l_marg=80), los otros no (l_marg=10)
                img_r1 = save_pdf_chart_final(generar_fig_reloj(v_auto, incluir_leyenda=True), "r1p.png", title="Auto", l_marg=80)
                img_r2 = save_pdf_chart_final(generar_fig_reloj(v_ind, incluir_leyenda=False), "r2p.png", title="Indiv", l_marg=10)
                img_r3 = save_pdf_chart_final(generar_fig_reloj(v_org, incluir_leyenda=False), "r3p.png", title="Org", l_marg=10)
                
                y_reloj = pdf.get_y()
                # Relación matemática para que los triángulos midan lo mismo: w=68 para el que tiene texto, w=50 para los limpios.
                pdf.image(img_r1, x=10, y=y_reloj, w=68)
                pdf.image(img_r2, x=82, y=y_reloj, w=50)
                pdf.image(img_r3, x=137, y=y_reloj, w=50)

                # --- PÁGINA 2: ESTRATEGIA Y ANÁLISIS ---
                pdf.add_page()
                # ... (Resto del código de NineBox y Análisis IA)

            st.download_button("📥 Guardar PDF Final Corregido", data=bytes(pdf.output()), file_name=f"Reporte_{lider_sel}.pdf")
        except Exception as e: st.error(f"Error: {e}")
