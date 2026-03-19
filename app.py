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

    gerencia_prom = (d.INDIV_L1 + d.INDIV_L2 + d.INDIV_L3) / 3
    transicion_prom = d.INDIV_L4
    liderazgo_prom = (d.INDIV_L5 + d.INDIV_L6 + d.INDIV_L7) / 3

    v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
    v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
    v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]

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

    # --- 4. FUNCIONES DE DIBUJO ---
    def generar_fig_barras(vals, titulo, color):
        labels = ['L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 'L4 - Facilitador', 'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis']
        v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
        fig = go.Figure(go.Bar(x=v_plot, y=labels, orientation='h', marker_color=color, text=[f"{round(v,1)}%" for v in v_plot], textposition='inside'))
        fig.update_layout(title=dict(text=titulo, x=0.5), xaxis_range=[0, 105], height=350, template="plotly_dark", margin=dict(l=0, r=10, t=40, b=20), yaxis=dict(autorange="reversed"))
        return fig

    def generar_fig_reloj(vals, incluir_leyenda=False):
        anchos = [6, 5, 4, 3.2, 4, 5, 6] 
        v_rev = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
        # Colores Institucionales Barrett Base
        colors_barrett_base = ["rgb(33,115,182)"]*3 + ["rgb(140,183,42)"] + ["rgb(241,102,35)"]*3
        labels_niveles = ["L7-Visionario", "L6-Mentor", "L5-Auténtico", "L4-Facilitador", "L3-Desempeño", "L2-Relaciones", "L1-Crisis"]
        
        fig = go.Figure(go.Funnel(
            y=labels_niveles if incluir_leyenda else [1,2,3,4,5,6,7], 
            x=anchos, text=[obtener_etiqueta(v) for v in v_rev], textinfo="text", 
            textfont=dict(color=[obtener_color_desarrollo(v) for v in v_rev], size=14, family='Arial Black'), 
            marker={
                "color": colors_barrett_base, # Fondo institucional sólido
                "line": {"width": 2, "color": "white"} 
            }, 
            connector={"visible": False}
        ))
        # MEJORA VISUAL FINAL (Doble Caja Proporcional): Caja blanca central amplia y definida para el texto
        fig.update_traces(texttemplate="<span style='background-color: white; border-radius: 4px; padding: 8px 25px; border: 1px solid #ccc; box-shadow: 1px 1px 3px rgba(0,0,0,0.1);'> %{text} </span>")
        fig.update_layout(height=400, margin=dict(l=80 if incluir_leyenda else 10, r=10, t=10, b=10), 
                          yaxis=dict(visible=incluir_leyenda, tickfont=dict(color="#94a3b8", size=10)), 
                          xaxis=dict(visible=False), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        return fig

    # --- 5. ASIGNACIÓN GLOBAL ---
    fig_b1 = generar_fig_barras(v_auto, "Autovaloración", "#3498db")
    fig_b2 = generar_fig_barras(v_ind, "Individual (360)", "#2ecc71")
    fig_b3 = generar_fig_barras(v_org, "Promedio Organizacional", "#e74c3c")
    
    fig_r1 = generar_fig_reloj(v_auto)
    fig_r2 = generar_fig_reloj(v_ind)
    fig_r3 = generar_fig_reloj(v_org)

    # --- 6. RENDER DASHBOARD ---
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1: st.plotly_chart(fig_b1, key="b1_v")
    with c2: st.plotly_chart(fig_b2, key="b2_v")
    with c3: st.plotly_chart(fig_b3, key="b3_v")

    st.divider()
    st.subheader("⏳ Evolución del Liderazgo (Semáforo de Madurez)")
    cl, cr1, cr2, cr3 = st.columns([1, 1, 1, 1])
    with cl:
        st.markdown('<div class="titulo-col">Nivel Barrett</div>', unsafe_allow_html=True)
        st.markdown('<div class="leyenda-v3">' + ''.join([f'<div class="item-ley">{n}</div>' for n in ["L7 - Visionario", "L6 - Mentor", "L5 - Auténtico", "L4 - Facilitador", "L3 - Desempeño", "L2 - Relaciones", "L1 - Crisis"]]) + '</div>', unsafe_allow_html=True)
    with cr1: st.markdown('<div class="titulo-col">Autovaloración</div>', unsafe_allow_html=True); st.plotly_chart(fig_r1, key="r1_v")
    with cr2: st.markdown('<div class="titulo-col">Individual</div>', unsafe_allow_html=True); st.plotly_chart(fig_r2, key="r2_v")
    with cr3: st.markdown('<div class="titulo-col">Organizacional</div>', unsafe_allow_html=True); st.plotly_chart(fig_r3, key="r3_v")

    # --- 7. Radar y Dimensiones ---
    st.divider()
    col_radar, col_dim = st.columns([1.5, 1])
    with col_radar:
        st.subheader("Radar de Alineación Triple (%)")
        fig_radar = go.Figure()
        cats = ['L1','L2','L3','L4','L5','L6','L7']
        for val, name, color in zip([v_auto, v_ind, v_org], ['Auto', 'Individual', 'Organizacional'], ['#3498db', '#2ecc71', '#e74c3c']):
            fig_radar.add_trace(go.Scatterpolar(r=val, theta=cats, fill='toself', name=name, line_color=color))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=500, template="plotly_dark", legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"))
        st.plotly_chart(fig_radar, key="radar_v")
    with col_dim:
        st.subheader("Madurez Global")
        vals_dim = [liderazgo_prom, transicion_prom, gerencia_prom]
        fig_dim = go.Figure(go.Bar(x=vals_dim, y=['Liderazgo (L5-L7)', 'Transición (L4)', 'Gerencia (L1-L3)'], orientation='h', marker_color=[obtener_color_desarrollo(v) for v in vals_dim], text=[f"{round(v,1)}% - {obtener_etiqueta(v)}" for v in vals_dim], textposition='inside'))
        fig_dim.update_layout(xaxis_range=[0, 105], height=400, template="plotly_dark", yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_dim, key="dim_v")

    # --- 8. INFORME IA (INTOCABLE) ---
    st.divider()
    if st.button("🚀 GENERAR INFORME EJECUTIVO"):
        prompt_maestro = f"""
        Actúa como consultor senior de DESARROLLO DE LIDERAZGO Barrett. Genera un reporte para {lider_sel}. DATOS: {d.to_json()}
        PROHIBIDO USAR ANGLICISMOS. REDACTA TODO EN ESPAÑOL PURO.
        CONTEXTO BARRETT:
        - L1: Gestor de Crisis. Foco en estabilidad y viabilidad operativa. (Supervivencia)
        - L2: Constructor de Relaciones. Foco en armonía y respeto mutuo. (Relaciones)
        - L3: Gestor Organizador. Foco en eficiencia y resultados de calidad. (Autoestima)
        - L4: Facilitador Influyente. Foco en innovación y adaptabilidad. (Transformación)
        - L5: Integrador Inspirador. Foco en integridad y valores. (Cohesión Interna)
        - L6: Mentor Socio. Foco en colaboración y mentoría. (Hacer la Diferencia)
        - L7: Visionario Sabio. Foco en propósito y visión de largo plazo. (Servicio)

        REGLAS DE ORO: 
        - INICIA DIRECTAMENTE. PROHIBIDO SALUDOS O INTRODUCCIONES o RESMENES O APRECIACIONES.
        - PROHIBIDO USAR: "desempeño", "brechas", "puntos ciegos" o hablar desde defectos o fallos, debe ser un feedback totalmente apreciativo.
        - USA: "desarrollo", "alineación", "influencia", "oportunidad de expansión".
        - RÚBRICA: Bajo (<65), Medio (65-75), Alto (75-85), Superior (>85).

        ESTRUCTURA ESPEJO OBLIGATORIA:
        1. DESCRIPCIÓN POR NIVELES: Lista de L1 a L7 con el nombre de contexto Barret (Ejemplo L1: Gestor de Crisis). Clasifica cada nivel basándote en el 'Ponderado Individual' usando la rúbrica (Bajo, Medio, Alto, Superior) y las definiciones Barrett anteriores para generar una descripción según el modelo barrat y el nivel de la rubrida del lider.
        2. ANÁLISIS DE AUTOVALORACIÓN: Un párrafo. Analiza alineación percepción interna (Autoevaluacion) vs colectiva (Ponderado individual que es la evaluación de Jefe directo, Colaboradore a cargo y Pares). Resalta donde la influencia externa es mayor a la autopercepción, o aquellos puntos donde la autoevaluacion sea mayor en rubrica a lo evaluado pues son 2 cosas diferentes a trabajar segun el nivel de consiencia.
        3. MATRIZ DE MADUREZ: Un párrafo sólido. Analiza sintonía del líder (Ponderado Individual) con el Ponderado Organizacional basándote en la Rúbrica.
        4. PERFIL DE LIDERAZGO: Un párrafo sólido. Define el estilo predominante según el promedio más alto (Liderazgo: {round(liderazgo_prom,1)}%, Transición: {round(transicion_prom,1)}%, Gerencia: {round(gerencia_prom,1)}%) y ofrece 3 recomendaciones de expansión para llegar a un equilibrio de las 3 dimensiones (Liderazgo Transicion y Gerencia) punto seguido.
        """
        try:
            with st.spinner('Consolidando informe espejo...'):
                response = model.generate_content(prompt_maestro)
                st.session_state.informe_cache[lider_sel] = response.text
        except Exception as e:
            st.error(f"Error IA: {e}")

    if lider_sel in st.session_state.informe_cache:
        texto_informe = st.session_state.informe_cache[lider_sel]
        st.markdown(f"### 📋 Informe de Desarrollo: {lider_sel}")
        st.write(texto_informe)

        if st.button("📄 GENERAR REPORTE COMPLETO PDF"):
            with st.spinner('Procesando PDF...'):
                try:
                    pdf = FPDF()
                    pdf.set_auto_page_break(auto=True, margin=15)
                    pdf.add_page()
                    pdf.set_font('Helvetica', 'B', 14)
                    pdf.cell(0, 10, 'REPORTE ESTRATEGICO DE DESARROLLO DE LIDERAZGO', ln=True, align='C')
                    pdf.set_font('Helvetica', '', 11)
                    pdf.cell(0, 10, f'Líder Evaluado: {lider_sel}', ln=True, align='C')
                    pdf.ln(10)

                    with tempfile.TemporaryDirectory() as tmp_dir:
                        def save_chart(fig, name, w=600, h=300):
                            fig.update_layout(template="plotly", paper_bgcolor='white', font=dict(color="black", size=12), width=w, height=h)
                            path = os.path.join(tmp_dir, name)
                            fig.write_image(path, engine="kaleido", scale=2) 
                            return path
                        
                        pdf.set_font('Helvetica', 'B', 9)
                        pdf.text(10, 38, "1. Distribución de Energía (%)")
                        pdf.image(save_chart(fig_b1, "b1.png"), x=10, y=40, w=60)
                        pdf.image(save_chart(fig_b2, "b2.png"), x=75, y=40, w=60)
                        pdf.image(save_chart(fig_b3, "b3.png"), x=140, y=40, w=60)

                        pdf.text(10, 93, "2. Radar de Alineación | 3. Madurez Global")
                        pdf.image(save_chart(fig_radar, "radar.png", 500, 400), x=10, y=95, w=95)
                        pdf.image(save_chart(fig_dim, "dim.png", 500, 350), x=110, y=105, w=90)

                        pdf.text(15, 173, "4. Evolución Madurez Liderazgo")
                        fig_r1_p = generar_fig_reloj(v_auto, incluir_leyenda=True)
                        pdf.image(save_chart(fig_r1_p, "r1.png", 500, 400), x=10, y=175, w=70)
                        pdf.image(save_chart(fig_r2, "r2.png", 400, 400), x=80, y=175, w=60)
                        pdf.image(save_chart(fig_r3, "r3.png", 400, 400), x=140, y=175, w=60)

                    pdf.add_page()
                    pdf.set_font('Helvetica', 'B', 14)
                    pdf.cell(0, 10, 'Análisis Ejecutivo de Consciencia de Liderazgo', ln=True)
                    pdf.ln(5)
                    pdf.set_font('Helvetica', '', 10)
                    limpio = texto_informe.replace("**", "").replace("###", "").replace("- ", "• ")
                    limpio = re.sub(r'\$\(L\d\)\^\{\*\*\}', '', limpio)
                    limpio = limpio.encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(0, 6, limpio)

                    output = pdf.output()
                    st.download_button(label="📥 Descargar PDF Final", data=bytes(output), file_name=f"Reporte_Liderazgo_{lider_sel}.pdf", mime="application/pdf")
                except Exception as e: st.error(f"Error PDF: {e}")
