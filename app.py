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
    h3 { text-align: center; }
    /* Ajuste de leyenda para evitar descuadres */
    .leyenda-container { display: flex; flex-direction: column; justify-content: space-around; height: 400px; margin-top: 60px; border-right: 2px solid #334155; padding-right: 10px; }
    .leyenda-nivel { height: 50px; display: flex; align-items: center; justify-content: flex-end; font-size: 0.75rem; font-weight: bold; color: #94a3b8; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN IA SEGURA ---
try:
    api_key_segura = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key_segura)
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error("Error: Configura 'GEMINI_API_KEY' en los Secrets de Streamlit.")

# --- 3. CARGA DE DATOS ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('Resultados_Gerentes.csv', sep=';', decimal=',')
        df.columns = df.columns.str.strip()
        df['Nombre_Lider'] = df['Nombre_Lider'].astype(str).str.strip()
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
    lider_sel = st.selectbox("Seleccione el líder para el análisis 360°:", lideres)
    d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

    gerencia_prom = (d.INDIV_L1 + d.INDIV_L2 + d.INDIV_L3) / 3
    transicion_prom = d.INDIV_L4
    liderazgo_prom = (d.INDIV_L5 + d.INDIV_L6 + d.INDIV_L7) / 3

    def obtener_etiqueta_color(v):
        if v < 65: return "Bajo", "#ff4b4b"
        if v < 75: return "Medio", "#f1c40f"
        if v < 85: return "Alto", "#2ecc71"
        return "Superior", "#3498db"

    # --- 5. BARRAS ENERGÍA (%) ---
    st.divider()
    st.subheader("Distribución de Energía por Niveles de Conciencia (%)")
    c1, c2, c3 = st.columns(3)

    def dibujar_barras(vals, titulo, color):
        labels = ['L7-Visionario', 'L6-Mentor', 'L5-Auténtico', 'L4-Facilitador', 'L3-Desempeño', 'L2-Relaciones', 'L1-Crisis']
        v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
        fig = go.Figure(go.Bar(x=v_plot, y=labels, orientation='h', marker_color=color, text=[f"{round(v,1)}%" for v in v_plot], textposition='inside'))
        fig.update_layout(title=dict(text=titulo, x=0.5), xaxis_range=[0, 105], height=350, template="plotly_dark", margin=dict(l=0, r=10, t=40, b=20), yaxis=dict(autorange="reversed"))
        return fig

    with c1: st.plotly_chart(dibujar_barras([d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7], "Autovaloración", "#3498db"), use_container_width=True)
    with c2: st.plotly_chart(dibujar_barras([d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7], "Individual (360)", "#2ecc71"), use_container_width=True)
    with c3: st.plotly_chart(dibujar_barras([d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7], "Referencia Cultura", "#e74c3c"), use_container_width=True)

    # --- 6. RELOJES DE ARENA ---
    st.divider()
    st.subheader("⏳ Evolución del Liderazgo (Escala de Madurez)")
    col_leyenda, r1, r2, r3 = st.columns([0.7, 1, 1, 1])

    with col_leyenda:
        st.markdown('<div class="leyenda-container">', unsafe_allow_html=True)
        niveles = ["L7 - Visionario", "L6 - Mentor", "L5 - Auténtico", "L4 - Facilitador", "L3 - Desempeño", "L2 - Relaciones", "L1 - Crisis"]
        for n in niveles: st.markdown(f'<div class="leyenda-nivel">{n}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    def dibujar_reloj_fijo(vals, titulo):
        anchos = [6, 5, 4, 3.5, 4, 5, 6] 
        colors = ["rgba(111, 66, 193, 0.4)"]*3 + ["rgba(40, 167, 69, 0.4)"] + ["rgba(253, 126, 20, 0.4)"]*3
        etiquetas = [obtener_etiqueta_color(vals[i])[0] for i in [6, 5, 4, 3, 2, 1, 0]]
        col_txt = [obtener_etiqueta_color(vals[i])[1] for i in [6, 5, 4, 3, 2, 1, 0]]
        fig = go.Figure(go.Funnel(y=[7,6,5,4,3,2,1], x=anchos, text=etiquetas, textinfo="text", textfont=dict(color=col_txt, size=14, family='Arial Black'), marker={"color": colors, "line": {"width": 2, "color": "white"}}, connector={"visible": False}))
        fig.update_layout(title=dict(text=titulo, x=0.5), height=450, margin=dict(l=5, r=5, t=50, b=10), yaxis=dict(visible=False, autorange="reversed"), xaxis=dict(visible=False), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        return fig

    with r1: st.plotly_chart(dibujar_reloj_fijo([d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7], "Auto"), use_container_width=True)
    with r2: st.plotly_chart(dibujar_reloj_fijo([d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7], "Individual"), use_container_width=True)
    with r3: st.plotly_chart(dibujar_reloj_fijo([d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7], "Cultura"), use_container_width=True)

    # --- 7. RADAR Y DIMENSIONES ---
    st.divider()
    col_radar, col_dim = st.columns([1.5, 1])
    with col_radar:
        st.subheader("Radar 360°: Alineación de Liderazgo")
        fig_radar = go.Figure()
        cats = ['L1','L2','L3','L4','L5','L6','L7']
        for val, name, color in zip([[d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7], [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7], [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]], ['Auto', 'Individual', 'Organizacional'], ['#3498db', '#2ecc71', '#e74c3c']):
            fig_radar.add_trace(go.Scatterpolar(r=val, theta=cats, fill='toself', name=name, line_color=color))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=500, template="plotly_dark", legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_radar, use_container_width=True)

    with col_dim:
        st.subheader("Madurez Global por Dimensiones")
        dims, vals_dim = ['Liderazgo (L5-L7)', 'Transición (L4)', 'Gerencia (L1-L3)'], [liderazgo_prom, transicion_prom, gerencia_prom]
        colors_dim = [obtener_etiqueta_color(v)[1] for v in vals_dim]
        labels_dim = [obtener_etiqueta_color(v)[0] for v in vals_dim]
        fig_dim = go.Figure(go.Bar(x=vals_dim, y=dims, orientation='h', marker_color=colors_dim, text=[f"{round(v,1)}% - {l}" for v, l in zip(vals_dim, labels_dim)], textposition='inside'))
        fig_dim.update_layout(xaxis_range=[0, 105], height=400, template="plotly_dark", yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_dim, use_container_width=True)

    # --- 8. INFORME IA (SIN ALUCINACIONES DE DATOS) ---
    st.divider()
    if st.button("🚀 GENERAR ANÁLISIS ESTRATÉGICO 360°"):
        prompt_maestro = f"""
        Actúa como un experto consultor senior en desarrollo de liderazgo especializado en el Modelo de Barrett. 
        Analiza a {lider_sel} bajo una óptica de Evaluación 360° de Liderazgo.

        DATOS FUENTE (Únicos datos reales):
        {d.to_json()}
        - Dimensiones Agrupadas: Gerencia: {round(gerencia_prom,1)}%, Transición: {round(transicion_prom,1)}%, Liderazgo: {round(liderazgo_prom,1)}%.

        REGLAS DE ORO (ESTRICTO):
        1. NO INVENTES COMPARACIONES: En el punto 1 (Descripción por niveles), usa ÚNICAMENTE el dato de 'Ponderado Individual'. No menciones la Autovaloración ni el Organizacional en este punto; eso déjalo para las secciones posteriores de brechas.
        2. NO COMPETENCIAS/DESEMPEÑO: Habla exclusivamente de evolución de la consciencia y liderazgo.
        3. CERO BASURA: Inicia directamente con el punto 1. Sin fechas, preámbulos o nombres de consultores.
        4. TONO: Apreciativo y basado en potencial.

        ESTRUCTURA:
        1. ANÁLISIS DE EVOLUCIÓN POR NIVELES (PONDERADO INDIVIDUAL): Describe qué significa el puntaje del 'Ponderado Individual' para cada uno de los 7 niveles (L1-L7). Identifica talentos y rutas para elevar la consciencia.
        2. BRECHAS DE CONSCIENCIA (AUTO vs INDIVIDUAL): Analiza cómo se percibe el líder frente a cómo lo ve su entorno. Destaca puntos de acuerdo y áreas de autodescubrimiento.
        3. ALINEACIÓN CON LA CULTURA (INDIVIDUAL vs ORGANIZACIONAL): Explica cómo el perfil del líder se integra o impulsa los valores de la organización.
        4. EQUILIBRIO DE DIMENSIONES Y RUTA ESTRATÉGICA: Analiza el equilibrio entre Gerencia, Transición y Liderazgo usando los % promediados. Entrega 3 recomendaciones tácticas de alto valor para su transformación.

        RÚBRICA: 0-65 Bajo, 66-75 Medio, 76-85 Alto, 85-100 Superior.
        NOMENCLATURA: L1 Líder de Crisis/Viabilidad, L2 Líder de Relaciones, L3 Líder de Desempeño, L4 Líder Facilitador, L5 Líder Auténtico, L6 Líder Mentor/Socio, L7 Líder Visionario.
        """
        try:
            with st.spinner('Analizando consciencia...'):
                response = model.generate_content(prompt_maestro)
                st.markdown(f"## Análisis Estratégico 360°: {lider_sel}")
                st.markdown("---")
                st.write(response.text)
        except Exception as e:
            st.error(f"Error IA: {e}")
