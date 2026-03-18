import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="LDR Barrett - Consultoría Confa", layout="wide", page_icon="🏛️")

# Estilo CSS para limpieza visual y botones ejecutivos
st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    h1 { color: #1e3a8a; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    h3 { color: #334155; margin-top: 20px; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }
    .stSelectbox label { font-weight: bold; color: #1e3a8a; }
    .stButton>button { background-color: #1e3a8a; color: white; border-radius: 8px; height: 3.5em; font-weight: bold; width: 100%; transition: 0.3s; }
    .stButton>button:hover { background-color: #2563eb; border: none; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN IA (MODELO 1.5-FLASH-8B) ---
# Usamos el alias que te funcionó para evitar errores 404
API_KEY = "AIzaSyB_llfm1vZ7fZkubkkbMBwup5WCXVw36yY"
try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-8b')
except Exception as e:
    st.error(f"Error de conexión con la IA: {e}")

# --- 3. PROCESAMIENTO DE DATOS ---
@st.cache_data
def cargar_datos():
    try:
        df = pd.read_csv('Resultados_Gerentes.csv', sep=';', decimal=',')
        df.columns = df.columns.str.strip()
        df['Nombre_Lider'] = df['Nombre_Lider'].str.strip()
        # Limpieza de nulos y conversión numérica
        niveles_cols = [c for c in df.columns if 'L' in c]
        for col in niveles_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Error al leer Resultados_Gerentes.csv: {e}")
        return None

df = cargar_datos()

if df is not None:
    # --- 4. SELECCIÓN DE LÍDER ---
    st.title("🏛️ Plataforma Senior de Liderazgo Barrett")
    lideres = sorted(df['Nombre_Lider'].unique())
    lider_sel = st.selectbox("👤 Seleccione el Líder para el diagnóstico detallado:", lideres)
    d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

    # --- 5. RADAR DE ALINEACIÓN ---
    st.subheader("🎯 Radar de Alineación Estratégica (Visión 360)")
    cats = ['L1 Crisis','L2 Relac.','L3 Desemp.','L4 Facil.','L5 Autént.','L6 Mentor','L7 Vision.']
    v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
    v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(r=v_auto, theta=cats, fill='toself', name='Autovaloración', line_color='#3b82f6'))
    fig_radar.add_trace(go.Scatterpolar(r=v_ind, theta=cats, fill='toself', name='Ponderado Individual', line_color='#10b981'))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=450, margin=dict(t=20, b=20))
    st.plotly_chart(fig_radar, use_container_width=True)

    # --- 6. RELOJES DE ARENA (ESCALA DE DESARROLLO 1-4) ---
    st.divider()
    st.subheader("⏳ Relojes de Arena: Nivel de Desarrollo (Escala 1 a 4)")
    st.info("Visualización de la madurez del líder por nivel: 1-Bajo, 2-Medio, 3-Alto, 4-Superior")
    
    def a_escala_4(v):
        if v < 65: return 1
        if v < 75: return 2
        if v < 85: return 3
        return 4

    def dibujar_hourglass(vals, titulo, color):
        # Mapeo a escala 1-4
        v_4 = [a_escala_4(x) for x in vals]
        # Niveles invertidos para que L7 esté arriba (Reloj de Arena Barrett)
        labels = ['L7 Visionario', 'L6 Mentor', 'L5 Auténtico', 'L4 Facilitador', 'L3 Desempeño', 'L2 Relaciones', 'L1 Crisis']
        v_plot = [v_4[6], v_4[5], v_4[4], v_4[3], v_4[2], v_4[1], v_4[0]]
        
        # El efecto hourglass se logra con un gráfico de Funnel o barras centradas
        fig = go.Figure(go.Funnel(
            y=labels,
            x=v_plot,
            textinfo="value",
            marker=dict(color=color, line=dict(width=2, color="white")),
            connector=dict(line=dict(color="white", width=1))
        ))
        fig.update_layout(title=dict(text=titulo, x=0.5), height=500, margin=dict(l=150, r=50))
        return fig

    c1, c2, c3 = st.columns(3)
    with c1:
        st.plotly_chart(dibujar_hourglass(v_auto, "Auto-Desarrollo", "#3b82f6"), use_container_width=True)
    with c2:
        st.plotly_chart(dibujar_hourglass(v_ind, "Desarrollo Observado", "#10b981"), use_container_width=True)
    with c3:
        v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]
        st.plotly_chart(dibujar_hourglass(v_org, "Nivel Organizacional", "#64748b"), use_container_width=True)

    # --- 7. DIAGRAMA DE BARRAS DE RESULTADOS ---
    st.divider()
    st.subheader("📊 Resultados Detallados (Porcentaje)")
    
    def dibujar_barras(vals, titulo, color):
        labels = ['L7', 'L6', 'L5', 'L4', 'L3', 'L2', 'L1']
        v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
        fig = go.Figure(go.Bar(x=v_plot, y=labels, orientation='h', marker_color=color, text=[f"{v}%" for v in v_plot], textposition='inside'))
        fig.update_layout(title=titulo, xaxis_range=[0,105], height=350)
        return fig

    b1, b2, b3 = st.columns(3)
    with b1: st.plotly_chart(dibujar_barras(v_auto, "Resultados Auto", "#3b82f6"), use_container_width=True)
    with b2: st.plotly_chart(dibujar_barras(v_ind, "Resultados Individual", "#10b981"), use_container_width=True)
    with b3: st.plotly_chart(dibujar_barras(v_org, "Resultados Org.", "#64748b"), use_container_width=True)

    # --- 8. MOTOR DE INFORME ESTRATÉGICO ---
    st.divider()
    if st.button("🚀 GENERAR INFORME DE ALTO IMPACTO"):
        
        # PROMPT REFORZADO CON MARCO TEÓRICO Y REGLAS ESTRICTAS
        CONTEXTO_BARRETT = """
        Marco Teórico Barrett:
        L1 (Viabilidad): Estabilidad, salud financiera.
        L2 (Relaciones): Armonía, resolución de conflictos.
        L3 (Desempeño): Eficiencia, mejores prácticas.
        L4 (Evolución): Transformación, empoderamiento.
        L5 (Alineación): Confianza, integridad, valores compartidos.
        L6 (Colaboración): Desarrollo de líderes, alianzas.
        L7 (Servicio): Visión global, legado, ética.
        """
        
        PROMPT_ESTRICTO = f"""
        Actúa como un experto consultor senior en el modelo de 7 niveles de conciencia de Richard Barrett. 
        Analiza a {lider_sel} basándote en estos datos reales: {d.to_json()}
        
        {CONTEXTO_BARRETT}

        Rúbrica de evaluación:
        - 0 a 65: Bajo
        - 65 a 75: Medio
        - 75 a 85: Alto
        - 85 a 100: Superior

        ESTRUCTURA DEL INFORME (OBLIGATORIA):
        1. DESCRIPCIÓN POR NIVELES: Desglose analítico de L1 a L7 usando el Ponderado Individual. Define potencial y oportunidades.
        2. ANÁLISIS DE AUTOVALORACIÓN: ¿Cómo se percibe el líder? Evalúa sesgos entre AUTO e INDIVIDUAL.
        3. ANÁLISIS DE PONDERADO INDIVIDUAL: Evaluación de la competencia real observada.
        4. MATRIZ DE MADUREZ: Cruce entre Ponderado Individual y Organizacional. Determina alineación cultural con Confa.
        5. PERFIL DE LIDERAZGO: Define un estilo predominante (basado en el nivel con mayor desarrollo) y da 3 recomendaciones tácticas para el equilibrio de los 7 niveles.

        Tono: Ejecutivo, profesional y accionable. No inventes datos.
        """
        
        try:
            with st.spinner('Procesando análisis de alta dirección...'):
                response = model.generate_content(PROMPT_ESTRICTO)
                st.markdown(f"## Informe Ejecutivo: {lider_sel}")
                st.write(response.text)
        except Exception as e:
            st.error(f"Error al generar el informe: {e}")

else:
    st.warning("Asegúrate de que el archivo 'Resultados_Gerentes.csv' esté en la carpeta raíz de tu GitHub.")
