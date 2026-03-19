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
    st.error("Error: Configura 'GEMINI_API_KEY' in Secrets.")

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
    # MEJORA: Buscador habilitado en la lista desplegable
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
    
    fig_b1 = dibujar_barras(v_auto, "Autovaloración", "#3498db")
    fig_b2 = dibujar_barras(v_ind, "Individual (360)", "#2ecc71")
    fig_b3 = dibujar_barras(v_org, "Promedio Organizacional", "#e74c3c")
    
    with c1: st.plotly_chart(fig_b1, key="b1")
    with c2: st.plotly_chart(fig_b2, key="b2")
    with c3: st.plotly_chart(fig_b3, key="b3")

    # --- 6. RELOJES (MEJORA COLORES BARRETT SIN PERDER RÚBRICA) ---
    st.divider()
    st.subheader("⏳ Evolución del Liderazgo (Semáforo de Madurez)")
    def dibujar_reloj_barrett(vals):
        anchos = [6, 5, 4, 3.2, 4, 5, 6] 
        # Fondo Azul Barrett para L5-L7, el resto sigue igual
        colors_barrett = ["#819FF7"]*3 + ["rgba(40, 167, 69, 0.4)"] + ["rgba(253, 126, 20, 0.5)"]*3
        v_rev = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
        etiquetas = [obtener_etiqueta_color(v)[0] for v in v_rev]
        
        col_txt = []
        for i, v in enumerate(v_rev):
            if i < 3 and obtener_etiqueta_color(v)[0] == "Superior":
                col_txt.append("#0000FF") # Azul intenso para Superior en zona Barrett
            else:
                col_txt.append(obtener_etiqueta_color(v)[1])

        fig = go.Figure(go.Funnel(y=[1,2,3,4,5,6,7], x=anchos, text=etiquetas, textinfo="text", textfont=dict(color=col_txt, size=14, family='Arial Black'), marker={"color": colors_barrett, "line": {"width": 2, "color": "white"}}, connector={"visible": False}))
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
        fig_dim = go.Figure(go.Bar(x=vals_dim, y=dims, orientation='h', marker_color=[obtener_etiqueta_color(v)[1] for v in vals_dim], text=[f"{round(v,1)}% - {obtener_etiqueta_color(v)[0]}" for v in vals_dim], textposition='inside'))
        fig_dim.update_layout(xaxis_range=[0, 105], height=400, template="plotly_dark", yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_dim, key="dim")

    # --- 8. INFORME IA (RECUPERADO ÍNTEGRO) ---
    st.divider()
    if st.button("🚀 GENERAR INFORME EJECUTIVO"):
        prompt_maestro = f"""
        Actúa como consultor senior Barrett. Analiza a {lider_sel}. DATOS: {d.to_json()}
        REGLA DE ORO: INICIA DIRECTAMENTE CON EL PUNTO 1. PROHIBIDO SALUDOS O INTRODUCCIONES.
        NOMENCLATURA: L7: LÍDER VISIONARIO, L6: LÍDER MENTOR/SOCIO, L5: LÍDER AUTÉNTICO, L4: FACILITADOR/INNOVADOR, L3: GESTOR DE DESEMPEÑO, L2: GESTOR DE RELACIONES, L1: GESTOR DE CRISIS.
        RÚBRICA: Bajo (<65), Medio (65-75), Alto (75-85), Superior (>85).
        
        ESTRUCTURA Y ANÁLISIS REQUERIDO:
        1. DESCRIPCIÓN POR NIVELES: Orden L1-L7. Describe el nivel basándote en el 'Ponderado Individual' usando las categorías de la RÚBRICA. da una descripción apreciativa de los niveles de liderazgo y categorias según su Nivel de desarrollo de liderazgo de 'Ponderado Individual'
        2. ANÁLISIS DE AUTOVALORACIÓN: Resalta brechas notorias entre Autoevaluacion y Ponderado Individual. Enfatiza los "puntos ciegos positivos" (donde el líder se califica Bajo/Medio pero el entorno(colaboradores, pares y jefe) lo califica Alto/Superior o viceversa).
        3. MATRIZ DE MADUREZ: Analiza diferencias significativas del líder (Ponderado individual) respecto al promedio organizacional(ponderado organizacional), tanto en fortalezas sobresalientes como en áreas con potencial de alineación.
        4. PERFIL DE LIDERAZGO: Estilo predominante según promedios (Liderazgo: {round(liderazgo_prom,1)}%, Transición: {round(transicion_prom,1)}%, Gerencia: {round(gerencia_prom,1)}%) y 3 recomendaciones apreciativas (punto seguido).
        
        FILOSOFÍA: 100% Apreciativa. Tercera persona neutral.
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
                            fig.write_image(path, engine="kaleido", scale=2) 
                            return path
                        
                        # MEJORA: Títulos para las 8 imágenes
                        pdf.set_font('Helvetica', 'B', 9)
                        pdf.text(10, 28, "Distribucion de Energia por Niveles (Auto | Individual | Organizacional)")
                        pdf.image(save_chart(fig_b1, "b1.png"), x=10, y=30, w=60)
                        pdf.image(save_chart(fig_b2, "b2.png"), x=75, y=30, w=60)
                        pdf.image(save_chart(fig_b3, "b3.png"), x=140, y=30, w=60)
                        
                        pdf.text(10, 83, "Radar de Alineacion Triple")
                        pdf.image(save_chart(fig_radar, "radar.png", 500, 400), x=10, y=85, w=95)
                        pdf.text(110, 83, "Madurez Global por Dimensiones")
                        pdf.image(save_chart(fig_dim, "dim.png", 500, 350), x=110, y=95, w=90)
                        
                        pdf.text(15, 163, "Evolucion: Autovaloracion")
                        pdf.image(save_chart(fig_r1, "r1.png", 400, 400), x=15, y=165, w=55)
                        pdf.text(75, 163, "Evolucion: Individual (360)")
                        pdf.image(save_chart(fig_r2, "r2.png", 400, 400), x=75, y=165, w=55)
                        pdf.text(135, 163, "Evolucion: Organizacional")
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

                    output = pdf.output()
                    st.download_button(label="📥 Descargar PDF", data=bytes(output), file_name=f"Reporte_{lider_sel}.pdf", mime="application/pdf")
                except Exception as e: st.error(f"Error PDF: {e}")
