import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
from fpdf import FPDF
import io
import tempfile
import os

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
    # --- 4. SELECCIÓN ---
    lideres = sorted(df['Nombre_Lider'].unique())
    lider_sel = st.selectbox("Seleccione el líder para el análisis detallado:", lideres)
    
    if "informe_cache" not in st.session_state:
        st.session_state.informe_cache = {}
        
    d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

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
    with c1: st.plotly_chart(dibujar_barras(v_auto, "Autovaloración", "#3498db"), key="b1")
    with c2: st.plotly_chart(dibujar_barras(v_ind, "Individual (360)", "#2ecc71"), key="b2")
    with c3: st.plotly_chart(dibujar_barras(v_org, "Promedio Organizacional", "#e74c3c"), key="b3")

    # --- 6. RELOJES ---
    st.divider()
    st.subheader("⏳ Evolución del Liderazgo (Semáforo de Madurez)")
    def dibujar_reloj_barrett(vals):
        anchos = [6, 5, 4, 3.2, 4, 5, 6] 
        colors_barrett = ["rgba(111, 66, 193, 0.5)"]*3 + ["rgba(40, 167, 69, 0.5)"] + ["rgba(253, 126, 20, 0.5)"]*3
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
    with cr1:
        st.plotly_chart(dibujar_reloj_barrett(v_auto), key="r1")
    with cr2:
        st.plotly_chart(dibujar_reloj_barrett(v_ind), key="r2")
    with cr3:
        st.plotly_chart(dibujar_reloj_barrett(v_org), key="r3")

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

    # --- 8. INFORME IA ---
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
        ESTRUCTURA:
        1. DESCRIPCIÓN POR NIVELES: Desglose L1 a L7 ascendente. Usa la NOMENCLATURA OBLIGATORIA y analiza el impacto según el 'Ponderado Individual' (Sin poner que es el ponderado individuale esas reduandancias sobran).
        2. ANÁLISIS DE AUTOVALORACIÓN: Autoconciencia frente a la visión del entorno (Ponderado individual).
        3. MATRIZ DE MADUREZ: Alineación estratégica Individual (Ponderado Individual) vs Organizacional (Ponderado organizacional).
        4. PERFIL DE LIDERAZGO: Estilo (Nivel predominante y dimensión predominante según el promedio mas alto (Liderazgo, Trasnsicion, Gerencia)) y 3 recomendaciones apreciativas (punto seguido).
        FILOSOFÍA: 100% Apreciativa. Sin lenguaje negativo. Inicia directamente.
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

        # --- 9. MÓDULO PDF CON IMÁGENES ---
        st.divider()
        if st.button("📄 GENERAR REPORTE COMPLETO PDF"):
            with st.spinner('Procesando imágenes y generando PDF...'):
                try:
                    pdf = FPDF()
                    pdf.set_auto_page_break(auto=True, margin=15)
                    pdf.add_page()
                    pdf.set_font('Helvetica', 'B', 16)
                    pdf.cell(0, 10, 'REPORTE ESTRATEGICO DE LIDERAZGO (BARRETT)', ln=True, align='C')
                    pdf.set_font('Helvetica', '', 12)
                    pdf.cell(0, 10, f'Líder Evaluado: {lider_sel}', ln=True, align='C')
                    pdf.ln(5)

                    # Exportar Radar
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_radar:
                        fig_radar.update_layout(template="plotly", paper_bgcolor='white', plot_bgcolor='white', font=dict(color="black"))
                        fig_radar.write_image(tmp_radar.name, engine="kaleido", format="png")
                        pdf.image(tmp_radar.name, x=10, y=35, w=110)
                    if os.path.exists(tmp_radar.name): os.remove(tmp_radar.name)

                    # Exportar Madurez
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_dim:
                        fig_dim.update_layout(template="plotly", paper_bgcolor='white', plot_bgcolor='white', font=dict(color="black"))
                        fig_dim.write_image(tmp_dim.name, engine="kaleido", format="png")
                        pdf.image(tmp_dim.name, x=125, y=50, w=75)
                    if os.path.exists(tmp_dim.name): os.remove(tmp_dim.name)

                    pdf.set_y(140)
                    pdf.set_font('Helvetica', 'B', 14)
                    pdf.cell(0, 10, 'Analisis Ejecutivo de Consciencia', ln=True)
                    pdf.ln(2)
                    pdf.set_font('Helvetica', '', 10)
                    texto_pdf = texto_informe.encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(0, 7, texto_pdf)

                    # Reset charts to Dark
                    fig_radar.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)')
                    fig_dim.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)')

                    output = pdf.output()
                    st.download_button(label="📥 Descargar PDF Final", data=bytes(output), file_name=f"Reporte_{lider_sel}.pdf", mime="application/pdf")
                except Exception as e:
                    st.error(f"Error PDF: {e}")
