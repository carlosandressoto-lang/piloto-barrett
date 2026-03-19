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
    
    /* Restauración de la leyenda visual para la App */
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
    
    d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

    v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
    v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
    v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]

    gerencia_prom = (d.INDIV_L1 + d.INDIV_L2 + d.INDIV_L3) / 3
    transicion_prom = d.INDIV_L4
    liderazgo_prom = (d.INDIV_L5 + d.INDIV_L6 + d.INDIV_L7) / 3

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

    def generar_fig_reloj(vals, incluir_leyenda=False, forzar_pdf=False):
        anchos_base = [6, 5, 4, 3.2, 4, 5, 6] 
        v_rev = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
        colors_barrett = ["rgb(33,115,182)"]*3 + ["rgb(140,183,42)"] + ["rgb(241,102,35)"]*3
        labels_niveles = ["L7-Visionario", "L6-Mentor", "L5-Auténtico", "L4-Facilitador", "L3-Desempeño", "L2-Relaciones", "L1-Crisis"]
        
        fig = go.Figure()
        fig.add_trace(go.Funnel(
            y=labels_niveles if incluir_leyenda else [1,2,3,4,5,6,7],
            x=anchos_base,
            textinfo="none",
            hoverinfo="none",
            marker={"color": colors_barrett, "line": {"width": 1, "color": "rgba(255,255,255,0.3)"}},
            connector={"visible": False}
        ))

        for i, (val, ancho) in enumerate(zip(v_rev, anchos_base)):
            fig.add_annotation(
                x=0, y=i if incluir_leyenda else i+1,
                text=obtener_etiqueta(val),
                showarrow=False,
                font=dict(color=obtener_color_desarrollo(val), size=12, family='Arial Black'),
                bgcolor="white",
                bordercolor="rgba(255,255,255,0)",
                borderpad=4,
                width=ancho * 22.0
            )

        # COMPENSACIÓN DE MARGEN PARA SIMETRÍA (PDF)
        margen_l = 100 if (incluir_leyenda or forzar_pdf) else 10
        
        fig.update_layout(
            height=400, 
            margin=dict(l=margen_l, r=20, t=10, b=10), 
            yaxis=dict(visible=incluir_leyenda, tickfont=dict(color="#94a3b8" if not incluir_leyenda else "black", size=10)), 
            xaxis=dict(visible=False), 
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)'
        )
        return fig

    # --- 5. RENDER DASHBOARD ---
    st.divider()
    st.subheader("📊 Frecuencia de comportamientos por niveles (%)")
    c1, c2, c3 = st.columns(3)
    with c1: st.plotly_chart(generar_fig_barras(v_auto, "Autovaloración", "#3498db"), key="b1_v")
    with c2: st.plotly_chart(generar_fig_barras(v_ind, "Individual (360)", "#2ecc71"), key="b2_v")
    with c3: st.plotly_chart(generar_fig_barras(v_org, "Promedio Organizacional", "#e74c3c"), key="b3_v")

    st.divider()
    st.subheader("⏳ Resultados Evaluación 360°")
    
    # RESTAURACIÓN DE LA LEYENDA EN LA APP
    cl, cr1, cr2, cr3 = st.columns([1, 1, 1, 1])
    with cl:
        st.markdown('<div class="titulo-col">Nivel Barrett</div>', unsafe_allow_html=True)
        niveles = ["L7 - Visionario", "L6 - Mentor", "L5 - Auténtico", "L4 - Facilitador", "L3 - Desempeño", "L2 - Relaciones", "L1 - Crisis"]
        st.markdown('<div class="leyenda-v3">' + ''.join([f'<div class="item-ley">{n}</div>' for n in niveles]) + '</div>', unsafe_allow_html=True)
    
    with cr1: 
        st.markdown('<div class="titulo-col">Autovaloración</div>', unsafe_allow_html=True)
        st.plotly_chart(generar_fig_reloj(v_auto, incluir_leyenda=False), key="r1_v")
    with cr2: 
        st.markdown('<div class="titulo-col">Individual (360)</div>', unsafe_allow_html=True)
        st.plotly_chart(generar_fig_reloj(v_ind, incluir_leyenda=False), key="r2_v")
    with cr3: 
        st.markdown('<div class="titulo-col">Organizacional</div>', unsafe_allow_html=True)
        st.plotly_chart(generar_fig_reloj(v_org, incluir_leyenda=False), key="r3_v")

    # --- 6. RADAR Y DIMENSIONES ---
    st.divider()
    col_radar, col_dim = st.columns([1.5, 1])
    with col_radar:
        st.subheader("🎯 Alineación de Consciencia y Entorno")
        fig_radar = go.Figure()
        cats = ['L1','L2','L3','L4','L5','L6','L7']
        for val, name, color in zip([v_auto, v_ind, v_org], ['Auto', 'Individual', 'Organizacional'], ['#3498db', '#2ecc71', '#e74c3c']):
            fig_radar.add_trace(go.Scatterpolar(r=val, theta=cats, fill='toself', name=name, line_color=color))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=500, template="plotly_dark", legend=dict(orientation="h", y=1.25, x=0.5, xanchor="center"))
        st.plotly_chart(fig_radar, key="radar_v")
    with col_dim:
        st.subheader("⚖️ Índice del Equilibrio de Liderazgo")
        vals_dim = [liderazgo_prom, transicion_prom, gerencia_prom]
        fig_dim = go.Figure(go.Bar(x=vals_dim, y=['Liderazgo (L5-L7)', 'Transición (L4)', 'Gerencia (L1-L3)'], orientation='h', marker_color=[obtener_color_desarrollo(v) for v in vals_dim], text=[f"{round(v,1)}% - {obtener_etiqueta(v)}" for v in vals_dim], textposition='inside'))
        fig_dim.update_layout(xaxis_range=[0, 105], height=400, template="plotly_dark", yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_dim, key="dim_v")

    # --- 7. INFORME IA (SIN CAMBIOS) ---
    if "informe_cache" not in st.session_state:
        st.session_state.informe_cache = {}

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
        1. DESCRIPCIÓN POR NIVELES: Lista de L1 a L7 con el nombre de contexto Barret (Ejemplo L1: Gestor de Crisis). Clasifica cada nivel basándote en el 'Ponderado Individual' usando la rúbrica (Bajo, Medio, Alto, Superior) y las definiciones Barrett anteriores para generar una descripción según el modelo barret y el nivel de la rubrica del lider. Siempre una lista de Nivel 1 a Nivel 7 no lo hagas en 1 solo párrafo porque confunde
        2. ANÁLISIS DE AUTOVALORACIÓN: Un párrafo. Analiza alineación percepción interna (Autoevaluacion) vs colectiva (Ponderado individual que es la evaluación de Jefe directo, Colaboradores a cargo y Pares). Resalta donde la influencia externa es mayor a la autopercepción, o aquellos puntos donde la autoevaluacion sea mayor en rubrica a lo evaluado pues son 2 cosas diferentes a trabajar segun el nivel de consiencia. 
        3. MATRIZ DE MADUREZ: Un párrafo sólido. Analiza sintonía del líder (Ponderado Individual) con el Ponderado Organizacional basándote en la Rúbrica.
        4. PERFIL DE LIDERAZGO: Un párrafo sólido. Define el estilo predominante según el promedio más alto (Liderazgo: {round(liderazgo_prom,1)}%, Transición: {round(transicion_prom,1)}%, Gerencia: {round(gerencia_prom,1)}%) y ofrece 3 recomendaciones de expansión para llegar a un equilibrio de las 3 dimensiones (Liderazgo Transicion y Gerencia) punto seguido.
        """
        try:
            with st.spinner('Consolidando informe...'):
                response = model.generate_content(prompt_maestro)
                st.session_state.informe_cache[lider_sel] = response.text
        except Exception as e:
            st.error(f"Error IA: {e}")

    if lider_sel in st.session_state.informe_cache:
        st.markdown(f"### 📋 Informe de Desarrollo: {lider_sel}")
        st.write(st.session_state.informe_cache[lider_sel])

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
                        
                        pdf.set_font('Helvetica', 'B', 10)
                        pdf.text(10, 38, "1. Frecuencia de comportamientos por niveles (%)")
                        pdf.image(save_chart(generar_fig_barras(v_auto, "Auto", "#3498db"), "b1.png"), x=10, y=42, w=60)
                        pdf.image(save_chart(generar_fig_barras(v_ind, "Individual", "#2ecc71"), "b2.png"), x=75, y=42, w=60)
                        pdf.image(save_chart(generar_fig_barras(v_org, "Organizacional", "#e74c3c"), "b3.png"), x=140, y=42, w=60)

                        pdf.text(10, 95, "2. Alineación de Consciencia y Entorno")
                        pdf.image(save_chart(fig_radar, "radar.png", 500, 400), x=10, y=98, w=95)
                        pdf.text(110, 95, "3. Índice del Equilibrio de Liderazgo")
                        fig_dim_pdf = go.Figure(go.Bar(x=[liderazgo_prom, transicion_prom, gerencia_prom], y=['Liderazgo', 'Transición', 'Gerencia'], orientation='h', marker_color="#3498db"))
                        pdf.image(save_chart(fig_dim_pdf, "dim.png", 500, 350), x=110, y=105, w=90)

                        # SIMETRÍA TOTAL EN PDF SIN AFECTAR LA APP
                        pdf.text(15, 175, "4. Resultados Evaluación 360° (Niveles Barrett)")
                        pdf.set_font('Helvetica', 'B', 8)
                        pdf.text(45, 182, "Autovaloración")
                        pdf.text(103, 182, "Individual (360)")
                        pdf.text(158, 182, "Organizacional")
                        
                        r1_pdf = generar_fig_reloj(v_auto, incluir_leyenda=True)
                        r2_pdf = generar_fig_reloj(v_ind, incluir_leyenda=False, forzar_pdf=True)
                        r3_pdf = generar_fig_reloj(v_org, incluir_leyenda=False, forzar_pdf=True)

                        pdf.image(save_chart(r1_pdf, "r1.png", 500, 400), x=15, y=184, w=60) 
                        pdf.image(save_chart(r2_pdf, "r2.png", 500, 400), x=75, y=184, w=60) 
                        pdf.image(save_chart(r3_pdf, "r3.png", 500, 400), x=135, y=184, w=60)

                    pdf.add_page()
                    pdf.set_font('Helvetica', 'B', 14)
                    pdf.cell(0, 10, 'Análisis Ejecutivo de Consciencia de Liderazgo', ln=True)
                    pdf.ln(5)
                    pdf.set_font('Helvetica', '', 10)
                    limpio = st.session_state.informe_cache[lider_sel].replace("**", "").replace("###", "").replace("- ", "• ")
                    limpio = limpio.encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(0, 6, limpio)

                    output = pdf.output()
                    st.download_button(label="📥 Descargar PDF Final Simétrico", data=bytes(output), file_name=f"Reporte_Liderazgo_{lider_sel}.pdf", mime="application/pdf")
                except Exception as e: st.error(f"Error PDF: {e}")
