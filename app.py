import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
# --- NUEVAS IMPORTACIONES PARA PDF (AÑADIR fpdf2 Y kaleido A requirements.txt) ---
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
    d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

    # Cálculos de dimensiones
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
        colors_barrett = [
            "rgba(111, 66, 193, 0.5)", "rgba(111, 66, 193, 0.5)", "rgba(111, 66, 193, 0.5)", 
            "rgba(40, 167, 69, 0.5)", 
            "rgba(253, 126, 20, 0.5)", "rgba(253, 126, 20, 0.5)", "rgba(253, 126, 20, 0.5)"
        ]
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
        st.markdown('<div class="titulo-col">Autovaloración</div>', unsafe_allow_html=True)
        st.plotly_chart(dibujar_reloj_barrett(v_auto), key="r1")
    with cr2:
        st.markdown('<div class="titulo-col">Individual</div>', unsafe_allow_html=True)
        st.plotly_chart(dibujar_reloj_barrett(v_ind), key="r2")
    with cr3:
        st.markdown('<div class="titulo-col">Organizacional</div>', unsafe_allow_html=True)
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

    # --- 8. INFORME IA (RECUPERADO ÍNTEGRO) ---
    st.divider()
    
    # Manejo de memoria para no gastar API innecesariamente
    if "informe_cache" not in st.session_state: st.session_state.informe_cache = {}
    
    if st.button("🚀 GENERAR INFORME EJECUTIVO"):
        prompt_maestro = f"""
        Actúa como un experto consultor senior en desarrollo de liderazgo (Richard Barrett). Genera un informe estratégico 360° para {lider_sel}.
        DATOS: {d.to_json()}

        REGLA DE NOMENCLATURA OBLIGATORIA (PROHIBIDO OTROS NOMBRES):
        - Nivel 7: LÍDER VISIONARIO - Propósito de vivir
        - Nivel 6: LÍDER MENTOR/SOCIO - Trabajo en la colaboración
        - Nivel 5: LÍDER AUTÉNTICO - Autoexpresión genuina
        - Nivel 4: FACILITADOR/INNOVADOR - Evolución de forma valiente
        - Nivel 3: GESTOR DE DESEMPEÑO - Logrando la excelencia
        - Nivel 2: GESTOR DE RELACIONES - Apoyo de relaciones
        - Nivel 1: GESTOR DE CRISIS - Garantizar visibilidad

        ESTRUCTURA DEL INFORME:
        1. DESCRIPCIÓN POR NIVELES: Desglose del Nivel 1 al Nivel 7 en orden estrictamente ascendente. Usa la NOMENCLATURA OBLIGATORIA y analiza el impacto según el 'Ponderado Individual'.
        2. ANÁLISIS DE AUTOVALORACIÓN: Autoconciencia frente a la visión del entorno (Ponderado individual).
        3. MATRIZ DE MADUREZ: Alineación estratégica Individual (Ponderado Individual) vs Organizacional(Ponderado organizacional). No es como la organización lo ve es como esta su evaluación 360° respecto al promedio organizacional
        4. PERFIL DE LIDERAZGO: Definición de estilo según predominancia de dimensión (Liderazgo, Transición, Gerencia) y equilibrio de las 3 dimensions, en base a ese equilibrio entrega 3 recomendaciones apreciativas (punto seguido).

        FILOSOFÍA: 100% Apreciativa. Sin lenguaje negativo ni etiquetas de error. Inicia directamente sin preámbulos.
        """
        try:
            with st.spinner('Analizando datos...'):
                response = model.generate_content(prompt_maestro)
                st.session_state.informe_cache[lider_sel] = response.text
        except Exception as e:
            st.error(f"Error IA: {e}")

    # Mostrar informe si existe en memoria para este líder
    if lider_sel in st.session_state.informe_cache:
        texto_informe = st.session_state.informe_cache[lider_sel]
        st.markdown(f"### 📋 Informe Ejecutivo: {lider_sel}")
        st.markdown("---")
        st.write(texto_informe)
        
        # Botón de descarga
        st.download_button(
            label="📥 DESCARGAR INFORME (TXT)",
            data=texto_informe,
            file_name=f"Informe_Barrett_{lider_sel}.txt",
            mime="text/plain"
        )

# --- 9. MÓDULO DE EXPORTACIÓN A PDF (AÑADIDO AL FINAL, SIN TOCAR LO ANTERIOR) ---
st.divider()
st.subheader("📥 Exportar Reporte Completo")

# Función técnica para generar el PDF (ejecutada solo al pulsar el botón)
def generar_pdf_completo(lider_sel, d, liderazgo_prom, transicion_prom, gerencia_prom, texto_informe):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # --- PÁGINA 1: PORTADA Y GRÁFICOS DE BARRAS ---
    pdf.add_page()
    # Encabezado corporativo simulado
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(14, 17, 23) # Color oscuro del fondo del dashboard
    pdf.cell(0, 10, 'REPORTE DE LIDERAZGO MODELO BARRETT', ln=True, align='C')
    pdf.set_font('Helvetica', '', 12)
    pdf.cell(0, 10, f'Líder Evaluado: {lider_sel}', ln=True, align='C')
    pdf.ln(5)
    
    # Título Sección 1
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, '1. Distribución de Energía por Niveles (%)', ln=True)
    pdf.ln(2)
    
    # Generar imágenes temporales de los gráficos de barras usando kaleido
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_b1, \
         tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_b2, \
         tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_b3:
        
        # Guardar las figuras estáticas como PNG
        # Recreamos las figuras brevemente sin el template dark para que se vean bien en PDF blanco
        def fig_to_png(vals, titulo, tmp_file):
            labels = ['L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 'L4 - Facilitador', 'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis']
            v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
            fig = go.Figure(go.Bar(x=v_plot, y=labels, orientation='h', text=[f"{round(v,1)}%" for v in v_plot], textposition='inside'))
            fig.update_layout(title=dict(text=titulo, x=0.5), yaxis=dict(autorange="reversed"), width=700, height=350, margin=dict(l=80, r=20, t=40, b=20))
            fig.write_image(tmp_file.name, engine="kaleido")

        fig_to_png(v_auto, "Autovaloración", tmp_b1)
        fig_to_png(v_ind, "Individual (360)", tmp_b2)
        fig_to_png(v_org, "Promedio Organizacional", tmp_b3)
        
        # Insertar imágenes en PDF
        pdf.image(tmp_b1.name, x=10, w=100)
        pdf.image(tmp_b2.name, x=110, y=pdf.get_y()-65, w=100) # Ajuste manual de posición Y
        pdf.ln(5)
        pdf.image(tmp_b3.name, x=60, w=100)
        
    # --- PÁGINA 2: RADAR Y DIMENSIONES ---
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, '2. Radar de Alineación y Madurez Global', ln=True)
    pdf.ln(2)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_radar, \
         tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_dim:
        
        # Recrear Radar estático
        fig_radar_pdf = go.Figure()
        cats = ['L1','L2','L3','L4','L5','L6','L7']
        # Colores directos para PDF blanco
        colors = ['#3498db', '#2ecc71', '#e74c3c']
        for val, name, col in zip([v_auto, v_ind, v_org], ['Auto', 'Individual', 'Organizacional'], colors):
            fig_radar_pdf.add_trace(go.Scatterpolar(r=val, theta=cats, fill='toself', name=name, line_color=col))
        fig_radar_pdf.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), width=700, height=500, legend=dict(orientation="h", x=0.5, xanchor="center"))
        fig_radar_pdf.write_image(tmp_radar.name, engine="kaleido")
        
        # Recrear Dimensiones estáticas
        dims = ['Liderazgo (L5-L7)', 'Transición (L4)', 'Gerencia (L1-L3)']
        vals_dim = [liderazgo_prom, transicion_prom, gerencia_prom]
        # Colores directos para PDF
        def get_col_pdf(v):
            if v < 65: return "#ff4b4b"
            if v < 75: return "#f1c40f"
            if v < 85: return "#2ecc71"
            return "#3498db"
        
        fig_dim_pdf = go.Figure(go.Bar(x=vals_dim, y=dims, orientation='h', marker_color=[get_col_pdf(v) for v in vals_dim], text=[f"{round(v,1)}%" for v in vals_dim], textposition='inside'))
        fig_dim_pdf.update_layout(xaxis_range=[0, 105], yaxis=dict(autorange="reversed"), width=700, height=350, title="Madurez Global", margin=dict(l=100))
        fig_dim_pdf.write_image(tmp_dim.name, engine="kaleido")
        
        # Insertar
        pdf.image(tmp_radar.name, x=10, y=30, w=110)
        pdf.image(tmp_dim.name, x=120, y=50, w=85)
        
    # --- PÁGINA 3: INFORME IA ---
    if texto_informe:
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, '3. Informe Ejecutivo de Liderazgo', ln=True)
        pdf.ln(5)
        pdf.set_font('Helvetica', '', 10)
        # Limpieza de caracteres no compatibles con latin-1
        texto_limpio = texto_informe.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 7, texto_limpio)

    return pdf.output()

# Lógica del botón de PDF
if lider_sel in st.session_state.informe_cache:
    texto_para_pdf = st.session_state.informe_cache[lider_sel]
    
    if st.button("📄 GENERAR REPORTE COMPLETO EN PDF"):
        with st.spinner('Generando PDF profesional con gráficas...'):
            try:
                pdf_output = generar_pdf_completo(lider_sel, d, liderazgo_prom, transicion_prom, gerencia_prom, texto_para_pdf)
                
                # Botón de descarga final
                st.download_button(
                    label="📥 Descargar Reporte PDF",
                    data=bytes(pdf_output),
                    file_name=f"Reporte_Integral_Barrett_{lider_sel.replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Error técnico generando PDF: {e}")
                st.info("Asegúrate de tener 'fpdf2' y 'kaleido' instalados en el entorno.")
else:
    st.info("Primero debes hacer clic en 'GENERAR INFORME EJECUTIVO' para poder exportar el PDF completo.")
