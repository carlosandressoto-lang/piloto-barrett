import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
from fpdf import FPDF
import io
import tempfile
import os

# --- 1. CONFIGURACIÓN Y ESTILOS (MANTENEMOS TU DASHBOARD) ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide")

if "informe_cache" not in st.session_state:
    st.session_state.informe_cache = {}

st.markdown("""
<style>
    .titulo-seccion { font-weight: bold; margin-bottom: 10px; font-size: 1.1rem; text-align: center; }
    .leyenda-v3 { display: flex; flex-direction: column; justify-content: space-between; height: 340px; margin-top: 35px; padding-right: 10px; border-right: 1px solid rgba(128, 128, 128, 0.3); }
    .item-ley { height: 48px; display: flex; align-items: center; justify-content: flex-end; font-size: 0.85rem; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. CARGA DE DATOS ---
@st.cache_data
def load_data():
    try:
        csv_url = st.secrets["GSHEET_URL"]
        df = pd.read_csv(csv_url, decimal=',')
        df.columns = df.columns.str.strip()
        df['Nombre_Lider'] = df['Nombre_Lider'].astype(str).str.strip()
        df = df[~df['Nombre_Lider'].isin(['0.0', 'nan', ''])]
        cols_to_fix = [c for c in df.columns if ('L' in c) or 'POT' in c or 'DES' == c]
        for col in cols_to_fix:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except: return None

df = load_data()

# --- 3. FUNCIONES DE GRÁFICOS (RELOJ DE ARENA) ---
def obtener_color_desarrollo(v):
    if v < 65: return "#ff4b4b" 
    if v < 75: return "#f1c40f" 
    if v < 85: return "#2ecc71" 
    return "rgb(33, 115, 182)"

def obtener_etiqueta(v):
    if v < 65: return "Bajo"
    if v < 75: return "Medio"
    if v < 85: return "Alto"
    return "Superior"

def generar_fig_reloj(vals, incluir_leyenda=False):
    # Definimos la estructura del reloj (Pirámide invertida y normal)
    anchos_base = [6, 5, 4, 3.2, 4, 5, 6] 
    v_rev = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
    colors_barrett = ["rgb(33,115,182)"]*3 + ["rgb(140,183,42)"] + ["rgb(241,102,35)"]*3
    labels_niveles = ["L7-Visionario", "L6-Mentor", "L5-Auténtico", "L4-Facilitador", "L3-Desempeño", "L2-Relaciones", "L1-Crisis"]
    
    fig = go.Figure()
    fig.add_trace(go.Funnel(
        y=labels_niveles if incluir_leyenda else [1,2,3,4,5,6,7],
        x=anchos_base,
        textinfo="none",
        hoverinfo="none",
        marker={"color": colors_barrett, "line": {"width": 1, "color": "white"}},
        connector={"visible": False}
    ))
    
    for i, (val, ancho) in enumerate(zip(v_rev, anchos_base)):
        fig.add_annotation(
            x=0, y=i if incluir_leyenda else i+1,
            text=obtener_etiqueta(val),
            showarrow=False,
            font=dict(color=obtener_color_desarrollo(val), size=11, family='Arial Black'),
            bgcolor="white", borderpad=4, width=ancho * 22.0
        )
    
    fig.update_layout(
        height=400,
        margin=dict(l=80 if incluir_leyenda else 10, r=10, t=10, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(visible=incluir_leyenda),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        template="plotly_dark"
    )
    return fig

# --- 4. RENDERIZADO STREAMLIT ---
if df is not None:
    lider_sel = st.selectbox("Seleccione el líder:", sorted(df['Nombre_Lider'].unique()))
    d = df[df['Nombre_Lider'] == lider_sel].iloc[0]
    
    v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
    v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
    v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]

    st.subheader("⏳ Niveles de Madurez Barrett (Relojes)")
    cl, cr1, cr2, cr3 = st.columns([1.2, 1, 1, 1])
    with cl:
        st.markdown("<div class='titulo-seccion'>Nivel Barrett</div>", unsafe_allow_html=True)
        niv_labels = ["L7-Visionario", "L6-Mentor", "L5-Auténtico", "L4-Facilitador", "L3-Desempeño", "L2-Relaciones", "L1-Crisis"]
        st.markdown('<div class="leyenda-v3">' + ''.join([f'<div class="item-ley">{n}</div>' for n in niv_labels]) + '</div>', unsafe_allow_html=True)
    with cr1: st.plotly_chart(generar_fig_reloj(v_auto), key="r1", use_container_width=True)
    with cr2: st.plotly_chart(generar_fig_reloj(v_ind), key="r2", use_container_width=True)
    with cr3: st.plotly_chart(generar_fig_reloj(v_org), key="r3", use_container_width=True)

    # --- BOTÓN DE PDF (LA SOLUCIÓN SOLICITADA) ---
    if st.button("📄 GENERAR PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 16)
        pdf.cell(0, 10, f'REPORTE: {lider_sel}', ln=True, align='C')
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Función para guardar imágenes con fondo blanco para el PDF
            def save_img(fig, name, title):
                fig.update_layout(template="plotly", paper_bgcolor='white', plot_bgcolor='white', font=dict(color='black'), title=dict(text=title, x=0.5))
                path = os.path.join(tmp_dir, name)
                fig.write_image(path, engine="kaleido", scale=2)
                return path

            img_r1 = save_img(generar_fig_reloj(v_auto), "r1.png", "Auto")
            img_r2 = save_img(generar_fig_reloj(v_ind), "r2.png", "Individual")
            img_r3 = save_img(generar_fig_reloj(v_org), "r3.png", "Organizacional")

            # POSICIONAMIENTO MILIMÉTRICO EN EL PDF
            pdf.ln(10)
            pdf.set_font('Helvetica', 'B', 12)
            pdf.cell(0, 10, '3. Niveles de Madurez Barrett (Relojes)', ln=True)
            
            y_inicio_relojes = pdf.get_y()
            
            # 1. Insertamos la leyenda a la izquierda
            pdf.set_font('Helvetica', '', 8)
            pdf.set_text_color(100, 100, 100)
            niveles_txt = ["L7-Visionario", "L6-Mentor", "L5-Autentico", "L4-Facilitador", "L3-Desempeno", "L2-Relaciones", "L1-Crisis"]
            for i, txt in enumerate(niveles_txt):
                # El ajuste de 16 y 5.2 es para que el texto quede frente a cada barra del reloj
                pdf.text(10, y_inicio_relojes + 16 + (i * 5.2), txt)
            
            # 2. Insertamos los 3 relojes EXACTAMENTE IGUALES
            # x define la posición horizontal, y la vertical, w el ancho.
            pdf.image(img_r1, x=35, y=y_inicio_relojes, w=53)
            pdf.image(img_r2, x=88, y=y_inicio_relojes, w=53)
            pdf.image(img_r3, x=141, y=y_inicio_relojes, w=53)

        st.download_button("📥 Descargar PDF", data=bytes(pdf.output()), file_name=f"Reporte_{lider_sel}.pdf", mime="application/pdf")
