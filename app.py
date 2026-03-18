import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide")

# --- 2. CONEXIÓN CORREGIDA (SOLUCIÓN AL 404) ---
# Usa tu clave aquí. Si la tienes en Secrets, usa st.secrets["GOOGLE_API_KEY"]
API_KEY = "AIzaSyB_llfm1vZ7fZkubkkbMBwup5WCXVw36yY" 

try:
    genai.configure(api_key=API_KEY)
    # EL CAMBIO CLAVE: Quitamos 'models/' y usamos el nombre base
    # La librería se encarga de buscar la versión v1 o v1beta automáticamente
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Error de configuración inicial: {e}")

# --- 3. DATOS ---
try:
    df = pd.read_csv('Resultados_Gerentes.csv', sep=';', decimal=',')
    df.columns = df.columns.str.strip()
    df['Nombre_Lider'] = df['Nombre_Lider'].str.strip()
except Exception as e:
    st.error("No se pudo cargar el archivo CSV.")
    st.stop()

# --- 4. INTERFAZ ---
st.title("🏛️ Dashboard de Liderazgo")
lider_sel = st.selectbox("Seleccione el líder:", df['Nombre_Lider'].unique())
d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

# --- 5. GRÁFICO RADAR ---
fig_radar = go.Figure()
cats = ['L1','L2','L3','L4','L5','L6','L7']
v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]

fig_radar.add_trace(go.Scatterpolar(r=v_auto, theta=cats, fill='toself', name='Autovaloración'))
fig_radar.add_trace(go.Scatterpolar(r=v_ind, theta=cats, fill='toself', name='Ponderado Individual'))
fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=True)
st.plotly_chart(fig_radar)

# --- 6. EL BOTÓN QUE DABA ERROR (CORREGIDO) ---
if st.button("✨ Generar Informe Ejecutivo con IA"):
    prompt = f"Analiza los resultados de liderazgo de {lider_sel} bajo el modelo Barrett: {d.to_json()}"
    
    try:
        with st.spinner('Procesando con Gemini...'):
            # Cambiamos la llamada para asegurar compatibilidad
            response = model.generate_content(prompt)
            st.success("Análisis completado")
            st.markdown(response.text)
    except Exception as e:
        # Si el 404 persiste, intentamos con el nombre alternativo de emergencia
        try:
            model_alt = genai.GenerativeModel('gemini-pro')
            response = model_alt.generate_content(prompt)
            st.markdown(response.text)
        except:
            st.error(f"Error de conexión persistente: {e}")
            st.info("Sugerencia: Entra a Google AI Studio y verifica que no tengas un mensaje de 'Quota exceeded'.")
