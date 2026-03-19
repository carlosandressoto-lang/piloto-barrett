import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
from fpdf import FPDF
import io

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0e1117; color: white !important; font-family: 'Helvetica Neue', sans-serif; }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stSelectbox label { color: white !important; }
    .stSelectbox div[data-baseweb="select"] { color: white !important; background-color: #1e293b; }
    .block-container { padding-top: 1rem; }
    h1 { color: #BFDBFE !important; text-align: center; }
    .titulo-columna { text-align: center; color: white; font-weight: bold; font-size: 1.1rem; margin-bottom: 20px; height: 30px; }
    .leyenda-v2 { display: flex; flex-direction: column; justify-content: space-between; height: 380px; margin-top: 10px; padding-right: 10px; border-right: 1px solid #334155; }
    .item-leyenda { height: 50px; display: flex; align-items: center; justify-content: flex-end; font-size: 0.85rem; font-weight: bold; color: #94a3b8; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN IA (REGRESAMOS A 2.5 FLASH) ---
try:
    api_key_segura = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key_segura)
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error("Error: Revisa tu API KEY en los Secrets.")

# --- 3. CARGA DE DATOS ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('Resultados_Gerentes.csv', sep=';', decimal=',')
        df.columns = df.columns.str.strip()
        df['Nombre_Lider'] = df['Nombre_Lider'].astype(str).str.strip()
        df = df[(df['Nombre_Lider'] != '0.0') & (df['Nombre_Lider'] != 'nan')]
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
    lider_sel = st.selectbox("Seleccione el líder:", lideres)
    d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

    gerencia_prom = (d.INDIV_L1 + d.INDIV_L2 + d.INDIV_L3) / 3
    transicion_prom = d.INDIV_L4
    liderazgo_prom = (d.INDIV_L5 + d.INDIV_L6 + d.INDIV_L7) / 3

    def obtener_etiqueta_color(v):
        if v < 65: return "Bajo", "#ff4b4b"
        if v < 75: return "Medio", "#f1c40f"
        if v < 85: return "Alto", "#2ecc71"
        return "Superior", "#3498db"

    # --- GRAFICOS (VISUAL PERFECTA) ---
    st.divider()
    c1, c2, c3 = st.columns(3)
    def dibujar_barras(vals, titulo, color):
        labels = ['L7-Visionario', 'L6-Mentor', 'L5-Auténtico', 'L4-Facilitador', 'L3-Desempeño', 'L2-Relaciones', 'L1-Crisis']
        fig = go.Figure(go.Bar(x=[vals[6],vals[5],vals[4],vals[3],vals[2],vals[1],vals[0]], y=labels, orientation='h', marker_color=color, text=[f"{round(v,1)}%" for v in [vals[6],vals[5],vals[4],vals[3],vals[2],vals[1],vals[0]]], textposition='inside'))
        fig.update_layout(title=dict(text=titulo, x=0.5), height=350, template="plotly_dark", yaxis=dict(autorange="reversed"))
        return fig
    with c1: st.plotly_chart(dibujar_barras([d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7], "Autovaloración", "#3498db"), use_container_width=True)
    with c2: st.plotly_chart(dibujar_barras([d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7], "Individual", "#2ecc71"), use_container_width=True)
    with c3: st.plotly_chart(dibujar_barras([d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7], "Cultura", "#e74c3c"), use_container_width=True)

    st.divider()
    st.subheader("⏳ Evolución del Liderazgo (Escala de Madurez)")
    col_l, col_r1, col_r2, col_r3 = st.columns([1, 1, 1, 1])
    with col_l:
        st.markdown('<div class="titulo-columna">Nivel Barrett</div>', unsafe_allow_html=True)
        st.markdown('<div class="leyenda-v2">' + ''.join([f'<div class="item-leyenda">{n}</div>' for n in ["L7 - Visionario", "L6 - Mentor", "L5 - Auténtico", "L4 - Facilitador", "L3 - Desempeño", "L2 - Relaciones", "L1 - Crisis"]]) + '</div>', unsafe_allow_html=True)

    def dibujar_reloj_cuadro(vals):
        anchos = [6, 5, 4, 3.2, 4, 5, 6] 
        colors_faded = ["rgba(111, 66, 193, 0.4)"]*3 + ["rgba(40, 167, 69, 0.4)"] + ["rgba(253, 126, 20, 0.4)"]*3
        vals_rev = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
        etiquetas = [obtener_etiqueta_color(v)[0] for v in vals_rev]
        colores_t = [obtener_etiqueta_color(v)[1] for v in vals_rev]
        fig = go.Figure(go.Funnel(y=[7,6,5,4,3,2,1], x=anchos, text=etiquetas, textinfo="text", textfont=dict(color=colores_t, size=14, family='Arial Black'), marker={"color": colors_faded, "line": {"width": 2, "color": "white"}}, connector={"visible": False}))
        fig.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(visible=False, autorange="reversed"), xaxis=dict(visible=False), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        return fig
    with col_r1:
        st.markdown('<div class="titulo-columna">Autovaloración</div>', unsafe_allow_html=True)
        st.plotly_chart(dibujar_reloj_cuadro([d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]), use_container_width=True)
    with col_r2:
        st.markdown('<div class="titulo-columna">Individual</div>', unsafe_allow_html=True)
        st.plotly_chart(dibujar_reloj_cuadro([d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]), use_container_width=True)
    with col_r3:
        st.markdown('<div class="titulo-columna">Organizacional</div>', unsafe_allow_html=True)
        st.plotly_chart(dibujar_reloj_cuadro([d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]), use_container_width=True)

    # --- INFORME IA Y PDF ---
    st.divider()
    if st.button("🚀 GENERAR ANÁLISIS ESTRATÉGICO 360°"):
        prompt_maestro = f"""
        Actúa como experto consultor senior Barrett. Genera un informe estratégico 360° de {lider_sel}.
        DATOS: {d.to_json()}
        NOMENCLATURA OBLIGATORIA (L1-L7): GESTOR DE CRISIS, LÍDER DE RELACIONES, LÍDER DE DESEMPEÑO, LÍDER FACILITADOR, LÍDER AUTÉNTICO, LÍDER MENTOR, LÍDER VISIONARIO.
        REGLAS: Inicia directamente, títulos limpios (1. ANÁLISIS DE EVOLUCIÓN POR NIVELES, 2. SINTONÍA DE CONSCIENCIA, 3. RESULTADO ORGANIZACIONAL, 4. RUTA DE TRANSFORMACIÓN), orden L1 a L7, filosofía 100% apreciativa, sin etiquetas de error.
        """
        try:
            with st.spinner('Procesando...'):
                response = model.generate_content(prompt_maestro)
                informe_texto = response.text
                st.markdown(f"## Informe: {lider_sel}")
                st.write(informe_texto)
                
                # Función para crear PDF
                def crear_pdf(texto, nombre):
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 16)
                    pdf.cell(0, 10, f"Informe de Liderazgo Barrett: {nombre}", ln=True, align='C')
                    pdf.ln(10)
                    pdf.set_font("Arial", size=11)
                    # Limpieza básica de carácteres especiales para PDF
                    pdf.multi_cell(0, 10, texto.encode('latin-1', 'ignore').decode('latin-1'))
                    return pdf.output(dest='S').encode('latin-1')

                pdf_bytes = crear_pdf(informe_texto, lider_sel)
                st.download_button(label="📥 DESCARGAR INFORME EN PDF", data=pdf_bytes, file_name=f"Informe_Barrett_{lider_sel}.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"Error: {e}")
