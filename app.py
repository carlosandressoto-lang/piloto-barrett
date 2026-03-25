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
    h1 { color: #BFDBFE !important; text-align: center; }
    .titulo-col { text-align: center; font-weight: bold; margin-bottom: 10px; font-size: 1.1rem; color: #000000; background-color: #f8fafc; padding: 5px; border-radius: 5px; }
    .metric-box { background-color: #ffffff; padding: 15px; border-radius: 10px; text-align: left; border: 2px solid #334155; color: #000000; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); }
    .leyenda-v3 { display: flex; flex-direction: column; justify-content: space-between; height: 340px; margin-top: 35px; padding-right: 10px; border-right: 2px solid #334155; }
    .item-ley { height: 48px; display: flex; align-items: center; justify-content: flex-end; font-size: 0.85rem; font-weight: bold; color: #000000; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN IA ---
try:
    api_key_segura = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key_segura)
    model = genai.GenerativeModel('gemini-2.5-flash')
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

# --- 4. LÓGICA VISUAL ---
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
    fig = go.Figure(go.Bar(x=v_plot, y=labels, orientation='h', marker_color=color, text=[f"{round(v,1)}%" for v in v_plot], textposition='inside'))
    fig.update_layout(title=dict(text=titulo, x=0.5, font=dict(color='black')), xaxis_range=[0, 105], height=350, template="plotly_white", margin=dict(l=10, r=10, t=40, b=20), yaxis=dict(autorange="reversed"))
    return fig

def generar_fig_reloj(vals, incluir_leyenda=False):
    anchos_base = [6, 5, 4, 3.2, 4, 5, 6] 
    v_rev = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
    colors_barrett = ["rgb(33,115,182)"]*3 + ["rgb(140,183,42)"] + ["rgb(241,102,35)"]*3
    labels_niveles = ["L7-Visionario", "L6-Mentor", "L5-Auténtico", "L4-Facilitador", "L3-Desempeño", "L2-Relaciones", "L1-Crisis"]
    fig = go.Figure()
    fig.add_trace(go.Funnel(y=labels_niveles if incluir_leyenda else [1,2,3,4,5,6,7], x=anchos_base, textinfo="none", hoverinfo="none", marker={"color": colors_barrett, "line": {"width": 1, "color": "black"}}, connector={"visible": False}))
    for i, (val, ancho) in enumerate(zip(v_rev, anchos_base)):
        fig.add_annotation(x=0, y=i if incluir_leyenda else i+1, text=obtener_etiqueta(val), showarrow=False, font=dict(color=obtener_color_desarrollo(val), size=12, family='Arial Black'), bgcolor="white", borderpad=4, width=ancho * 22.0)
    fig.update_layout(height=400, margin=dict(l=100 if incluir_leyenda else 10, r=20, t=10, b=10), yaxis=dict(visible=incluir_leyenda, tickfont=dict(size=10, color='black')), xaxis=dict(visible=False), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
    return fig

# --- 5. RENDERIZADO ---
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

    st.subheader("📊 Frecuencia de comportamientos por niveles (%)")
    c1, c2, c3 = st.columns(3)
    with c1: st.plotly_chart(generar_fig_barras(v_auto, "Autovaloración", "#3498db"), use_container_width=True)
    with c2: st.plotly_chart(generar_fig_barras(v_ind, "Ponderado Individual", "#2ecc71"), use_container_width=True)
    with c3: st.plotly_chart(generar_fig_barras(v_org, "Ponderado Organizacional", "#e74c3c"), use_container_width=True)

    st.divider()
    cl, cr1, cr2, cr3 = st.columns([1.2, 1, 1, 1])
    with cl:
        st.markdown('<div class="titulo-col">Nivel Barrett</div>', unsafe_allow_html=True)
        niveles_barrett = ["L7-Visionario", "L6-Mentor", "L5-Auténtico", "L4-Facilitador", "L3-Desempeño", "L2-Relaciones", "L1-Crisis"]
        st.markdown('<div class="leyenda-v3">' + ''.join([f'<div class="item-ley">{n}</div>' for n in niveles_barrett]) + '</div>', unsafe_allow_html=True)
    with cr1: st.markdown('<div class="titulo-col">Autovaloración</div>', unsafe_allow_html=True); st.plotly_chart(generar_fig_reloj(v_auto), key="r1")
    with cr2: st.markdown('<div class="titulo-col">Ponderado Individual</div>', unsafe_allow_html=True); st.plotly_chart(generar_fig_reloj(v_ind), key="r2")
    with cr3: st.markdown('<div class="titulo-col">Ponderado Organizacional</div>', unsafe_allow_html=True); st.plotly_chart(generar_fig_reloj(v_org), key="r3")

    st.divider()
    col_radar, col_dim = st.columns([1.5, 1])
    with col_radar:
        st.subheader("🎯 Alineación de Consciencia")
        fig_radar = go.Figure()
        cats = ['L1','L2','L3','L4','L5','L6','L7']
        for val, name, color in zip([v_auto, v_ind, v_org], ['Auto', 'Individual', 'Organizacional'], ['#3498db', '#2ecc71', '#e74c3c']):
            fig_radar.add_trace(go.Scatterpolar(r=val, theta=cats, fill='toself', name=name, line_color=color))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(color='black'))), height=500, template="plotly_white")
        st.plotly_chart(fig_radar, use_container_width=True)
    with col_dim:
        st.subheader("⚖️ Índice de Equilibrio")
        vals_dim = [liderazgo_prom, transicion_prom, gerencia_prom]
        fig_dim = go.Figure(go.Bar(x=vals_dim, y=['Liderazgo', 'Transición', 'Gerencia'], orientation='h', marker_color=[obtener_color_desarrollo(v) for v in vals_dim], text=[f"{round(v,1)}%" for v in vals_dim], textposition='inside'))
        fig_dim.update_layout(xaxis_range=[0, 105], height=400, template="plotly_white", yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_dim, use_container_width=True)

    # --- NINEBOX INTEGRAL ---
    st.divider()
    st.subheader("🟦 Mapa de Talento NineBox Confa")
    cnb1, cnb2 = st.columns([1.5, 1])
    cuadrante = obtener_cuadrante_confa(d.IND_POT, d.DES)
    
    with cnb1:
        fig_nb = go.Figure()
        cuadrantes = [
            (0.5, 1.5, 0, 33.33, "#440154", "ICEBERG"), (1.5, 2.5, 0, 33.33, "#482878", "EFECTIVOS"), (2.5, 3.5, 0, 33.33, "#3b528b", "PROF. CONFIABLES"),
            (0.5, 1.5, 33.33, 66.66, "#31688e", "DILEMA"), (1.5, 2.5, 33.33, 66.66, "#21918c", "EMP. CLAVE"), (2.5, 3.5, 33.33, 66.66, "#5ec962", "FUT. ESTRELLAS"),
            (0.5, 1.5, 66.66, 100, "#b5de2b", "ENIGMA"), (1.5, 2.5, 66.66, 100, "#fde725", "ESTRELLA CREC."), (2.5, 3.5, 66.66, 100, "#f89441", "SUPERESTRELLAS")
        ]
        for x0, x1, y0, y1, color, label in cuadrantes:
            fig_nb.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1, fillcolor=color, opacity=0.8, line=dict(color="white", width=1))
            fig_nb.add_annotation(x=(x0+x1)/2, y=y1-3, text=f"<b>{label}</b>", showarrow=False, font=dict(size=10, color="white"))

        fig_nb.add_trace(go.Scatter(
            x=[d.DES], y=[escalar_visual_potencial(d.IND_POT)], mode='markers',
            marker=dict(size=20, color='white', symbol='diamond', line=dict(width=3, color='black')), 
            hoverinfo="text", text=f"Potencial: {round(d.IND_POT,2)}% | Desempeño: {d.DES}"
        ))
        fig_nb.update_layout(
            xaxis=dict(title="Desempeño (1-3)", tickvals=[1,2,3], range=[0.4, 3.6], color="black"), 
            yaxis=dict(title="Potencial (%)", tickvals=[0, 33.33, 66.66, 100], ticktext=["0", "60", "80", "100"], range=[-5, 105], color="black"),
            template="plotly_white", height=500, margin=dict(l=60, r=30, t=30, b=60)
        )
        st.plotly_chart(fig_nb, use_container_width=True)

    with cnb2:
        st.markdown(f"""
        <div class="metric-box">
            <h3 style="color:#1e293b; margin:0; font-size:1.4rem;">{cuadrante}</h3>
            <hr style="border:1px solid #e2e8f0; margin: 15px 0;">
            <p><b>Potencial Individual:</b> {round(d.IND_POT,2)}%</p>
            <p><b>Desempeño:</b> {d.DES}</p>
            <p><b>Autoevaluación Potencial:</b> {round(d.AUTO_POT,2)}%</p>
            <br>
            <p style="font-size:0.8rem; color: #64748b;">Análisis estratégico basado en Talent Confa 2026.</p>
        </div>
        """, unsafe_allow_html=True)

    # --- INFORME ---
    st.divider()
    if st.button("🚀 GENERAR INFORME"):
        prompt = f"Consultor Barrett. Genera un reporte para {lider_sel} basado en: {d.to_json()}... (Prompt original de 5 puntos)"
        try:
            with st.spinner('Procesando análisis...'):
                res = model.generate_content(prompt)
                st.session_state.informe_cache[lider_sel] = res.text
                st.write(res.text)
        except Exception as e: st.error(e)

    if lider_sel in st.session_state.informe_cache:
        if st.button("📄 DESCARGAR PDF HD"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font('Helvetica', 'B', 16)
            pdf.cell(0, 10, 'REPORTE ESTRATEGICO INTEGRAL', ln=True, align='C')
            with tempfile.TemporaryDirectory() as tmp_dir:
                nb_path = os.path.join(tmp_dir, "nb.png")
                fig_nb.write_image(nb_path, engine="kaleido", scale=4)
                pdf.image(nb_path, x=15, w=180)
                pdf.add_page()
                pdf.set_font('Helvetica', '', 10)
                limpio = st.session_state.informe_cache[lider_sel].replace("**", "").encode('latin-1', 'replace').decode('latin-1')
                pdf.multi_cell(0, 6, limpio)
            st.download_button("Guardar PDF", pdf.output(dest='S'), f"Reporte_{lider_sel}.pdf", "application/pdf")
