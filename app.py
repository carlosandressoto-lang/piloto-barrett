import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. CONFIGURACIÓN BÁSICA ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide")

# --- 2. CONEXIÓN IA (MODELO 2.5) ---
# Cambia por tu API KEY
API_KEY = "AIzaSyB_llfm1vZ7fZkubkkbMBwup5WCXVw36yY"
try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-8b') # Tu versión confirmada
except Exception as e:
    st.error(f"Error IA: {e}")

# --- 3. CARGA DE DATOS ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('Resultados_Gerentes.csv', sep=';', decimal=',')
        df.columns = df.columns.str.strip()
        df['Nombre_Lider'] = df['Nombre_Lider'].str.strip()
        # Asegurar numéricos
        for col in [c for c in df.columns if 'L' in c]:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Error cargando CSV: {e}")
        return None

df = load_data()

if df is not None:
    # --- 4. INTERFAZ: SELECTOR DE LIDER (RAÍZ) ---
    st.title("🏛️ Consultoría de Liderazgo Barrett - Confa")
    
    # Selector simple para evitar el error 0.0
    lideres_lista = sorted(df['Nombre_Lider'].unique())
    lider_sel = st.selectbox("👤 Seleccione el Líder:", lideres_lista)
    
    # Filtrado de datos del líder seleccionado
    d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

    # --- 5. LÓGICA DE ESCALA 1-4 PARA RELOJ DE ARENA ---
    def a_escala_4(v):
        if v < 65: return 1
        if v < 75: return 2
        if v < 85: return 3
        return 4

    # --- 6. VISUALIZACIÓN: RELOJES DE ARENA (DIAMANTE) ---
    st.subheader("⏳ Relojes de Arena: Nivel de Desarrollo (Escala 1 a 4)")
    
    def crear_diamante_barrett(vals, titulo, color):
        v4 = [a_escala_4(x) for x in vals]
        niveles = ['L1 Crisis', 'L2 Relac.', 'L3 Desemp.', 'L4 Facil.', 'L5 Autént.', 'L6 Mentor', 'L7 Vision.']
        
        # Simetría para formar el diamante
        x_pos = v4
        x_neg = [-x for x in v4]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_pos + x_neg[::-1], 
            y=niveles + niveles[::-1],
            fill='toself',
            fillcolor=color,
            line=dict(color='white', width=1),
            name=titulo
        ))
        
        # Etiquetas de nivel en el centro
        for i, val in enumerate(v4):
            fig.add_annotation(x=0, y=niveles[i], text=str(val), showarrow=False, font=dict(color="white"))

        fig.update_layout(
            title=dict(text=titulo, x=0.5),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-4.5, 4.5]),
            yaxis=dict(showgrid=True),
            height=450,
            margin=dict(l=20, r=20, t=40, b=20),
            showlegend=False,
            template="plotly_dark"
        )
        return fig

    v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
    v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
    v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]

    col1, col2, col3 = st.columns(3)
    with col1: st.plotly_chart(crear_diamante_barrett(v_auto, "Auto-Percepción", "rgba(59, 130, 246, 0.7)"), use_container_width=True)
    with col2: st.plotly_chart(crear_diamante_barrett(v_ind, "Competencia Real", "rgba(16, 185, 129, 0.7)"), use_container_width=True)
    with col3: st.plotly_chart(crear_diamante_barrett(v_org, "Cultura Org.", "rgba(148, 163, 184, 0.7)"), use_container_width=True)

    # --- 7. RADAR DE ALINEACIÓN ---
    st.divider()
    st.subheader("🎯 Radar de Alineación Estratégica (%)")
    fig_radar = go.Figure()
    cats = ['L1','L2','L3','L4','L5','L6','L7']
    fig_radar.add_trace(go.Scatterpolar(r=v_auto, theta=cats, fill='toself', name='Auto'))
    fig_radar.add_trace(go.Scatterpolar(r=v_ind, theta=cats, fill='toself', name='Indiv'))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=400, template="plotly_dark")
    st.plotly_chart(fig_radar, use_container_width=True)

    # --- 8. INFORME CONSULTIVO IA ---
    st.divider()
    if st.button("🚀 GENERAR INFORME ESTRATÉGICO"):
        PROMPT = f"""
        Actúa como un Consultor Master Barrett. Analiza los resultados de {lider_sel}.
        Datos del Líder: {d.to_json()}
        
        Sigue estrictamente la teoría de los 7 niveles de Richard Barrett:
        L1 Supervivencia, L2 Relaciones, L3 Autoestima, L4 Transformación, L5 Cohesión, L6 Alianzas, L7 Servicio.
        
        Rúbrica: 0-65 Bajo, 66-75 Medio, 76-85 Alto, 86-100 Superior.
        
        Estructura del Informe:
        1. Perfil de Liderazgo (Resumen Ejecutivo).
        2. Análisis por Niveles (Basado en Ponderado Individual).
        3. Evaluación de Brechas (Auto vs Individual).
        4. Matriz de Madurez (Alineación con Cultura Organizacional).
        5. Plan de Acción (1 estilo predominante y 3 metas de evolución).
        
        Tono profesional y analítico para alta gerencia.
        """
        try:
            with st.spinner('Analizando datos bajo el modelo Barrett...'):
                response = model.generate_content(PROMPT)
                st.markdown(response.text)
        except Exception as e:
            st.error(f"Error IA: {e}")

else:
    st.error("No se pudo cargar la base de datos.")
