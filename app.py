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
    .leyenda-v3 { display: flex; flex-direction: column; justify-content: space-between; height: 340px; margin-top: 35px; padding-right: 10px; border-right: 1px solid rgba(128, 128, 128, 0.3); }
    .item-ley { height: 48px; display: flex; align-items: center; justify-content: flex-end; font-size: 0.85rem; font-weight: bold; }
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

    st.subheader("👥 Información de la Evaluación")
    c_ev1, c_ev2 = st.columns([1, 2])
    with c_ev1: st.metric("Total Evaluadores", int(d.CANT_EVAL))
    with c_ev2: st.write(f"**Auto:** {int(d.CANT_AUTO)} | **Jefe:** {int(d.CANT_JEFE)} | **Pares:** {int(d.CANT_PAR)} | **Colab:** {int(d.CANT_COL)}")

    v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
    v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
    v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]
    liderazgo_prom = (d.INDIV_L5 + d.INDIV_L6 + d.INDIV_L7) / 3
    transicion_prom = d.INDIV_L4
    gerencia_prom = (d.INDIV_L1 + d.INDIV_L2 + d.INDIV_L3) / 3

    # DASHBOARD WEB
    st.subheader("📊 Frecuencia de comportamientos por niveles (%)")
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown("<div class='titulo-seccion'>Autovaloración</div>", unsafe_allow_html=True); st.plotly_chart(generar_fig_barras(v_auto, "", "#3498db"), use_container_width=True)
    with c2: st.markdown("<div class='titulo-seccion'>Ponderado Individual</div>", unsafe_allow_html=True); st.plotly_chart(generar_fig_barras(v_ind, "", "#2ecc71"), use_container_width=True)
    with c3: st.markdown("<div class='titulo-seccion'>Ponderado Organizacional</div>", unsafe_allow_html=True); st.plotly_chart(generar_fig_barras(v_org, "", "#e74c3c"), use_container_width=True)

    st.divider()
    st.subheader("⏳ Resultados Evaluación 360° (Niveles Barrett)")
    cl, cr1, cr2, cr3 = st.columns([1.2, 1, 1, 1])
    with cl:
        st.markdown("<div class='titulo-seccion'>Nivel Barrett</div>", unsafe_allow_html=True)
        niv_labels = ["L7-Visionario", "L6-Mentor", "L5-Auténtico", "L4-Facilitador", "L3-Desempeño", "L2-Relaciones", "L1-Crisis"]
        st.markdown('<div class="leyenda-v3">' + ''.join([f'<div class="item-ley">{n}</div>' for n in niv_labels]) + '</div>', unsafe_allow_html=True)
    with cr1: st.plotly_chart(generar_fig_reloj(v_auto), key="r1", use_container_width=True)
    with cr2: st.plotly_chart(generar_fig_reloj(v_ind), key="r2", use_container_width=True)
    with cr3: st.plotly_chart(generar_fig_reloj(v_org), key="r3", use_container_width=True)

    st.divider()
    col_radar, col_dim = st.columns([1.5, 1])
    with col_radar:
        st.subheader("🎯 Alineación de Consciencia")
        fig_radar = go.Figure()
        cats = ['L1','L2','L3','L4','L5','L6','L7']
        for val, name, color in zip([v_auto, v_ind, v_org], ['Auto', 'Individual', 'Org'], ['#3498db', '#2ecc71', '#e74c3c']):
            fig_radar.add_trace(go.Scatterpolar(r=val, theta=cats, fill='toself', name=name, line_color=color))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), template="plotly_dark", height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_radar, use_container_width=True)
    with col_dim:
        st.subheader("⚖️ Índice de Equilibrio")
        v_dim = [liderazgo_prom, transicion_prom, gerencia_prom]
        fig_dim = go.Figure(go.Bar(x=v_dim, y=['Liderazgo', 'Transición', 'Gerencia'], orientation='h', marker_color='#3498db', text=[f"{round(v,1)}%" for v in v_dim], textposition='inside'))
        fig_dim.update_layout(xaxis_range=[0, 105], height=400, template="plotly_dark", yaxis=dict(autorange="reversed"), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_dim, use_container_width=True)

    st.divider()
    st.subheader("🟦 Mapa de Talento NineBox Confa")
    cnb1, cnb2 = st.columns([1.5, 1])
    cuadrante = obtener_cuadrante_confa(d.IND_POT, d.DES)
    with cnb1:
        fig_nb = go.Figure()
        quads = [(0.5, 1.5, 0, 33.33, "#440154", "ICEBERG"), (1.5, 2.5, 0, 33.33, "#482878", "EFECTIVOS"), (2.5, 3.5, 0, 33.33, "#3b528b", "PROF. CONFIABLES"), (0.5, 1.5, 33.33, 66.66, "#31688e", "DILEMA"), (1.5, 2.5, 33.33, 66.66, "#21918c", "EMPLEADOS CLAVE"), (2.5, 3.5, 33.33, 66.66, "#5ec962", "FUTURAS ESTRELLAS"), (0.5, 1.5, 66.66, 100, "#b5de2b", "ENIGMA"), (1.5, 2.5, 66.66, 100, "#fde725", "ESTRELLA CREC."), (2.5, 3.5, 66.66, 100, "#f89441", "SUPERESTRELLAS")]
        for x0, x1, y0, y1, color, label in quads:
            fig_nb.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1, fillcolor=color, opacity=0.75, line=dict(color="rgba(255,255,255,0.3)", width=1))
            fig_nb.add_annotation(x=(x0+x1)/2, y=y1-2.5, text=f"<b>{label}</b>", showarrow=False, font=dict(size=9, color="white"))
        fig_nb.add_trace(go.Scatter(x=[d.DES], y=[d.IND_POT], mode='markers', marker=dict(size=14, color='red', symbol='diamond', line=dict(width=2, color='white'))))
        fig_nb.update_layout(xaxis=dict(title="Desempeño", tickvals=[1,2,3], range=[0.4, 3.6]), yaxis=dict(title="Potencial (%)", range=[-5, 105]), template="plotly_dark", height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_nb, use_container_width=True)
    with cnb2:
        st.markdown(f"<div class='metric-box'><h3>{cuadrante}</h3><hr><p><b>Potencial Individual:</b> {round(d.IND_POT,2)}%</p><p><b>Desempeño:</b> {d.DES}</p><p><b>Autoevaluación Potencial:</b> {round(d.AUTO_POT,2)}%</p></div>", unsafe_allow_html=True)

    # BLOQUE 5: INFORME (PROMPT MAESTRO)
    st.divider()
    if st.button("🚀 GENERAR INFORME"):
        if es_gerencia:
            contexto_ger = "ADAPTACIÓN GERENCIA: El evaluado es una GERENCIA. No hables de retroalimentación personal ni sucesiones individuales. Habla de 'Capacidad instalada del talento', 'Cultura de resultados grupal' y 'Estrategia de retención del talento del área'."
        else:
            contexto_ger = "Evaluado: Líder Individual."

        prompt_maestro = f"""Actúa como consultor senior de DESARROLLO DE LIDERAZGO Barrett. Genera un reporte para {lider_sel}. DATOS: {d.to_json()} donde AUTO es Autoevaluación, INDI es Ponderado Individual, ORG es Ponderado organizacional (Promedio de resultados organizacionales) y CANT es cantidad de respuestas o evaluadores. Si alguien tiene todo 0 en AUTO es porque no hizo Autoevaluacion para que lo tengas presente en la comparativa. Si ves que sus resultados INDI son muy bajos, revisa que al menos CANT_JEFE y CANT_PAR sean mínimo 1, si no ahí esta el error y dejaremos en el reporte ese hallazgo de forma obligatoria pues seria un sesgo matemático. Si no encontramos esas inconsistencias no mencionaremos por nada del mundo esta información en el resto del informe, si y solo si se cumplen una de esas restricciones.
        {contexto_ger}
        PROHIBIDO USAR ANGLICISMOS. REDACTA TODO EN ESPAÑOL PURO.
        CONTEXTO BARRETT: L1-Crisis, L2-Relaciones, L3-Desempeño, L4-Facilitador, L5-Integrador, L6-Mentor, L7-Visionario.
        CONTEXTO NINEBOX CONFA: Usa las 9 definiciones de CONFA 2018 para el análisis técnico.
        REGLAS DE ORO: FEEDBACK APRECIATIVO. RÚBRICA: Bajo (<65), Medio (65-75), Alto (75-85), Superior (>85).
        ESTRUCTURA OBLIGATORIA: 1. DESCRIPCIÓN POR NIVELES. 2. ANÁLISIS DE AUTOVALORACIÓN. 3. MATRIZ DE MADUREZ. 4. PERFIL DE LIDERAZGO. 5. POSICIONAMIENTO ESTRATÉGICO DE TALENTO ({cuadrante}).
        """
        try:
            with st.spinner('Analizando...'):
                res = model.generate_content(prompt_maestro)
                st.session_state.informe_cache[lider_sel] = res.text
                st.write(res.text)
        except Exception as e: st.error(e)

    # --- REPORTE PDF (UNIFICADO Y SIN SOLAPAMIENTO) ---
    if lider_sel in st.session_state.informe_cache:
        if st.button("📄 DESCARGAR PDF"):
            try:
                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                with tempfile.TemporaryDirectory() as tmp_dir:
                    def save_pdf_chart_final(fig, name, title=""):
                        fig.update_layout(template="plotly", paper_bgcolor='white', plot_bgcolor='white', font=dict(color='black'), title=dict(text=title, x=0.5, font=dict(size=14), y=0.95), margin=dict(t=60, b=20, l=10, r=10))
                        path = os.path.join(tmp_dir, name)
                        fig.write_image(path, engine="kaleido", scale=2)
                        return path

                    # PÁGINA 1: DASHBOARD COMPACTO
                    pdf.add_page()
                    pdf.set_font('Helvetica', 'B', 16); pdf.cell(0, 10, 'REPORTE ESTRATÉGICO INTEGRAL', ln=True, align='C')
                    pdf.set_font('Helvetica', '', 12); pdf.cell(0, 8, f'Evaluado: {lider_sel}', ln=True, align='C')
                    
                    pdf.set_font('Helvetica', 'B', 10)
                    eval_txt = f'Total Evaluadores: {int(d.CANT_EVAL)} | Auto: {int(d.CANT_AUTO)} | Jefe: {int(d.CANT_JEFE)} | Pares: {int(d.CANT_PAR)} | Colab: {int(d.CANT_COL)}'
                    pdf.cell(0, 8, eval_txt, ln=True, align='C')
                    
                    # 1. Frecuencia
                    pdf.ln(2); pdf.set_font('Helvetica', 'B', 11); pdf.cell(0, 10, '1. Frecuencia de comportamientos por niveles (%)', ln=True)
                    y_frec = pdf.get_y()
                    pdf.image(save_pdf_chart_final(generar_fig_barras(v_auto, "", "#3498db"), "b1.png", "Auto"), x=10, y=y_frec, w=60)
                    pdf.image(save_pdf_chart_final(generar_fig_barras(v_ind, "", "#2ecc71"), "b2.png", "Indiv"), x=75, y=y_frec, w=60)
                    pdf.image(save_pdf_chart_final(generar_fig_barras(v_org, "", "#e74c3c"), "b3.png", "Org"), x=140, y=y_frec, w=60)
                    
                    # 2. Radar y Equilibrio
                    pdf.set_y(y_frec + 43)
                    pdf.set_font('Helvetica', 'B', 11); pdf.cell(0, 10, '2. Alineación de Consciencia e Índice de Equilibrio', ln=True)
                    y_radar = pdf.get_y()
                    pdf.image(save_pdf_chart_final(fig_radar, "radar.png", ""), x=10, y=y_radar, w=95)
                    pdf.image(save_pdf_chart_final(fig_dim, "dim.png", ""), x=110, y=y_radar + 5, w=90)
                    
                    # 3. Relojes Barrett (Sincronizados)
                    pdf.ln(10)
                    pdf.set_y(y_radar + 75)
                    pdf.set_font('Helvetica', 'B', 11); pdf.cell(0, 10, '3. Niveles de Madurez Barrett (Relojes)', ln=True)
                    y_relojes_base = pdf.get_y()
                    img_r1 = save_pdf_chart_final(generar_fig_reloj(v_auto, False), "r1p.png", "Auto")
                    img_r2 = save_pdf_chart_final(generar_fig_reloj(v_ind, False), "r2p.png", "Indiv")
                    img_r3 = save_pdf_chart_final(generar_fig_reloj(v_org, False), "r3p.png", "Org")
                    
                    pdf.image(img_r1, x=35, y=y_relojes_base+12, w=60)
                    pdf.image(img_r2, x=88, y=y_relojes_base+12, w=60)
                    pdf.image(img_r3, x=141, y=y_relojes_base+12, w=60)
                    
                    pdf.set_font('Helvetica', '', 7); pdf.set_text_color(100, 100, 100)
                    niv_manual = ["L7-Visionario", "L6-Mentor", "L5-Autentico", "L4-Facilitador", "L3-Desempeno", "L2-Relaciones", "L1-Crisis"]
                    for i, txt in enumerate(niv_manual):
                        pdf.text(15, y_relojes_base + 10 + (i * 5.15), txt)
                    pdf.set_text_color(0, 0, 0)

                    # PÁGINA 2: NINEBOX Y TEXTO IA
                    pdf.add_page(); pdf.set_font('Helvetica', 'B', 11); pdf.cell(0, 10, '4. Posicionamiento Estratégico NineBox Confa', ln=True)
                    fig_nb.update_layout(template="plotly", paper_bgcolor='white', plot_bgcolor='white', font=dict(color='black'))
                    img_nb = os.path.join(tmp_dir, "nb.png"); fig_nb.write_image(img_nb, engine="kaleido", scale=4); pdf.image(img_nb, x=25, w=160)
                    
                    pdf.ln(5); pdf.set_font('Helvetica', 'B', 13); pdf.cell(0, 10, '5. Análisis Ejecutivo Estratégico', ln=True); pdf.set_font('Helvetica', '', 10)
                    limpio = st.session_state.informe_cache[lider_sel].replace("**", "").encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(0, 6, limpio)

                st.download_button("📥 Guardar PDF Final", data=bytes(pdf.output()), file_name=f"Reporte_{lider_sel}.pdf", mime="application/pdf")
            except Exception as e: st.error(f"Error PDF: {e}")
