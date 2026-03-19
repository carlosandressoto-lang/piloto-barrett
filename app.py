import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide")

# Estilo para fondo oscuro con texto legible
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

    # --- 5. BARRAS ORIGINALES (%) ---
    st.divider()
    st.subheader("Distribución de Energía por Niveles de Conciencia (%)")
    c1, c2, c3 = st.columns(3)

    def dibujar_barras(vals, titulo, color):
        labels = ['L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 'L4 - Facilitador', 'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis']
        v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
        fig = go.Figure(go.Bar(x=v_plot, y=labels, orientation='h', marker_color=color, text=[f"{round(v,1)}%" for v in v_plot], textposition='inside'))
        fig.update_layout(title=dict(text=titulo, font=dict(color='white')), xaxis_range=[0, 105], height=350, template="plotly_dark", margin=dict(l=0, r=10, t=40, b=20), yaxis=dict(autorange="reversed", tickfont=dict(color='white')), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        return fig

    v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
    v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
    v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]

    with c1: st.plotly_chart(dibujar_barras(v_auto, "Autovaloración", "#3498db"), use_container_width=True)
    with c2: st.plotly_chart(dibujar_barras(v_ind, "Individual (360)", "#2ecc71"), use_container_width=True)
    with c3: st.plotly_chart(dibujar_barras(v_org, "Promedio Organizacional", "#e74c3c"), use_container_width=True)

    # --- 6. RELOJES DE ARENA (CON SEMÁFORO DE TEXTO) ---
    st.divider()
    st.subheader("⏳ Nivel de Desarrollo Barrett (Semáforo de Desempeño)")

    def obtener_etiqueta_color(v):
        if v < 65: return "Bajo", "#ff4b4b"      # Rojo
        if v < 75: return "Medio", "#f1c40f"    # Amarillo
        if v < 85: return "Alto", "#2ecc71"     # Verde
        return "Superior", "#3498db"            # Azul

    def dibujar_reloj_semáforo(vals, titulo):
        levels = ['L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 'L4 - Facilitador', 'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis']
        anchos_hourglass = [5, 4, 3, 2.2, 3, 4, 5] 
        colors_barrett_faded = [
            "rgba(111, 66, 193, 0.4)", "rgba(111, 66, 193, 0.4)", "rgba(111, 66, 193, 0.4)", 
            "rgba(40, 167, 69, 0.4)", 
            "rgba(253, 126, 20, 0.4)", "rgba(253, 126, 20, 0.4)", "rgba(253, 126, 20, 0.4)"
        ]
        
        etiquetas = []
        colores_texto = []
        for i in [6, 5, 4, 3, 2, 1, 0]:
            texto, color = obtener_etiqueta_color(vals[i])
            etiquetas.append(texto)
            colores_texto.append(color)

        fig = go.Figure(go.Funnel(
            y=levels, x=anchos_hourglass, text=etiquetas, textinfo="text",
            textfont=dict(color=colores_texto, size=15, family='Arial Black'),
            marker={"color": colors_barrett_faded, "line": {"width": 2, "color": "white"}},
            connector={"line": {"color": "white", "width": 1}, "fillcolor": "rgba(200, 200, 200, 0.1)"}
        ))
        
        fig.update_layout(title=dict(text=titulo, x=0.5, font=dict(color='white')), height=500, margin=dict(l=150, r=20, t=50, b=50), yaxis=dict(autorange="reversed", tickfont=dict(color='white')), xaxis=dict(visible=False), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        return fig

    r1, r2, r3 = st.columns(3)
    with r1: st.plotly_chart(dibujar_reloj_semáforo(v_auto, "Autopercepción Barrett"), use_container_width=True)
    with r2: st.plotly_chart(dibujar_reloj_semáforo(v_ind, "Competencia Individual"), use_container_width=True)
    with r3: st.plotly_chart(dibujar_reloj_semáforo(v_org, "Cultura Organizacional"), use_container_width=True)

    # --- 7. RADAR CENTRADO ---
    st.divider()
    st.subheader("Radar de Alineación Estratégica Triple (%)")
    col_vacia1, col_center_radar, col_vacia2 = st.columns([1, 4, 1])
    with col_center_radar:
        fig_radar = go.Figure()
        cats = ['L1','L2','L3','L4','L5','L6','L7']
        fig_radar.add_trace(go.Scatterpolar(r=v_auto, theta=cats, fill='toself', name='Auto', line_color='#3498db'))
        fig_radar.add_trace(go.Scatterpolar(r=v_ind, theta=cats, fill='toself', name='Individual', line_color='#2ecc71'))
        fig_radar.add_trace(go.Scatterpolar(r=v_org, theta=cats, fill='toself', name='Organizacional', line_color='#e74c3c'))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(color='white')), angularaxis=dict(tickfont=dict(color='white'))), height=600, template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5))
        st.plotly_chart(fig_radar, use_container_width=True)

    # --- 8. INFORME IA A ANCHO COMPLETO CON PROMPT MAESTRO ---
    st.divider()
    if st.button("✨ GENERAR INFORME EJECUTIVO"):
        prompt_maestro = f"""
        CONTEXTO Y ROL:
        Actúa como un experto consultor senior en desarrollo de liderazgo, especializado exclusivamente en el Modelo de los 7 Niveles de Conciencia de Richard Barrett. 
        Tu objetivo es generar un informe de alto impacto para el Comité Ejecutivo y la Gerencia de Gestión Humana sobre el líder {lider_sel}.

        DATOS PARA EL ANÁLISIS:
        {d.to_json()}

        FILOSOFÍA DE FEEDBACK (OBLIGATORIO):
        - Utiliza un enfoque basado en OPORTUNIDADES DE DESARROLLO y POTENCIAL.
        - Está estrictamente prohibido utilizar lenguaje negativo, señalar "errores" o "fallos".
        - Todo hallazgo debe ser enmarcado como una posibilidad de crecimiento o un área para fortalecer el equilibrio.
        - NO incluyas introducciones corteses como "Aquí tienes el análisis...". Inicia directamente con el contenido profesional.

        ESTRUCTURA DEL INFORME:
        1. DESCRIPCIÓN POR NIVELES: Desglose analítico de los 7 niveles (L1 a L7). Identifica el potencial actual en cada nivel y las oportunidades específicas de evolución según los datos de 'Ponderado Individual'.
        2. ANÁLISIS DE AUTOVALORACIÓN: Evalúa la percepción del líder sobre sí mismo. Destaca las áreas donde el líder muestra una autoconciencia sólida y aquellas donde el entorno observa un potencial que el líder aún puede reconocer más profundamente.
        3. ANÁLISIS DE PONDERADO INDIVIDUAL: Evalúa las competencias reales observadas por el entorno. Utiliza la rúbrica para destacar los niveles donde la maestría es evidente y aquellos donde existe un camino claro para elevar el impacto.
        4. MATRIZ DE MADUREZ: Cruza el Ponderado Individual con el Ponderado Organizacional. Determina la alineación estratégica del líder con la cultura actual y su rol como motor de crecimiento organizacional.
        5. PERFIL DE LIDERAZGO: Define un (1) estilo predominante basado en el nivel más desarrollado. Propón tres recomendaciones accionables y de gran valor estratégico para armonizar los 7 niveles de conciencia.

        RÚBRICA TÉCNICA:
        - 0 a 65: Bajo | 65 a 75: Medio | 75 a 85: Alto | 85 a 100: Superior

        TONO Y TERMINOLOGÍA:
        - Profesional, ejecutivo, analítico y transformacional.
        - Emplea terminología técnica de Barrett (ej. Viabilidad, Relaciones, Desempeño, Evolución, Alineación, Colaboración, Servicio).
        """
        
        try:
            with st.spinner('Analizando datos bajo el modelo Barrett...'):
                response = model.generate_content(prompt_maestro)
                st.markdown(f"### 📋 Informe Ejecutivo: {lider_sel}")
                st.markdown("---")
                st.write(response.text)
        except Exception as e:
            st.error(f"Error IA: {e}")
