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
    st.title("🏛️ Índice del equilibrio - Dashboard LDR Barrett")
    lideres = sorted(df['Nombre_Lider'].unique())
    lider_sel = st.selectbox("Seleccione el líder para el análisis detallado:", lideres)
    d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

    # Cálculos de dimensiones agrupadas
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

    with c1: st.plotly_chart(dibujar_barras(v_auto, "Autovaloración", "#3498db"), use_container_width=True, key="b1")
    with c2: st.plotly_chart(dibujar_barras(v_ind, "Individual (360)", "#2ecc71"), use_container_width=True, key="b2")
    with c3: st.plotly_chart(dibujar_barras(v_org, "Promedio Organizacional", "#e74c3c"), use_container_width=True, key="b3")

    # --- 6. RELOJES ---
    st.divider()
    st.subheader("⏳ Evolución del Liderazgo (Semáforo de Madurez)")
    
    def dibujar_reloj_limpio(vals):
        anchos = [6, 5, 4, 3.2, 4, 5, 6] 
        v_rev = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
        etiquetas = [obtener_etiqueta_color(v)[0] for v in v_rev]
        colores_texto = [obtener_etiqueta_color(v)[1] for v in v_rev]
        fig = go.Figure(go.Funnel(y=[1,2,3,4,5,6,7], x=anchos, text=etiquetas, textinfo="text", textfont=dict(color=colores_texto, size=14, family='Arial Black'), marker={"color": "rgba(64, 64, 64, 0.4)", "line": {"width": 2, "color": "white"}}, connector={"visible": False}))
        fig.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(visible=False), xaxis=dict(visible=False), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        return fig

    cl, cr1, cr2, cr3 = st.columns([1, 1, 1, 1])
    with cl:
        st.markdown('<div class="titulo-col">Nivel Barrett</div>', unsafe_allow_html=True)
        st.markdown('<div class="leyenda-v3">' + ''.join([f'<div class="item-ley">{n}</div>' for n in ["L7 - Visionario", "L6 - Mentor", "L5 - Auténtico", "L4 - Facilitador", "L3 - Desempeño", "L2 - Relaciones", "L1 - Crisis"]]) + '</div>', unsafe_allow_html=True)
    with cr1:
        st.markdown('<div class="titulo-col">Autovaloración</div>', unsafe_allow_html=True)
        st.plotly_chart(dibujar_reloj_limpio(v_auto), use_container_width=True, key="r1")
    with cr2:
        st.markdown('<div class="titulo-col">Individual</div>', unsafe_allow_html=True)
        st.plotly_chart(dibujar_reloj_limpio(v_ind), use_container_width=True, key="r2")
    with cr3:
        st.markdown('<div class="titulo-col">Organizacional</div>', unsafe_allow_html=True)
        st.plotly_chart(dibujar_reloj_limpio(v_org), use_container_width=True, key="r3")

    # --- 7. RADAR Y DIMENSIONES (RECUPERADOS) ---
    st.divider()
    col_radar, col_dim = st.columns([1.5, 1])
    with col_radar:
        st.subheader("Radar de Alineación Triple (%)")
        fig_radar = go.Figure()
        cats = ['L1','L2','L3','L4','L5','L6','L7']
        fig_radar.add_trace(go.Scatterpolar(r=v_auto, theta=cats, fill='toself', name='Auto', line_color='#3498db'))
        fig_radar.add_trace(go.Scatterpolar(r=v_ind, theta=cats, fill='toself', name='Individual', line_color='#2ecc71'))
        fig_radar.add_trace(go.Scatterpolar(r=v_org, theta=cats, fill='toself', name='Organizacional', line_color='#e74c3c'))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=500, template="plotly_dark", legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"))
        st.plotly_chart(fig_radar, use_container_width=True, key="radar_main")

    with col_dim:
        st.subheader("Madurez Global por Dimensiones")
        dims = ['Liderazgo (L5-L7)', 'Transición (L4)', 'Gerencia (L1-L3)']
        vals_dim = [liderazgo_prom, transicion_prom, gerencia_prom]
        fig_dim = go.Figure(go.Bar(x=vals_dim, y=dims, orientation='h', marker_color=[obtener_etiqueta_color(v)[1] for v in vals_dim], text=[f"{round(v,1)}% - {obtener_etiqueta_color(v)[0]}" for v in vals_dim], textposition='inside'))
        fig_dim.update_layout(xaxis_range=[0, 105], height=400, template="plotly_dark", yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_dim, use_container_width=True, key="bar_dim")

    # --- 8. INFORME IA CON NOMENCLATURA OBLIGATORIA ---
    st.divider()
    if st.button("🚀 GENERAR INFORME EJECUTIVO"):
        prompt_maestro = f"""
        Actúa como consultor senior Barrett. Analiza al líder {lider_sel}.
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
        1. DESCRIPCIÓN POR NIVELES: Orden L1 a L7 obligatorio. Usa la NOMENCLATURA OBLIGATORIA y analiza 'Ponderado Individual'.
        2. ANÁLISIS DE AUTOVALORACIÓN: Autoconciencia vs Entorno.
        3. ANÁLISIS DE PONDERADO INDIVIDUAL: Maestría observada.
        4. MATRIZ DE MADUREZ: Alineación estratégica Individual vs Organizacional.
        5. PERFIL DE LIDERAZGO: Recomendaciones estratégicas (punto seguido, filosofía apreciativa).
        """
        try:
            with st.spinner('Procesando...'):
                response = model.generate_content(prompt_maestro)
                st.markdown(f"### 📋 Informe Ejecutivo: {lider_sel}")
                st.markdown("---")
                st.write(response.text)
        except Exception as e:
            st.error(f"Error IA: {e}")
