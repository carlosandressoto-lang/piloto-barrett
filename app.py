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
    h1 { color: #BFDBFE !important; }
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
    lider_sel = st.selectbox("Seleccione el líder para el análisis detallado:", lideres)
    d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

    gerencia_prom = (d.INDIV_L1 + d.INDIV_L2 + d.INDIV_L3) / 3
    transicion_prom = d.INDIV_L4
    liderazgo_prom = (d.INDIV_L5 + d.INDIV_L6 + d.INDIV_L7) / 3

    def obtener_etiqueta_color(v):
        if v < 65: return "Bajo", "#ff4b4b"
        if v < 75: return "Medio", "#f1c40f"
        if v < 85: return "Alto", "#2ecc71"
        return "Superior", "#3498db"

    # --- 5. BARRAS ORIGINALES (%) ---
    st.divider()
    st.subheader("Distribución de Energía por Niveles de Conciencia (%)")
    c1, c2, c3 = st.columns(3)

    def dibujar_barras(vals, titulo, color):
        labels = ['L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 'L4 - Facilitador', 'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis']
        v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
        fig = go.Figure(go.Bar(x=v_plot, y=labels, orientation='h', marker_color=color, text=[f"{round(v,1)}%" for v in v_plot], textposition='inside'))
        fig.update_layout(title=dict(text=titulo), xaxis_range=[0, 105], height=350, template="plotly_dark", margin=dict(l=0, r=10, t=40, b=20), yaxis=dict(autorange="reversed"))
        return fig

    with c1: st.plotly_chart(dibujar_barras([d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7], "Autovaloración", "#3498db"), use_container_width=True)
    with c2: st.plotly_chart(dibujar_barras([d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7], "Individual (360)", "#2ecc71"), use_container_width=True)
    with c3: st.plotly_chart(dibujar_barras([d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7], "Promedio Organizacional", "#e74c3c"), use_container_width=True)

    # --- 6. RELOJES DE ARENA (RESPONSIVIDAD L4 CORREGIDA) ---
    st.divider()
    st.subheader("⏳ Nivel de Desarrollo Barrett (Semáforo de Desempeño)")

    def dibujar_reloj_semáforo(vals, titulo):
        levels = ['L7 - Líder Visionario', 'L6 - Líder Mentor/Socio', 'L5 - Líder Auténtico', 'L4 - Líder Facilitador', 'L3 - Líder de Desempeño', 'L2 - Líder de Relaciones', 'L1 - Líder de Crisis/Viabilidad']
        # Ensanchamos L4 (2.2 -> 3.0) para asegurar que el texto "Superior" entre siempre
        anchos_hourglass = [6, 5, 4, 3.2, 4, 5, 6] 
        colors_faded = ["rgba(111, 66, 193, 0.4)"]*3 + ["rgba(40, 167, 69, 0.4)"] + ["rgba(253, 126, 20, 0.4)"]*3
        etiquetas = [obtener_etiqueta_color(vals[i])[0] for i in [6, 5, 4, 3, 2, 1, 0]]
        colores_t = [obtener_etiqueta_color(vals[i])[1] for i in [6, 5, 4, 3, 2, 1, 0]]

        fig = go.Figure(go.Funnel(
            y=levels, x=anchos_hourglass, text=etiquetas, textinfo="text",
            textfont=dict(color=colores_t, size=14, family='Arial Black'),
            marker={"color": colors_faded, "line": {"width": 2, "color": "white"}},
            connector={"line": {"color": "white", "width": 1}, "fillcolor": "rgba(200, 200, 200, 0.1)"}
        ))
        fig.update_layout(title=dict(text=titulo, x=0.5), height=500, margin=dict(l=220, r=20, t=50, b=50), yaxis=dict(autorange="reversed"), xaxis=dict(visible=False), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        return fig

    r1, r2, r3 = st.columns(3)
    with r1: st.plotly_chart(dibujar_reloj_semáforo([d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7], "Autopercepción Barrett"), use_container_width=True)
    with r2: st.plotly_chart(dibujar_reloj_semáforo([d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7], "Competencia Individual"), use_container_width=True)
    with r3: st.plotly_chart(dibujar_reloj_semáforo([d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7], "Cultura Organizacional"), use_container_width=True)

    # --- 7. RADAR Y DIMENSIONES ---
    st.divider()
    col_radar, col_dim = st.columns([1.5, 1])
    with col_radar:
        st.subheader("Radar de Alineación Estratégica Triple (%)")
        fig_radar = go.Figure()
        cats = ['L1','L2','L3','L4','L5','L6','L7']
        for val, name, color in zip([[d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7], [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7], [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]], ['Auto', 'Individual', 'Organizacional'], ['#3498db', '#2ecc71', '#e74c3c']):
            fig_radar.add_trace(go.Scatterpolar(r=val, theta=cats, fill='toself', name=name, line_color=color))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=500, template="plotly_dark", legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_radar, use_container_width=True)

    with col_dim:
        st.subheader("Madurez por Dimensiones (Promedio Individual)")
        dims = ['Liderazgo (L5-L7)', 'Transición (L4)', 'Gerencia (L1-L3)']
        vals_dim = [liderazgo_prom, transicion_prom, gerencia_prom]
        colors_dim = [obtener_etiqueta_color(v)[1] for v in vals_dim]
        labels_dim = [obtener_etiqueta_color(v)[0] for v in vals_dim]
        fig_dim = go.Figure(go.Bar(x=vals_dim, y=dims, orientation='h', marker_color=colors_dim, text=[f"{round(v,1)}% - {l}" for v, l in zip(vals_dim, labels_dim)], textposition='inside'))
        fig_dim.update_layout(xaxis_range=[0, 105], height=400, template="plotly_dark", yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_dim, use_container_width=True)

    # --- 8. INFORME IA (PROMPT SIN REDUNDANCIAS) ---
    st.divider()
    if st.button("✨ GENERAR INFORME EJECUTIVO"):
        prompt_maestro = f"""
        Actúa como un experto consultor senior en desarrollo de liderazgo (Modelo Barrett). Genera un informe estratégico de alto impacto para el líder {lider_sel}.

        DATOS (Usa exclusivamente estos):
        {d.to_json()}
        - Dimensiones: Gerencia L1-L3: {round(gerencia_prom,1)}%, Transición L4: {round(transicion_prom,1)}%, Liderazgo L5-L7: {round(liderazgo_prom,1)}%.

        REGLAS DE ORO:
        - INICIA DIRECTAMENTE CON EL ANÁLISIS. PROHIBIDO: preámbulos, fechas, nombres de consultor o advertencias de confidencialidad.
        - FILOSOFÍA: 100% Apreciativa. Habla de "Oportunidades de Desarrollo" y "Potencial". Prohibido lenguaje negativo o señalar "errores".
        - DATOS: El Ponderado Individual es la competencia real. Auto y Org son solo para comparar alineación. No mezcles el dato de la organización como si fuera la nota del líder.

        ESTRUCTURA DEL INFORME:
        1. DESCRIPCIÓN POR NIVELES Y COMPETENCIA: Realiza un desglose de los 7 niveles (L1-L7). Para cada nivel, integra el análisis de la competencia observada (Ponderado Individual), el potencial y las oportunidades de crecimiento. (NO REPITAS ESTA INFORMACIÓN LUEGO).
        2. ANÁLISIS DE AUTOVALORACIÓN: Evalúa cómo se percibe el líder y destaca áreas de autoconciencia sólida frente al entorno.
        3. MATRIZ DE MADUREZ Y ALINEACIÓN: Cruza el Ponderado Individual con el Organizacional para determinar la alineación con la cultura de Confa.
        4. PERFIL DE LIDERAZGO (EQUILIBRIO): Define el estilo basado en el bloque más fuerte (Gerencia, Transición o Liderazgo). Da 3 recomendaciones estratégicas para armonizar los 7 niveles.

        RÚBRICA: 0-65 Bajo, 66-75 Medio, 76-85 Alto, 85-100 Superior.
        NOMENCLATURA: L1 Líder de Crisis/Viabilidad, L2 Líder de Relaciones, L3 Líder de Desempeño, L4 Líder Facilitador, L5 Líder Auténtico, L6 Líder Mentor/Socio, L7 Líder Visionario.
        """
        try:
            with st.spinner('Analizando datos estratégicos...'):
                response = model.generate_content(prompt_maestro)
                st.markdown(f"## Análisis de Liderazgo Barrett: {lider_sel}")
                st.markdown("---")
                st.write(response.text)
        except Exception as e:
            st.error(f"Error IA: {e}")
