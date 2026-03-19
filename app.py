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
    .main { background-color: #0e1117; color: white !important; font-family: 'Helvetica Neue', sans-serif; }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stSelectbox label { color: white !important; }
    .stSelectbox div[data-baseweb="select"] { color: white !important; background-color: #1e293b; }
    .block-container { padding-top: 1rem; }
    h1 { color: #BFDBFE !important; text-align: center; }
    .titulo-col { text-align: center; font-weight: bold; color: #BFDBFE; margin-bottom: 10px; font-size: 1.1rem; }
    
    .leyenda-v3 {
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        height: 340px; 
        margin-top: 35px; 
        padding-right: 10px;
        border-right: 1px solid #334155;
    }
    .item-ley {
        height: 48px; 
        display: flex;
        align-items: center;
        justify-content: flex-end;
        font-size: 0.85rem;
        font-weight: bold;
        color: #94a3b8;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN IA SEGURA ---
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
        df = pd.read_csv('Resultados_Gerentes.csv', sep=';', decimal=',')
        df.columns = df.columns.str.strip()
        df['Nombre_Lider'] = df['Nombre_Lider'].astype(str).str.strip()
        df = df[~df['Nombre_Lider'].isin(['0.0', 'nan', ''])]
        df = df.dropna(subset=['Nombre_Lider'])
        cols_check = [c for c in df.columns if 'L' in c and any(x in c for x in ['AUTO', 'INDIV', 'ORG'])]
        for col in cols_check:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Error crítico de datos: {e}")
        return None

df = load_data()

if df is not None:
    lideres = sorted(df['Nombre_Lider'].unique())
    lider_sel = st.selectbox("Seleccione el líder para el análisis detallado:", lideres)
    
    if "informe_cache" not in st.session_state:
        st.session_state.informe_cache = {}
        
    d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

    # Cálculos de dimensiones (RESTAURADOS)
    gerencia_prom = (d.INDIV_L1 + d.INDIV_L2 + d.INDIV_L3) / 3
    transicion_prom = d.INDIV_L4
    liderazgo_prom = (d.INDIV_L5 + d.INDIV_L6 + d.INDIV_L7) / 3

    v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
    v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
    v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]

    def obtener_etiqueta_color(v):
        if v < 65: return "Bajo", "#ff4b4b"
        if v < 75: return "Medio", "#f1c40f"
        if v < 85: return "Alto", "#2ecc71"
        return "Superior", "#3498db"

    # --- 5. BARRAS (%) ---
    st.divider()
    st.subheader("Distribución de Energía por Niveles de Conciencia (%)")
    c1, c2, c3 = st.columns(3)
    def dibujar_barras(vals, titulo, color):
        labels = ['L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 'L4 - Facilitador', 'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis']
        v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
        fig = go.Figure(go.Bar(x=v_plot, y=labels, orientation='h', marker_color=color, text=[f"{round(v,1)}%" for v in v_plot], textposition='inside'))
        fig.update_layout(title=dict(text=titulo, x=0.5), xaxis_range=[0, 105], height=350, template="plotly_dark", margin=dict(l=0, r=10, t=40, b=20), yaxis=dict(autorange="reversed"))
        return fig
    
    fig_b1 = dibujar_barras(v_auto, "Autovaloración", "#3498db")
    fig_b2 = dibujar_barras(v_ind, "Individual (360)", "#2ecc71")
    fig_b3 = dibujar_barras(v_org, "Promedio Organizacional", "#e74c3c")
    
    with c1: st.plotly_chart(fig_b1, key="b1")
    with c2: st.plotly_chart(fig_b2, key="b2")
    with c3: st.plotly_chart(fig_b3, key="b3")

    # --- 6. RELOJES (ALINEACIÓN RESTAURADA) ---
    st.divider()
    st.subheader("⏳ Evolución del Liderazgo (Semáforo de Madurez)")
    def dibujar_reloj_barrett(vals):
        anchos = [6, 5, 4, 3.2, 4, 5, 6] 
        colors_barrett = ["rgba(111, 66, 193, 0.5)"]*3 + ["rgba(40, 167, 69, 0.4)"] + ["rgba(253, 126, 20, 0.5)"]*3
        v_rev = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
        etiquetas = [obtener_etiqueta_color(v)[0] for v in v_rev]
        col_txt = [obtener_etiqueta_color(v)[1] for v in v_rev]
        fig = go.Figure(go.Funnel(y=[1,2,3,4,5,6,7], x=anchos, text=etiquetas, textinfo="text", textfont=dict(color=col_txt, size=14, family='Arial Black'), marker={"color": colors_barrett, "line": {"width": 2, "color": "white"}}, connector={"visible": False}))
        fig.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(visible=False), xaxis=dict(visible=False), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        return fig

    cl, cr1, cr2, cr3 = st.columns([1, 1, 1, 1])
    with cl:
        st.markdown('<div class="titulo-col">Nivel Barrett</div>', unsafe_allow_html=True)
        st.markdown('<div class="leyenda-v3">' + ''.join([f'<div class="item-ley">{n}</div>' for n in ["L7 - Visionario", "L6 - Mentor", "L5 - Auténtico", "L4 - Facilitador", "L3 - Desempeño", "L2 - Relaciones", "L1 - Crisis"]]) + '</div>', unsafe_allow_html=True)
    
    fig_r1 = dibujar_reloj_barrett(v_auto)
    fig_r2 = dibujar_reloj_barrett(v_ind)
    fig_r3 = dibujar_reloj_barrett(v_org)

    with cr1: st.plotly_chart(fig_r1, key="r1")
    with cr2: st.plotly_chart(fig_r2, key="r2")
    with cr3: st.plotly_chart(fig_r3, key="r3")

    # --- 7. RADAR Y DIMENSIONES ---
    st.divider()
    col_radar, col_dim = st.columns([1.5, 1])
    with col_radar:
        st.subheader("Radar de Alineación Triple (%)")
        fig_radar = go.Figure()
        cats = ['L1','L2','L3','L4','L5','L6','L7']
        for val, name, color in zip([v_auto, v_ind, v_org], ['Auto', 'Individual', 'Organizacional'], ['#3498db', '#2ecc71', '#e74c3c']):
            fig_radar.add_trace(go.Scatterpolar(r=val, theta=cats, fill='toself', name=name, line_color=color))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=500, template="plotly_dark", legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"))
        st.plotly_chart(fig_radar, key="radar")
    with col_dim:
        st.subheader("Madurez Global")
        dims = ['Liderazgo (L5-L7)', 'Transición (L4)', 'Gerencia (L1-L3)']
        vals_dim = [liderazgo_prom, transicion_prom, gerencia_prom]
        fig_dim = go.Figure(go.Bar(x=vals_dim, y=dims, orientation='h', marker_color=[obtener_etiqueta_color(v)[1] for v in vals_dim], text=[f"{round(v,1)}% - {obtener_etiqueta_color(v)[0]}" for v in vals_dim], textposition='inside'))
        fig_dim.update_layout(xaxis_range=[0, 105], height=400, template="plotly_dark", yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_dim, key="dim")

    # --- 8. INFORME IA (RECUPERADO ÍNTEGRO CON DIMENSIONES) ---
    st.divider()
    if st.button("🚀 GENERAR INFORME EJECUTIVO"):
        prompt_maestro = f"""
        Actúa como un experto consultor senior en desarrollo de liderazgo (Richard Barrett). Genera un informe estratégico 360° para {lider_sel}.
        DATOS: {d.to_json()}
        REGLA DE NOMENCLATURA OBLIGATORIA:
        - Nivel 7: LÍDER VISIONARIO - Propósito de vivir
        - Nivel 6: LÍDER MENTOR/SOCIO - Trabajo en la colaboración
        - Nivel 5: LÍDER AUTÉNTICO - Autoexpresión genuina
        - Nivel 4: FACILITADOR/INNOVADOR - Evolución de forma valiente
        - Nivel 3: GESTOR DE DESEMPEÑO - Logrando la excelencia
        - Nivel 2: GESTOR DE RELACIONES - Apoyo de relaciones
        - Nivel 1: GESTOR DE CRISIS - Garantizar visibilidad

        ESTRUCTURA DEL INFORME:
        1. DESCRIPCIÓN POR NIVELES: Desglose L1 a L7 ascendente. Usa la NOMENCLATURA OBLIGATORIA y analiza el impacto según el 'Ponderado Individual'.
        2. ANÁLISIS DE AUTOVALORACIÓN: Autoconciencia frente a la visión del entorno (Ponderado individual vs Autoevaluacion).
        3. MATRIZ DE MADUREZ: Alineación estratégica Individual (Ponderado Individual) vs Organizacional (Ponderado organizacional).
        4. PERFIL DE LIDERAZGO: Estilo (Nivel predominante y dimensión predominante según el promedio mas alto (Liderazgo: {round(liderazgo_prom,1)}%, Transición: {round(transicion_prom,1)}%, Gerencia: {round(gerencia_prom,1)}%)) y equilibrio de las 3 dimensiones, en base a ese equilibrio entrega 3 recomendaciones apreciativas (punto seguido).

        FILOSOFÍA Y REDACCIÓN: 100% Apreciativa. Sin lenguaje negativo. HABLA SIEMPRE EN TERCERA PERSONA NEUTRAL. Inicia directamente.
        """
        try:
            with st.spinner('Analizando datos...'):
                response = model.generate_content(prompt_maestro)
                st.session_state.informe_cache[lider_sel] = response.text
        except Exception as e:
            st.error(f"Error IA: {e}")

    if lider_sel in st.session_state.informe_cache:
        texto_informe = st.session_state.informe_cache[lider_sel]
        st.markdown(f"### 📋 Informe Ejecutivo: {lider_sel}")
        st.write(texto_informe)

        # --- 9. MÓDULO PDF CONSOLIDADO UNA HOJA ---
        st.divider()
        if st.button("📄 GENERAR REPORTE CONSOLIDADO PDF"):
            with st.spinner('Procesando PDF...'):
                try:
                    pdf = FPDF()
                    pdf.set_auto_page_break(auto=True, margin=15)
                    pdf.add_page()
                    pdf.set_font('Helvetica', 'B', 14)
                    pdf.cell(0, 10, 'REPORTE ESTRATEGICO DE LIDERAZGO (MODELO BARRETT)', ln=True, align='C')
                    pdf.set_font('Helvetica', '', 11)
                    pdf.cell(0, 8, f'Líder: {lider_sel}', ln=True, align='C')
                    pdf.ln(2)

                    with tempfile.TemporaryDirectory() as tmp_dir:
                        def save_chart(fig, name, w=600, h=300):
                            fig.update_layout(template="plotly", paper_bgcolor='white', font=dict(color="black"), width=w, height=h)
                            path = os.path.join(tmp_dir, name)
                            fig.write_image(path, engine="kaleido")
                            return path
                        
                        # Fila 1: Barras
                        pdf.image(save_chart(fig_b1, "b1.png"), x=10, y=30, w=60)
                        pdf.image(save_chart(fig_b2, "b2.png"), x=75, y=30, w=60)
                        pdf.image(save_chart(fig_b3, "b3.png"), x=140, y=30, w=60)
                        
                        # Fila 2: Radar y Dimensiones
                        pdf.image(save_chart(fig_radar, "radar.png", 500, 400), x=10, y=85, w=95)
                        pdf.image(save_chart(fig_dim, "dim.png", 500, 350), x=110, y=95, w=90)
                        
                        # Fila 3: Relojes
                        pdf.image(save_chart(fig_r1, "r1.png", 400, 400), x=15, y=165, w=55)
                        pdf.image(save_chart(fig_r2, "r2.png", 400, 400), x=75, y=165, w=55)
                        pdf.image(save_chart(fig_r3, "r3.png", 400, 400), x=135, y=165, w=55)

                    pdf.add_page()
                    pdf.set_font('Helvetica', 'B', 14)
                    pdf.cell(0, 10, 'Analisis Ejecutivo de Consciencia', ln=True)
                    pdf.ln(5)
                    pdf.set_font('Helvetica', '', 10)
                    limpio = texto_informe.replace("**", "").replace("###", "").replace("- ", "• ")
                    limpio = re.sub(r'\$\(L\d\)\^\{\*\*\}', '', limpio)
                    limpio = limpio.encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(0, 6, limpio)

                    for f in [fig_radar, fig_dim, fig_r1, fig_r2, fig_r3, fig_b1, fig_b2, fig_b3]:
                        f.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)')

                    output = pdf.output()
                    st.download_button(label="📥 Descargar PDF", data=bytes(output), file_name=f"Reporte_{lider_sel}.pdf", mime="application/pdf")
                except Exception as e: st.error(f"Error PDF: {e}")
