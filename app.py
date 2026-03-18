import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide")

# --- 2. CONEXIÓN IA (2.5-FLASH-8B) ---
API_KEY = "AIzaSyB_llfm1vZ7fZkubkkbMBwup5WCXVw36yY"
try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash') # Tu modelo de éxito
except Exception as e:
    st.error(f"Error IA: {e}")

# --- 3. CARGA DE DATOS (MÉTODO SEGURO) ---
@st.cache_data
def load_data():
    # Cargamos el archivo asegurando los separadores correctos
    df = pd.read_csv('Resultados_Gerentes.csv', sep=';', decimal=',')
    # Limpiamos nombres de columnas y datos de texto
    df.columns = df.columns.str.strip()
    df['Nombre_Lider'] = df['Nombre_Lider'].astype(str).str.strip()
    # Convertimos los niveles a números
    for col in [c for c in df.columns if 'L' in c]:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

df = load_data()

# --- 4. SELECTOR DE LÍDER (CONTROL DE ERRORES) ---
st.title("🏛️ Consultoría de Liderazgo Barrett - Confa")

# Obtenemos la lista de nombres. Si sale 0.0 es porque el CSV no leyó bien los strings.
nombres_lideres = df['Nombre_Lider'].unique().tolist()

if not nombres_lideres:
    st.error("No se encontraron nombres en la columna 'Nombre_Lider'. Revisa el CSV.")
else:
    lider_sel = st.selectbox("👤 Seleccione el Líder:", nombres_lideres)
    d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

    # --- 5. LÓGICA ESCALA 1-4 ---
    def scale_1_4(v):
        if v < 65: return 1
        if v < 75: return 2
        if v < 85: return 3
        return 4

    # --- 6. GRÁFICOS RELOJ DE ARENA (SIMÉTRICOS) ---
    st.subheader("⏳ Relojes de Arena (Nivel de Desarrollo 1 a 4)")
    
    def render_hourglass(vals, titulo, color):
        v4 = [scale_1_4(x) for x in vals]
        levels = ['L1 Crisis', 'L2 Relac.', 'L3 Desemp.', 'L4 Facil.', 'L5 Autént.', 'L6 Mentor', 'L7 Vision.']
        
        fig = go.Figure()
        # Forma simétrica (diamante)
        fig.add_trace(go.Scatter(
            x=v4 + [-x for x in v4[::-1]], 
            y=levels + levels[::-1],
            fill='toself',
            fillcolor=color,
            line=dict(color='white', width=1),
            hoverinfo='none'
        ))
        
        for i, val in enumerate(v4):
            fig.add_annotation(x=0, y=levels[i], text=str(val), showarrow=False, font=dict(color="white"))

        fig.update_layout(
            title=dict(text=titulo, x=0.5),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-5, 5]),
            height=450, margin=dict(l=20, r=20, t=40, b=20), template="plotly_dark"
        )
        return fig

    v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
    v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
    v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]

    c1, c2, c3 = st.columns(3)
    with c1: st.plotly_chart(render_hourglass(v_auto, "Auto-Desarrollo", "rgba(59, 130, 246, 0.7)"), use_container_width=True)
    with c2: st.plotly_chart(render_hourglass(v_ind, "Desarrollo Individual", "rgba(16, 185, 129, 0.7)"), use_container_width=True)
    with c3: st.plotly_chart(render_hourglass(v_org, "Cultura Organizacional", "rgba(148, 163, 184, 0.7)"), use_container_width=True)

    # --- 7. RADAR DE ALINEACIÓN ---
    st.divider()
    st.subheader("🎯 Radar de Alineación Estratégica (%)")
    fig_radar = go.Figure()
    cats = ['L1','L2','L3','L4','L5','L6','L7']
    fig_radar.add_trace(go.Scatterpolar(r=v_auto, theta=cats, fill='toself', name='Auto'))
    fig_radar.add_trace(go.Scatterpolar(r=v_ind, theta=cats, fill='toself', name='Indiv'))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=400, template="plotly_dark")
    st.plotly_chart(fig_radar, use_container_width=True)

    # --- 8. INFORME IA CONSULTOR SENIOR ---
    st.divider()
    if st.button("🚀 GENERAR INFORME ESTRATÉGICO"):
        PROMPT = f"""
        Actúa como un Consultor Master Barrett. Analiza los resultados de liderazgo de {lider_sel}.
        Datos JSON: {d.to_json()}
        
        INSTRUCCIONES:
        1. Contextualiza cada nivel según Richard Barrett (L1 a L7).
        2. Aplica rúbrica: 0-65 Bajo, 66-75 Medio, 76-85 Alto, 86-100 Superior.
        3. Analiza la forma del Reloj de Arena (si el desarrollo está en la base o en la cima).
        4. Define estilo predominante y 3 metas de evolución.
        """
        try:
            with st.spinner('Procesando datos...'):
                response = model.generate_content(PROMPT)
                st.markdown(response.text)
        except Exception as e:
            st.error(f"Error IA: {e}")
