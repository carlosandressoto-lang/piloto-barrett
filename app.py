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
    .leyenda-v3 { display: flex; flex-direction: column; justify-content: space-between; height: 380px; margin-top: 55px; padding-right: 10px; border-right: 1px solid #334155; }
    .item-ley { height: 50px; display: flex; align-items: center; justify-content: flex-end; font-size: 0.85rem; font-weight: bold; color: #94a3b8; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN IA SEGURA ---
try:
    api_key_segura = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key_segura)
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error("Error: Configura 'GEMINI_API_KEY' en los Secrets.")

# --- 3. CARGA DE DATOS (BLINDADA CONTRA 0.0 Y BASURA) ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('Resultados_Gerentes.csv', sep=';', decimal=',')
        df.columns = df.columns.str.strip()
        df['Nombre_Lider'] = df['Nombre_Lider'].astype(str).str.strip()
        
        # FILTRO ROBUSTO: Solo nombres reales
        df = df[df['Nombre_Lider'].notna()]
        df = df[df['Nombre_Lider'] != '0.0']
        df = df[df['Nombre_Lider'] != 'nan']
        df = df[df['Nombre_Lider'] != '']
        
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

    # --- 6. RELOJES (SIMETRÍA Y ALINEACIÓN) ---
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

    # --- 7. RADAR ---
    st.divider()
    st.subheader("Radar de Alineación Estratégica Triple (%)")
    col_center_radar = st.columns([1, 4, 1])[1]
    with col_center_radar:
        fig_radar = go.Figure()
        cats = ['L1','L2','L3','L4','L5','L6','L7']
        for val, name, color in zip([v_auto, v_ind, v_org], ['Auto', 'Individual', 'Organizacional'], ['#3498db', '#2ecc71', '#e74c3c']):
            fig_radar.add_trace(go.Scatterpolar(r=val, theta=cats, fill='toself', name=name, line_color=color))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=600, template="plotly_dark", legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"))
        st.plotly_chart(fig_radar, use_container_width=True, key="radar_final")

    # --- 8. INFORME IA (PROMPT MAESTRO INTEGRAL) ---
    st.divider()
    if st.button("🚀 GENERAR INFORME EJECUTIVO"):
        prompt_maestro = f"""
        Actúa como un experto consultor senior en desarrollo de liderazgo (Richard Barrett). Genera un informe estratégico 360° para {lider_sel}.
        DATOS PARA EL ANÁLISIS: {d.to_json()}
        
        FILOSOFÍA DE FEEDBACK:
        - Enfoque 100% en OPORTUNIDADES y POTENCIAL.
        - Prohibido lenguaje negativo, señalar "errores" o usar etiquetas como "Oportunidad de Desarrollo:".
        - NO incluyas introducciones cordiales. Inicia directamente.

        ESTRUCTURA DEL INFORME:
        1. DESCRIPCIÓN POR NIVELES: Desglose analítico de los 7 niveles (L1 a L7). Identifica el potencial actual basándote en 'Ponderado Individual'.
        2. ANÁLISIS DE AUTOVALORACIÓN: Evalúa la percepción del líder frente a la del entorno.
        3. ANÁLISIS DE PONDERADO INDIVIDUAL: Evalúa las competencias reales observadas por el entorno profesional.
        4. MATRIZ DE MADUREZ: Cruza Individual con Organizacional para determinar la alineación estratégica.
        5. PERFIL DE LIDERAZGO: Define un (1) estilo predominante y propón tres recomendaciones de gran valor estratégico.

        RÚBRICA: 0-65 Bajo | 65-75 Medio | 75-85 Alto | 85-100 Superior
        TERMINOLOGÍA: Emplea terminología técnica de Barrett (Viabilidad, Relaciones, Desempeño, Evolución, etc.).
        """
        try:
            with st.spinner('Analizando datos bajo el modelo Barrett...'):
                response = model.generate_content(prompt_maestro)
                st.markdown(f"### 📋 Informe Ejecutivo: {lider_sel}")
                st.markdown("---")
                st.write(response.text)
        except Exception as e:
            st.error(f"Error IA: {e}")
