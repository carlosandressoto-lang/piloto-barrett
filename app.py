import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

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
    
    /* AJUSTE DE LEYENDA PARA ALINEACIÓN CON RELOJES */
    .leyenda-v3 {
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        height: 340px; /* Altura ajustada a la escala del funnel */
        margin-top: 35px; /* Alineación con el primer bloque superior */
        padding-right: 10px;
        border-right: 1px solid #334155;
    }
    .item-ley {
        height: 48px; /* Altura proporcional a cada nivel del funnel */
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
    lider_sel = st.selectbox("Seleccione el líder para el análisis estratégico:", lideres)
    d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

    v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
    v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
    v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]

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

    with c1: st.plotly_chart(dibujar_barras(v_auto, "Autovaloración", "#3498db"), use_container_width=True, key="bar_auto")
    with c2: st.plotly_chart(dibujar_barras(v_ind, "Individual (360)", "#2ecc71"), use_container_width=True, key="bar_ind")
    with c3: st.plotly_chart(dibujar_barras(v_org, "Promedio Organizacional", "#e74c3c"), use_container_width=True, key="bar_org")

    # --- 6. RELOJES ---
    st.divider()
    st.subheader("⏳ Evolución del Liderazgo (Semáforo de Madurez)")

    def obtener_etiqueta_color(v):
        if v < 65: return "Bajo", "#ff4b4b"
        if v < 75: return "Medio", "#f1c40f"
        if v < 85: return "Alto", "#2ecc71"
        return "Superior", "#3498db"

    def dibujar_reloj_limpio(vals):
        anchos_hourglass = [6, 5, 4, 3.2, 4, 5, 6] 
        colors_barrett_faded = ["rgba(111, 66, 193, 0.4)"]*3 + ["rgba(40, 167, 69, 0.4)"] + ["rgba(253, 126, 20, 0.4)"]*3
        v_rev = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
        etiquetas = [obtener_etiqueta_color(v)[0] for v in v_rev]
        colores_texto = [obtener_etiqueta_color(v)[1] for v in v_rev]

        fig = go.Figure(go.Funnel(
            y=[1,2,3,4,5,6,7], x=anchos_hourglass, text=etiquetas, textinfo="text",
            textfont=dict(color=colores_texto, size=14, family='Arial Black'),
            marker={"color": colors_barrett_faded, "line": {"width": 2, "color": "white"}},
            connector={"visible": False}
        ))
        fig.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(visible=False, autorange="reversed"), xaxis=dict(visible=False), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        return fig

    col_l, col_r1, col_r2, col_r3 = st.columns([1, 1, 1, 1])
    with col_l:
        st.markdown('<div class="titulo-col">Nivel Barrett</div>', unsafe_allow_html=True)
        st.markdown('<div class="leyenda-v3">' + ''.join([f'<div class="item-ley">{n}</div>' for n in ["L7 - Visionario", "L6 - Mentor", "L5 - Auténtico", "L4 - Facilitador", "L3 - Desempeño", "L2 - Relaciones", "L1 - Crisis"]]) + '</div>', unsafe_allow_html=True)
    with col_r1:
        st.markdown('<div class="titulo-col">Autovaloración</div>', unsafe_allow_html=True)
        st.plotly_chart(dibujar_reloj_limpio(v_auto), use_container_width=True, key="re_auto")
    with col_r2:
        st.markdown('<div class="titulo-col">Individual</div>', unsafe_allow_html=True)
        st.plotly_chart(dibujar_reloj_limpio(v_ind), use_container_width=True, key="re_ind")
    with col_r3:
        st.markdown('<div class="titulo-col">Organizacional</div>', unsafe_allow_html=True)
        st.plotly_chart(dibujar_reloj_limpio(v_org), use_container_width=True, key="re_org")

    # --- 8. INFORME IA (PROMPT MAESTRO CORREGIDO CON NOMENCLATURA) ---
    st.divider()
    if st.button("🚀 GENERAR INFORME EJECUTIVO"):
        prompt_maestro = f"""
        CONTEXTO: Actúa como consultor senior Barrett. Analiza al líder {lider_sel}.
        DATOS: {d.to_json()}

        REGLA DE NOMENCLATURA OBLIGATORIA (No puedes usar otros nombres):
        - Nivel 7: LÍDER VISIONARIO - Propósito de vivir
        - Nivel 6: LÍDER MENTOR/SOCIO - Trabajo en la colaboración
        - Nivel 5: LÍDER AUTÉNTICO - Autoexpresión genuina
        - Nivel 4: FACILITADOR/INNOVADOR - Evolución de forma valiente
        - Nivel 3: GESTOR DE DESEMPEÑO - Logrando la excelencia
        - Nivel 2: GESTOR DE RELACIONES - Apoyo de relaciones
        - Nivel 1: GESTOR DE CRISIS - Garantizar visibilidad

        FILOSOFÍA: 100% Apreciativa (Oportunidades y Potencial). Sin lenguaje negativo.

        ESTRUCTURA:
        1. DESCRIPCIÓN POR NIVELES: Desglose del Nivel 1 al Nivel 7 en orden estrictamente ascendente. Para cada nivel usa la NOMENCLATURA OBLIGATORIA arriba definida y analiza el dato de 'Ponderado Individual'.
        2. ANÁLISIS DE AUTOVALORACIÓN: Percepción del líder vs entorno.
        3. ANÁLISIS DE PONDERADO INDIVIDUAL: Competencias reales 360°.
        4. MATRIZ DE MADUREZ: Alineación estratégica Individual vs Organizacional.
        5. PERFIL DE LIDERAZGO: 1 estilo predominante y 3 recomendaciones estratégicas.
        """
        try:
            with st.spinner('Procesando análisis Barrett...'):
                response = model.generate_content(prompt_maestro)
                st.markdown(f"### 📋 Informe Ejecutivo: {lider_sel}")
                st.markdown("---")
                st.write(response.text)
        except Exception as e:
            st.error(f"Error IA: {e}")
