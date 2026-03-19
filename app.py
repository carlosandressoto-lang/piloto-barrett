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
        return "#3498db"

    def obtener_etiqueta(v):
        if v < 65: return "Bajo"
        if v < 75: return "Medio"
        if v < 85: return "Alto"
        return "Superior"

    # --- 5. BARRAS (%) ---
    st.divider()
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

    # --- 6. RELOJES ---
    st.divider()
    st.subheader("⏳ Evolución del Liderazgo (Semáforo de Madurez)")
    def dibujar_reloj_barrett(vals):
        anchos = [6, 5, 4, 3.2, 4, 5, 6] 
        v_rev = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
        colors_barrett = ["#1e3a8a"]*3 + ["#15803d"] + ["#c2410c"]*3
        
        labels = [obtener_etiqueta(v) for v in v_rev]
        text_colors = [obtener_color_desarrollo(v) for v in v_rev]

        fig = go.Figure(go.Funnel(
            y=[1,2,3,4,5,6,7], x=anchos, text=labels, textinfo="text", 
            textfont=dict(color=text_colors, size=15, family='Arial Black'), 
            marker={"color": colors_barrett, "line": {"width": 2, "color": "white"}}, 
            connector={"visible": False}
        ))
        fig.update_traces(texttemplate="<span style='background-color: white; padding: 2px 8px;'> %{text} </span>")
        fig.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(visible=False), xaxis=dict(visible=False), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        return fig

    cl, cr1, cr2, cr3 = st.columns([1, 1, 1, 1])
    with cl:
        st.markdown('<div class="titulo-col">Nivel Barrett</div>', unsafe_allow_html=True)
        st.markdown('<div class="leyenda-v3">' + ''.join([f'<div class="item-ley">{n}</div>' for n in ["L7 - Visionario", "L6 - Mentor", "L5 - Auténtico", "L4 - Facilitador", "L3 - Desempeño", "L2 - Relaciones", "L1 - Crisis"]]) + '</div>', unsafe_allow_html=True)
    
    fig_r1, fig_r2, fig_r3 = dibujar_reloj_barrett(v_auto), dibujar_reloj_barrett(v_ind), dibujar_reloj_barrett(v_org)
    with cr1: st.markdown('<div class="titulo-col">Autovaloración</div>', unsafe_allow_html=True); st.plotly_chart(fig_r1, key="r1")
    with cr2: st.markdown('<div class="titulo-col">Individual</div>', unsafe_allow_html=True); st.plotly_chart(fig_r2, key="r2")
    with cr3: st.markdown('<div class="titulo-col">Organizacional</div>', unsafe_allow_html=True); st.plotly_chart(fig_r3, key="r3")

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
        fig_dim = go.Figure(go.Bar(x=vals_dim, y=dims, orientation='h', marker_color=[obtener_color_desarrollo(v) for v in vals_dim], text=[f"{round(v,1)}% - {obtener_etiqueta(v)}" for v in vals_dim], textposition='inside'))
        fig_dim.update_layout(xaxis_range=[0, 105], height=400, template="plotly_dark", yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_dim, key="dim")

    # --- 8. INFORME IA ---
    st.divider()
    if st.button("🚀 GENERAR INFORME EJECUTIVO"):
        prompt_maestro = f"""
        Actúa como consultor Barrett senior. Genera un reporte de DESARROLLO DE LIDERAZGO para {lider_sel}. DATOS: {d.to_json()}
        
        CONTEXTO BARRETT OBLIGATORIO:
        - L1 (Survival): Crisis Manager. Estabilidad financiera y viabilidad[cite: 242, 243].
        - L2 (Relationship): Relationship Builder. Respeto, armonía y manejo de conflictos[cite: 257, 265].
        - L3 (Self-esteem): Manager/Organizer. Eficiencia, orden y resultados de calidad[cite: 274, 275, 285].
        - L4 (Transformation): Facilitator/Influencer. Aprendizaje continuo, innovación y adaptabilidad[cite: 295, 296, 301, 309].
        - L5 (Internal Cohesion): Integrator/Inspirer. Valores, integridad y cohesión interna[cite: 314, 315, 317].
        - L6 (Making a Difference): Mentor/Partner. Colaboración, mentoría y alianzas estratégicas[cite: 333, 334, 344].
        - L7 (Service): Wisdom/Visionary. Propósito, servicio al mundo y visión a largo plazo[cite: 350, 352, 363].

        REGLAS DE ORO:
        - INICIA DIRECTAMENTE. PROHIBIDO SALUDOS O INTRODUCCIONES GENÉRICAS.
        - PROHIBIDO USAR: "desempeño", "brechas", "puntos ciegos" o hablar desde defectos o fallos, debe ser un feedback totalmente apreciativo.
        - USA: "desarrollo", "alineación", "influencia", "oportunidad de expansión".
        - RÚBRICA: Bajo (<65), Medio (65-75), Alto (75-85), Superior (>85).

        ESTRUCTURA ESPEJO OBLIGATORIA:
        1. DESCRIPCIÓN POR NIVELES: Lista desglosada de L1 a L7. Clasifica cada nivel basándote en el 'Ponderado Individual' usando la RÚBRICA y el CONTEXTO BARRETT anterior.
        2. ANÁLISIS DE AUTOVALORACIÓN: Un párrafo sólido. Compara Autoevaluación vs percepción colectiva (Jefe, Pares, Colaboradores) que es el 'Ponderado individual'. Resalta donde la influencia es mayor de lo percibido por el líder en su autovaloracion, o donde se tenga mayor brecha.
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

        # --- 9. PDF CONSOLIDADO ---
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
                        pdf.text(10, 38, "1. Distribucion de Energia (%) - Autovaloracion | Individual | Organizacional")
                        pdf.image(save_chart(fig_b1, "b1.png"), x=10, y=40, w=60)
                        pdf.image(save_chart(fig_b2, "b2.png"), x=75, y=40, w=60)
                        pdf.image(save_chart(fig_b3, "b3.png"), x=140, y=40, w=60)

                        pdf.text(10, 93, "2. Radar de Alineacion de Liderazgo Triple")
                        pdf.image(save_chart(fig_radar, "radar.png", 500, 400), x=10, y=95, w=95)
                        pdf.text(110, 93, "3. Madurez Global por Dimensiones (L-T-G)")
                        pdf.image(save_chart(fig_dim, "dim.png", 500, 350), x=110, y=105, w=90)

                        # Captura Leyenda y Relojes
                        pdf.text(15, 173, "4. Evolucion Madurez Liderazgo (Leyenda | Auto | Individual | Organizacional)")
                        # Creamos imagen de leyenda
                        leyenda_niveles = ["L7 - Visionario", "L6 - Mentor", "L5 - Autentico", "L4 - Facilitador", "L3 - Desempeno", "L2 - Relaciones", "L1 - Crisis"]
                        pdf.set_font('Helvetica', 'B', 7)
                        curr_y = 183
                        for n in leyenda_niveles:
                            pdf.text(10, curr_y, n)
                            curr_y += 6.5
                        
                        pdf.image(save_chart(fig_r1, "r1.png", 400, 400), x=30, y=175, w=55)
                        pdf.image(save_chart(fig_r2, "r2.png", 400, 400), x=85, y=175, w=55)
                        pdf.image(save_chart(fig_r3, "r3.png", 400, 400), x=140, y=175, w=55)

                    pdf.add_page()
                    pdf.set_font('Helvetica', 'B', 14)
                    pdf.cell(0, 10, 'Analisis Ejecutivo de Consciencia de Liderazgo', ln=True)
                    pdf.ln(5)
                    pdf.set_font('Helvetica', '', 10)
                    limpio = texto_informe.replace("**", "").replace("###", "").replace("- ", "• ")
                    limpio = re.sub(r'\$\(L\d\)\^\{\*\*\}', '', limpio)
                    limpio = limpio.encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(0, 6, limpio)

                    output = pdf.output()
                    st.download_button(label="📥 Descargar PDF Final", data=bytes(output), file_name=f"Reporte_Liderazgo_{lider_sel}.pdf", mime="application/pdf")
                except Exception as e: st.error(f"Error PDF: {e}")
