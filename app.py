import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide")

# --- 2. CONEXIÓN IA ---
API_KEY = "AIzaSyB_llfm1vZ7fZkubkkbMBwup5WCXVw36yY"
try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error(f"Error IA: {e}")

# --- 3. CARGA DE DATOS ---
try:
    df = pd.read_csv('Resultados_Gerentes.csv', sep=';', decimal=',')
    df.columns = df.columns.str.strip()
    df['Nombre_Lider'] = df['Nombre_Lider'].str.strip()
    for col in [c for c in df.columns if 'L' in c]:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
except Exception as e:
    st.error(f"Error cargando archivo: {e}")
    st.stop()

# --- 4. SELECCIÓN ---
st.title("🏛️ Dashboard de Liderazgo Barrett - Confa")
lider_sel = st.selectbox("Seleccione el líder:", df['Nombre_Lider'].unique())
d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

# --- 5. VISUALIZACIÓN ESTILO "JENNIFER GARCÍA" ---
st.divider()

# Definimos los datos de las 3 columnas principales
v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]

# Layout de 4 columnas: Icono Teórico | Auto | Individual | Org
col_icono, col1, col2, col3 = st.columns([0.6, 1, 1, 1])

# --- COLUMNA 0: ICONO RELOJ DE ARENA TEÓRICO (LIDERAZGO, TRANSICIÓN, GERENCIA) ---
with col_icono:
    # Creamos un gráfico de barras constante para simular el reloj de la foto
    labels_teoricas = ['L7', 'L6', 'L5', 'L4', 'L3', 'L2', 'L1']
    # Anchos para simular la forma del reloj (ancho arriba y abajo, estrecho al medio)
    anchos = [4, 3, 2, 1.5, 2, 3, 4] 
    colores_teoricos = ['#6F42C1','#6F42C1','#6F42C1','#28A745','#FD7E14','#FD7E14','#FD7E14']
    
    fig_icono = go.Figure()
    # Barras simétricas para crear la forma de copa/reloj
    fig_icono.add_trace(go.Bar(y=labels_teoricas, x=anchos, orientation='h', marker_color=colores_teoricos, hoverinfo='none'))
    fig_icono.add_trace(go.Bar(y=labels_teoricas, x=[-x for x in anchos], orientation='h', marker_color=colores_teoricos, hoverinfo='none'))
    
    # Anotaciones de Texto (Liderazgo, Transición, Gerencia)
    fig_icono.add_annotation(x=0, y='L6', text="LIDERAZGO", showarrow=False, font=dict(color="white", size=10))
    fig_icono.add_annotation(x=0, y='L4', text="TRANSICIÓN", showarrow=False, font=dict(color="white", size=10))
    fig_icono.add_annotation(x=0, y='L2', text="GERENCIA", showarrow=False, font=dict(color="white", size=10))

    fig_icono.update_layout(
        template="plotly_dark", height=450, barmode='relative',
        xaxis=dict(visible=False, range=[-5, 5]),
        yaxis=dict(showgrid=False, autorange="reversed"),
        margin=dict(l=0, r=0, t=10, b=10), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )
    st.plotly_chart(fig_icono, use_container_width=True)

# --- COLUMNAS 1, 2, 3: TUS GRÁFICOS DE BARRAS FUNCIONALES ---
def dibujar_barras_estilo(vals, titulo, color_base):
    labels = ['L7 Vision.', 'L6 Mentor', 'L5 Autént.', 'L4 Facil.', 'L3 Desemp.', 'L2 Relac.', 'L1 Crisis']
    v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
    
    # Colores dinámicos según el nivel (estilo Jennifer)
    colores = ['#6F42C1','#6F42C1','#6F42C1','#28A745','#FD7E14','#FD7E14','#FD7E14']
    
    fig = go.Figure(go.Bar(
        x=v_plot, y=labels, orientation='h', 
        marker_color=colores, # Usamos los colores por categoría
        text=[f"{round(v,1)}%" for v in v_plot], textposition='inside'
    ))
    fig.update_layout(
        title=titulo, xaxis_range=[0, 105], height=450, template="plotly_dark",
        margin=dict(l=0, r=10, t=40, b=20), yaxis=dict(autorange="reversed"),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig

with col1: st.plotly_chart(dibujar_barras_estilo(v_auto, "Auto-Percepción"), use_container_width=True)
with col2: st.plotly_chart(dibujar_barras_estilo(v_ind, "Valores Observados"), use_container_width=True)
with col3: st.plotly_chart(dibujar_barras_estilo(v_org, "Valores Deseados (Org)"), use_container_width=True)

# --- 6. RADAR Y BOTÓN IA ---
st.divider()
col_radar, col_button = st.columns([2, 1])

with col_radar:
    st.subheader("Radar de Alineación Estratégica")
    fig_radar = go.Figure()
    cats = ['L1','L2','L3','L4','L5','L6','L7']
    fig_radar.add_trace(go.Scatterpolar(r=v_auto, theta=cats, fill='toself', name='Auto', line_color='#3498db'))
    fig_radar.add_trace(go.Scatterpolar(r=v_ind, theta=cats, fill='toself', name='Individual', line_color='#2ecc71'))
    fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=450, template="plotly_dark")
    st.plotly_chart(fig_radar, use_container_width=True)

with col_button:
    st.write("") # Espaciador
    if st.button("✨ Generar Informe Ejecutivo con IA"):
        prompt = f"Analiza los resultados de {lider_sel} bajo el modelo Barrett: {d.to_json()}. Tono ejecutivo, español."
        try:
            with st.spinner('Analizando...'):
                response = model.generate_content(prompt)
                st.markdown(response.text)
        except Exception as e:
            st.error(f"Error IA: {e}")
