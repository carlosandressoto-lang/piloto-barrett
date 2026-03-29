import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
from fpdf import FPDF
import io
import tempfile
import os
import re

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="LDR Barrett - Confa", layout="wide")

if "informe_cache" not in st.session_state:
    st.session_state.informe_cache = {}

st.markdown("""
<style>
    .main { font-family: 'Helvetica Neue', sans-serif; }
    .titulo-seccion { font-weight: bold; margin-bottom: 10px; font-size: 1.1rem; text-align: center; }
    .metric-box { 
        background-color: rgba(30, 41, 59, 0.05); 
        padding: 15px; 
        border-radius: 10px; 
        text-align: left; 
        border: 1px solid rgba(128, 128, 128, 0.3); 
    }
    .ninebox-container { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 20px; }
    .quadrant-box { border-radius: 8px; padding: 15px; min-height: 150px; color: white; font-size: 0.85rem; border: 1px solid rgba(255,255,255,0.2); }
    .quad-title { font-weight: bold; border-bottom: 1px solid rgba(255,255,255,0.4); margin-bottom: 8px; padding-bottom: 4px; text-transform: uppercase; font-size: 0.75rem; }
    .name-list { line-height: 1.4; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN IA SEGURA ---
try:
    api_key_segura = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key_segura)
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error("Error: Configure su API KEY en los Secrets.")

# --- 3. CARGA DE DATOS ---
@st.cache_data
def load_data():
    try:
        csv_url = st.secrets["GSHEET_URL"]
        df = pd.read_csv(csv_url, decimal=',')
        df.columns = df.columns.str.strip()
        df['Nombre_Lider'] = df['Nombre_Lider'].astype(str).str.strip()
        df = df[~df['Nombre_Lider'].isin(['0.0', 'nan', ''])]
        df = df.dropna(subset=['Nombre_Lider'])
        if 'GER_LID' in df.columns:
            df['GER_LID'] = df['GER_LID'].fillna("N/A").astype(str).str.strip()
        
        cols_to_fix = [c for c in df.columns if ('L' in c and any(x in c for x in ['AUTO', 'INDIV', 'ORG'])) or 'CANT_' in c or 'POT' in c or 'DES' == c]
        for col in cols_to_fix:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Error crítico: {e}")
        return None

df = load_data()

# --- 4. LÓGICAS VISUALES ---
def obtener_cuadrante_confa(pot, des):
    if pot < 60: p_label = "BAJO"
    elif pot < 80: p_label = "ALTO"
    else: p_label = "SUPERIOR"
    if des <= 1: d_label = "BAJO"
    elif des <= 2: d_label = "ALTO"
    else: d_label = "SUPERIOR"
    mapping = {
        ("SUPERIOR", "BAJO"): "ENIGMA: DIAMANTE EN BRUTO", ("SUPERIOR", "ALTO"): "FUTURA ESTRELLA EN CRECIMIENTO", ("SUPERIOR", "SUPERIOR"): "FUTUROS LIDERES: SUPERESTRELLAS",
        ("ALTO", "BAJO"): "DILEMA", ("ALTO", "ALTO"): "EMPLEADOS CLAVE", ("ALTO", "SUPERIOR"): "FUTURAS ESTRELLAS",
        ("BAJO", "BAJO"): "ICEBERG", ("BAJO", "ALTO"): "EFECTIVOS", ("BAJO", "SUPERIOR"): "PROFESIONALES CONFIABLES"
    }
    return mapping.get((p_label, d_label), "No clasificado")

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

def generar_fig_barras(vals, titulo, color):
    labels = ['L7-Visionario', 'L6-Mentor Socio', 'L5-Auténtico', 'L4-Facilitador Innovador', 'L3-Gestor de Desempeño', 'L2-Gestor de Relaciones', 'L1-Gestor de Crisis']
    v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
    fig = go.Figure(go.Bar(x=v_plot, y=labels, orientation='h', marker_color=color, text=[f"{round(v,1)}%" for v in v_plot], textposition='inside', insidetextfont=dict(color='white')))
    fig.update_layout(title=dict(text=titulo, x=0.5), xaxis_range=[0, 105], template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=10, t=40, b=20), height=350, yaxis=dict(autorange="reversed"))
    return fig

def generar_fig_reloj(vals, incluir_leyenda=False):
    anchos_base = [6, 5, 4, 3.2, 4, 5, 6] 
    v_rev = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
    colors_barrett = ["rgb(33,115,182)"]*3 + ["rgb(140,183,42)"] + ["rgb(241,102,35)"]*3
    labels_niveles = ['L7-Visionario', 'L6-Mentor Socio', 'L5-Auténtico', 'L4-Facilitador Innovador', 'L3-Gestor de Desempeño', 'L2-Gestor de Relaciones', 'L1-Gestor de Crisis']
    fig = go.Figure()
    fig.add_trace(go.Funnel(y=labels_niveles if incluir_leyenda else [1,2,3,4,5,6,7], x=anchos_base, textinfo="none", hoverinfo="none", marker={"color": colors_barrett, "line": {"width": 1, "color": "white"}}, connector={"visible": False}))
    for i, (val, ancho) in enumerate(zip(v_rev, anchos_base)):
        fig.add_annotation(x=0, y=i if incluir_leyenda else i+1, text=obtener_etiqueta(val), showarrow=False, font=dict(color=obtener_color_desarrollo(val), size=11, family='Arial Black'), bgcolor="white", borderpad=4, width=ancho * 22.0)
    fig.update_layout(height=400, margin=dict(l=100 if incluir_leyenda else 10, r=10, t=10, b=10), xaxis=dict(visible=False), yaxis=dict(visible=incluir_leyenda), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', template="plotly_dark")
    return fig

# --- 5. RENDERIZADO PRINCIPAL ---
if df is not None:
    lideres = sorted(df['Nombre_Lider'].unique())
    lider_sel = st.selectbox("Seleccione el líder:", lideres)
    
    es_gerencia = lider_sel.startswith("GER_")
    es_confa = lider_sel == "CONFA"

    d = df[df['Nombre_Lider'] == lider_sel].iloc[0]

    if es_confa:
        df_grupo = df[~df['Nombre_Lider'].isin(["CONFA"]) & ~df['Nombre_Lider'].str.startswith("GER_")]
    elif es_gerencia:
        df_grupo = df[df['GER_LID'] == lider_sel]
    else:
        df_grupo = df[df['Nombre_Lider'] == lider_sel]

    st.subheader("👥 Información de la Evaluación")
    c_ev1, c_ev2 = st.columns([1, 2])
    with c_ev1: st.metric("Total Evaluadores", int(d.CANT_EVAL))
    with c_ev2: 
        ger_lid_val = d.get('GER_LID', 'N/A')
        st.write(f"**Gerencia:** {ger_lid_val} | **Auto:** {int(d.CANT_AUTO)} | **Jefe:** {int(d.CANT_JEFE)} | **Pares:** {int(d.CANT_PAR)} | **Colab:** {int(d.CANT_COL)}")

    v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
    v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
    v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]
    liderazgo_prom = (d.INDIV_L5 + d.INDIV_L6 + d.INDIV_L7) / 3
    transicion_prom = d.INDIV_L4
    gerencia_prom = (d.INDIV_L1 + d.INDIV_L2 + d.INDIV_L3) / 3

    st.subheader("📊 Frecuencia de comportamientos por niveles (%)")
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown("<div class='titulo-seccion'>Autovaloración</div>", unsafe_allow_html=True); st.plotly_chart(generar_fig_barras(v_auto, "", "#3498db"), use_container_width=True)
    with c2: st.markdown("<div class='titulo-seccion'>Ponderado Individual</div>", unsafe_allow_html=True); st.plotly_chart(generar_fig_barras(v_ind, "", "#2ecc71"), use_container_width=True)
    with c3: st.markdown("<div class='titulo-seccion'>Ponderado Organizacional</div>", unsafe_allow_html=True); st.plotly_chart(generar_fig_barras(v_org, "", "#e74c3c"), use_container_width=True)

    st.divider()
    st.subheader("⏳ Resultados Evaluación 360° (Niveles Barrett)")
    cl, cr1, cr2, cr3 = st.columns([0.7, 1, 1, 1])
    with cl:
        st.markdown("<div class='titulo-seccion'>Nivel Barrett</div>", unsafe_allow_html=True)
        niv_labels = ['L7-Visionario', 'L6-Mentor Socio', 'L5-Auténtico', 'L4-Facilitador Innovador', 'L3-Gestor de Desempeño', 'L2-Gestor de Relaciones', 'L1-Gestor de Crisis']
        st.markdown(f"""
            <div style="display: flex; flex-direction: column; justify-content: space-between; height: 350px; margin-top: 40px; padding-bottom: 15px; border-right: 1px solid rgba(128,128,128,0.3);">
                {''.join([f'<div style="height: 45px; display: flex; align-items: center; justify-content: flex-end; font-size: 0.85rem; font-weight: bold; padding-right: 10px;">{n}</div>' for n in niv_labels])}
            </div>
        """, unsafe_allow_html=True)

    fig_config_fix = {"margin": dict(l=0, r=0, t=10, b=10), "height": 400, "showlegend": False}
    with cr1: 
        st.markdown("<div class='titulo-seccion'>Autovaloración</div>", unsafe_allow_html=True)
        f1 = generar_fig_reloj(v_auto); f1.update_layout(**fig_config_fix); st.plotly_chart(f1, key="r1_dash", use_container_width=True, config={'displayModeBar': False})
    with cr2: 
        st.markdown("<div class='titulo-seccion'>Individual</div>", unsafe_allow_html=True)
        f2 = generar_fig_reloj(v_ind); f2.update_layout(**fig_config_fix); st.plotly_chart(f2, key="r2_dash", use_container_width=True, config={'displayModeBar': False})
    with cr3: 
        st.markdown("<div class='titulo-seccion'>Organizacional</div>", unsafe_allow_html=True)
        f3 = generar_fig_reloj(v_org); f3.update_layout(**fig_config_fix); st.plotly_chart(f3, key="r3_dash", use_container_width=True, config={'displayModeBar': False})

    st.divider()
    col_radar, col_dim = st.columns([1, 1])
    with col_radar:
        st.subheader("🎯 Alineación de Consciencia")
        fig_radar = go.Figure()
        cats = ['L1','L2','L3','L4','L5','L6','L7']
        for val, name, color in zip([v_auto, v_ind, v_org], ['Auto', 'Individual', 'Org'], ['#3498db', '#2ecc71', '#e74c3c']):
            fig_radar.add_trace(go.Scatterpolar(r=val, theta=cats, fill='toself', name=name, line_color=color))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), template="plotly_dark", height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_radar, use_container_width=True)
    with col_dim:
        st.subheader("⚖️ Índice de Equilibrio")
        v_dim = [liderazgo_prom, transicion_prom, gerencia_prom]
        fig_dim = go.Figure(go.Bar(x=v_dim, y=['Liderazgo', 'Transición', 'Gerencia'], orientation='h', marker_color='#3498db', text=[f"{round(v,1)}%" for v in v_dim], textposition='inside'))
        fig_dim.update_layout(xaxis_range=[0, 105], height=400, template="plotly_dark", yaxis=dict(autorange="reversed"), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_dim, use_container_width=True)

    st.divider()
    st.subheader("🟦 Mapa de Talento NineBox Confa")
    cnb1, cnb2 = st.columns([1.5, 1])
    cuadrante = obtener_cuadrante_confa(d.IND_POT, d.DES)
    
    with cnb1:
        fig_nb = go.Figure()
        quads = [
            (0.5, 1.5, 0, 33.33, "#440154", "ICEBERG"), 
            (1.5, 2.5, 0, 33.33, "#482878", "EFECTIVOS"), 
            (2.5, 3.5, 0, 33.33, "#3b528b", "PROF. CONFIABLES"), 
            (0.5, 1.5, 33.33, 66.66, "#31688e", "DILEMA"), 
            (1.5, 2.5, 33.33, 66.66, "#21918c", "EMPLEADOS CLAVE"), 
            (2.5, 3.5, 33.33, 66.66, "#5ec962", "FUTURAS ESTRELLAS"), 
            (0.5, 1.5, 66.66, 100, "#b5de2b", "ENIGMA"), 
            (1.5, 2.5, 66.66, 100, "#fde725", "ESTRELLA CREC."), 
            (2.5, 3.5, 66.66, 100, "#f89441", "SUPERESTRELLAS")
        ]
        for x0, x1, y0, y1, color, label in quads:
            fig_nb.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1, fillcolor=color, opacity=0.75, line=dict(color="rgba(255,255,255,0.3)", width=1))
            fig_nb.add_annotation(x=(x0+x1)/2, y=y1-2.5, text=f"<b>{label}</b>", showarrow=False, font=dict(size=9, color="white"))
        
        if es_confa or es_gerencia:
            fig_nb.add_trace(go.Scatter(x=df_grupo['DES'], y=df_grupo['IND_POT'], mode='markers', text=df_grupo['Nombre_Lider'], hoverinfo="text", marker=dict(size=10, color='red', symbol='diamond', line=dict(width=1, color='white'))))
        else:
            fig_nb.add_trace(go.Scatter(x=[d.DES], y=[d.IND_POT], mode='markers+text', text=[f"({d.DES}, {round(d.IND_POT,1)}%)"], textposition="top center", textfont=dict(color="white", size=11), marker=dict(size=14, color='red', symbol='diamond', line=dict(width=2, color='white'))))
        
        fig_nb.update_layout(xaxis=dict(title="Desempeño", tickvals=[1,2,3], range=[0.4, 3.6]), yaxis=dict(title="Potencial (%)", tickvals=[0, 33.3, 66.6, 100], range=[-5, 105]), template="plotly_dark", height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_nb, use_container_width=True)

    with cnb2:
        st.markdown(f"<div class='metric-box'><h3>{cuadrante}</h3><hr><p><b>Potencial Individual:</b> {round(d.IND_POT,2)}%</p><p><b>Desempeño:</b> {d.DES}</p><p><b>Autoevaluación Potencial:</b> {round(d.AUTO_POT,2)}%</p></div>", unsafe_allow_html=True)

    if (es_confa or es_gerencia) and not df_grupo.empty:
        st.markdown("### 🗺️ Matriz de Ubicación de Talentos")
        df_grupo['Cuadrante'] = df_grupo.apply(lambda x: obtener_cuadrante_confa(x['IND_POT'], x['DES']), axis=1).astype(str)
        
        c_mat1, c_mat2, c_mat3 = st.columns(3)
        with c_mat1: 
            names = df_grupo[df_grupo['Cuadrante'].str.contains("ENIGMA", na=False)]['Nombre_Lider'].tolist()
            st.markdown(f"<div class='quadrant-box' style='background-color: #b5de2b;'><div class='quad-title'>ENIGMA</div><div class='name-list'>{'<br>'.join(names) if names else 'Sin registros'}</div></div>", unsafe_allow_html=True)
        with c_mat2:
            names = df_grupo[df_grupo['Cuadrante'].str.contains("CRECIMIENTO", na=False)]['Nombre_Lider'].tolist()
            st.markdown(f"<div class='quadrant-box' style='background-color: #fde725; color: black;'><div class='quad-title'>ESTRELLA CREC.</div><div class='name-list'>{'<br>'.join(names) if names else 'Sin registros'}</div></div>", unsafe_allow_html=True)
        with c_mat3:
            names = df_grupo[df_grupo['Cuadrante'].str.contains("SUPERESTRELLAS", na=False)]['Nombre_Lider'].tolist()
            st.markdown(f"<div class='quadrant-box' style='background-color: #f89441;'><div class='quad-title'>SUPERESTRELLAS</div><div class='name-list'>{'<br>'.join(names) if names else 'Sin registros'}</div></div>", unsafe_allow_html=True)

        c_mat4, c_mat5, c_mat6 = st.columns(3)
        with c_mat4:
            names = df_grupo[df_grupo['Cuadrante'].str.contains("DILEMA", na=False)]['Nombre_Lider'].tolist()
            st.markdown(f"<div class='quadrant-box' style='background-color: #31688e;'><div class='quad-title'>DILEMA</div><div class='name-list'>{'<br>'.join(names) if names else 'Sin registros'}</div></div>", unsafe_allow_html=True)
        with c_mat5:
            names = df_grupo[df_grupo['Cuadrante'].str.contains("EMPLEADOS CLAVE", na=False)]['Nombre_Lider'].tolist()
            st.markdown(f"<div class='quadrant-box' style='background-color: #21918c;'><div class='quad-title'>EMPLEADOS CLAVE</div><div class='name-list'>{'<br>'.join(names) if names else 'Sin registros'}</div></div>", unsafe_allow_html=True)
        with c_mat6:
            names = df_grupo[df_grupo['Cuadrante'].str.contains("FUTURAS ESTRELLAS", na=False)]['Nombre_Lider'].tolist()
            st.markdown(f"<div class='quadrant-box' style='background-color: #5ec962;'><div class='quad-title'>FUTURAS ESTRELLAS</div><div class='name-list'>{'<br>'.join(names) if names else 'Sin registros'}</div></div>", unsafe_allow_html=True)

        c_mat7, c_mat8, c_mat9 = st.columns(3)
        with c_mat7:
            names = df_grupo[df_grupo['Cuadrante'].str.contains("ICEBERG", na=False)]['Nombre_Lider'].tolist()
            st.markdown(f"<div class='quadrant-box' style='background-color: #440154;'><div class='quad-title'>ICEBERG</div><div class='name-list'>{'<br>'.join(names) if names else 'Sin registros'}</div></div>", unsafe_allow_html=True)
        with c_mat8:
            names = df_grupo[df_grupo['Cuadrante'].str.contains("EFECTIVOS", na=False)]['Nombre_Lider'].tolist()
            st.markdown(f"<div class='quadrant-box' style='background-color: #482878;'><div class='quad-title'>EFECTIVOS</div><div class='name-list'>{'<br>'.join(names) if names else 'Sin registros'}</div></div>", unsafe_allow_html=True)
        with c_mat9:
            names = df_grupo[df_grupo['Cuadrante'].str.contains("CONFIABLES", na=False)]['Nombre_Lider'].tolist()
            st.markdown(f"<div class='quadrant-box' style='background-color: #3b528b;'><div class='quad-title'>PROF. CONFIABLES</div><div class='name-list'>{'<br>'.join(names) if names else 'Sin registros'}</div></div>", unsafe_allow_html=True)

    # --- BLOQUE IA: PROMPT MAESTRO INTEGRADO ---
    st.divider()
    if st.button("🚀 GENERAR INFORME"):
        texto_gerencia = ""
        if es_gerencia or es_confa:
            texto_gerencia = "NOTA: Este es un análisis GRUPAL. No hables de individuos, habla de capacidad instalada del equipo y cultura organizacional de la gerencia."

        prompt_maestro = f"""Actúa como consultor senior de DESARROLLO DE LIDERAZGO Barrett. Genera un reporte para {lider_sel}. DATOS: {d.to_json()} donde AUTO es Autoevaluación, INDI es Ponderado Individual, ORG es Ponderado organizacional (Promedio de resultados organizacionales) y CANT es cantidad de respuestas o evaluadores. Si alguien tiene todo 0 en AUTO es porque no hizo Autoevalaucion para que lo tengas presente en la comparativa. Si ves que sus resultados INDI son muy bajos, revisa que al menos CANT_JEFE y CANT_PAR sean mínimo 1, si no ahí esta el error y dejaremos en el reporte ese hallazgo de forma obligatoria pues seria un sesgo matemático. Si no encontramos esas inconsistencias no mencionaremos por nada del mundo esta información en el resto del informe, si y solo si se cumplen una de esas restricciones.
        PROHIBIDO USAR ANGLICISMOS. REDACTA TODO EN ESPAÑOL PURO.
        CONTEXTO BARRETT:
        - L1: Gestor de Crisis. Foco en estabilidad y viabilidad operativa. (Supervivencia)
        - L2: Constructor de Relaciones. Foco en armonía y respeto mutuo. (Relaciones)
        - L3: Gestor Organizador. Foco en eficiencia y resultados de calidad. (Autoestima)
        - L4: Facilitador Influyente. Foco en innovación y adaptabilidad. (Transformación)
        - L5: Integrador Inspirador. Foco en integridad y valores. (Cohesión Interna)
        - L6: Mentor Socio. Foco en colaboración y mentoría. (Hacer la Diferencia)
        - L7: Visionario Sabio. Foco en propósito y visión de largo plazo. (Servicio)
        CONTEXTO NINEBOX CONFA
        Usa las 9 definiciones de CONFA para el análisis:
        -ENIGMA: Líder con alto potencial pero desempeño bajo (ubicarlo bien o revisar jefe).
        -ESTRELLA CRECIENTE: Alto potencial, desempeño esperado (sacar de zona de confort).
        -SUPERESTRELLA: Mejor opción para sucesión (reconocer y premiar).
        -DILEMA: Potencial medio, desempeño bajo (trabajar motivación).
        -EMPLEADO CLAVE: Prometedor (retar y motivar).
        -FUTURA ESTRELLA: Alto desempeño, potencial medio (puestos clave).
        -ICEBERG: Bajo potencial y desempeño (observar o decidir desvinculación).
        -EFECTIVO: Desempeño medio, bajo potencial (incitar a aprender cosas nuevas).
        -PROFESIONAL CONFIABLE: Desempeño excepcional, bajo potencial liderazgo (reconocer esfuerzo y desarrollar liderazgo).

        REGLAS DE ORO: 
        {texto_gerencia}
        - INICIA DIRECTAMENTE. PROHIBIDO SALUDOS O INTRODUCCIONES o RESMENES O APRECIACIONES.
        - PROHIBIDO USAR: "desempeño", "brechas", "puntos ciegos" o hablar desde defectos o fallos, debe ser un feedback totalmente apreciativo.
        - USA: "desarrollo", "alineación", "influencia", "oportunidad de expansión".
        - RÚBRICA NIVELES DE BARRET: Bajo (<65), Medio (65-75), Alto (75-85), Superior (>85).
        - RÚBRICA DESEMPEÑO CONFA (POTENCIAL): DEBAJO DE LO ACORDADO = Bajo (1), EN LO ACORDADO = ALTO (2), SUPERA LO ACORDADO = SUPERIOR (3).
        - SI CANT_JEFE es 0: Debes iniciar el informe con una ADVERTENCIA ESTRATÉGICA indicando que el ponderado individual se ve severamente afectado (sesgo a la baja) debido a la ausencia de la valoración del líder directo (40% del peso).
        - SI CANT_PAR es 0: Debes iniciar el informe con una ADVERTENCIA ESTRATÉGICA indicando que el ponderado individual se ve severamente afectado (sesgo a la baja) debido a la ausencia de la valoración del minimo 1 par (20% del peso si tiene colaboradores a cargo, 40% si no tiene colaboradores a cargo).
        - SI CANT_AUTO es 0: Indica que no existe punto de comparación interno.
        - Si no hay estos ceros, no menciones nada de esto.

        ESTRUCTURA informe OBLIGATORIA: Respeta estrictamente los titulos, números y puntos hasta los dos puntos (:), por ejemplo 1. DESCRIPCIÓN POR NIVELES, 2. ANÁLISIS DE AUTOVALORACIÓN
        1. DESCRIPCIÓN POR NIVELES: Lista de L1 a L7 con el nombre de contexto Barret (Ejemplo Nivel 1: Gestor de Crisis). Clasifica cada nivel basándote en el 'Ponderado Individual' usando la rúbrica (Bajo, Medio, Alto, Superior) y las definiciones Barrett anteriores para generar una descripción según el modelo Barret y el nivel de la rubrica del líder. Siempre una lista de Nivel 1 a Nivel 7 no lo hagas en 1 solo párrafo porque confunde
        2. ANÁLISIS DE AUTOVALORACIÓN: Un párrafo. Analiza alineación percepción interna (Autoevaluacion) vs colectiva (Ponderado individual que es la evaluación de Jefe directo, Colaboradores a cargo y Pares). Resalta donde la influencia externa es mayor a la autopercepción, o aquellos puntos donde la autoevaluacion sea mayor en rubrica a lo evaluado pues son 2 cosas diferentes a trabajar según el nivel de conciencia.
        3. MATRIZ DE MADUREZ: Un párrafo sólido. Analiza sintonía del líder (Ponderado Individual) con el Ponderado Organizacional basándote en la RÚBRICA NIVELES DE BARRET.
        4. PERFIL DE LIDERAZGO: Un párrafo sólido. Define el estilo predominante según el promedio más alto (Liderazgo: {round(liderazgo_prom,1)}%, Transición: {round(transicion_prom,1)}%, Gerencia: {round(gerencia_prom,1)}%) y ofrece 3 recomendaciones de expansión para llegar a un equilibrio de las 3 dimensiones (Liderazgo Transicion and Gerencia) punto seguido.
        5. POSICIONAMIENTO ESTRATÉGICO DE TALENTO (Potencial y NineBox): Un párrafo sólido y técnico. Identifica el cuadrante asignado ({cuadrante}) y utiliza su definición estratégica de Confa (CONTEXTO NINEBOX CONFA) para explicar la situación actual del evaluado. Analiza la brecha o alineación entre la Autoevaluacion de potencial (AUTO_POT ({d.AUTO_POT}%)) and el Resultado de evaluacion de potencial 360° ({d.IND_POT}%), determinando si existe una sobrevaloración o una subvaloración del propio potencial de crecimiento. Establece la 'Tendencia de Transición' evaluando qué tan cerca está de los límites de la rúbrica (Bajo <60, ALto 60-80, Superior >80) and define, basándose en el cruce con Desempeño Organizacional (Nivel {d.DES}), qué acciones de retención, motivación o movilidad interna son imperativas para maximizar su valor en la organización. Si el Resultado de evaluacion de potencial 360° es significativamente más alto que la Autoevaluacion de potencial, resalta el "Talento Oculto"; si es al contrario, analiza la necesidad de un ajuste de expectativas de carrera. Termina con una frase sobre la proyección de este perfil hacia posiciones de mayor jerarquía o roles técnicos expertos según sea el caso.
        """
        try:
            with st.spinner('Analizando...'):
                res = model.generate_content(prompt_maestro)
                st.session_state.informe_cache[lider_sel] = res.text
                st.write(res.text)
        except Exception as e: st.error(e)

    # --- 6. GENERACIÓN DE REPORTES PDF ---
    if lider_sel in st.session_state.informe_cache:
        st.divider()
        col_btn1, col_btn2 = st.columns(2)

        def generar_pdf_final(tipo="GH"):
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            with tempfile.TemporaryDirectory() as tmp_dir:
                def save_pdf_chart(fig, name, title=""):
                    # Eliminamos emojis solo en el título del layout de Plotly para el PDF
                    titulo_limpio = title.replace("📊 ", "").replace("⏳ ", "").replace("🎯 ", "").replace("⚖️ ", "").replace("🟦 ", "")
                    fig.update_layout(template="plotly", paper_bgcolor='white', plot_bgcolor='white', font=dict(color='black'), title=dict(text=titulo_limpio, x=0.5, font=dict(size=14), y=0.95), margin=dict(t=60, b=20, l=10, r=10))
                    path = os.path.join(tmp_dir, name)
                    fig.write_image(path, engine="kaleido", scale=2)
                    return path

                # --- PÁGINA 1: CONTEXTO (SOLO COLABORADOR) ---
                if tipo == "COLABORADOR":
                    pdf.add_page()
                    pdf.set_font('Helvetica', 'B', 16); pdf.cell(0, 10, 'MODELO DE LIDERAZGO CONFA', ln=True, align='C'); pdf.ln(5)
                    pdf.set_font('Helvetica', 'B', 12); pdf.cell(0, 10, 'Introducción al Modelo Barrett', ln=True); pdf.ln(2)
                    pdf.set_font('Helvetica', '', 10)
                    pdf.multi_cell(0, 5, "El liderazgo en Confa se fundamenta en el Modelo de Barrett, un marco diseñado para liberar el potencial humano a través de la comprensión de las necesidades y motivaciones que subyacen al comportamiento. Este modelo evalúa siete niveles de consciencia, permitiendo a los líderes transitar desde la estabilidad operativa hasta el servicio con visión de futuro.\n\nEl enfoque de esta evaluación no es punitivo, sino de desarrollo y aprendizaje. Busca identificar fortalezas y oportunidades de expansión para potenciar el bienestar individual y el propósito colectivo de Confa.")
                    pdf.ln(5); pdf.set_font('Helvetica', 'B', 11); pdf.cell(0, 10, 'Interpretación de Niveles de Desarrollo', ln=True); pdf.ln(2)
                    
                    filas = [
                        ["L7: Visionario (Servicio)", "Falta de ética o humildad. No conecta el día a día con el propósito mayor de Confa.", "Perspectiva ocasional. Entiende la visión pero solo la comparte en momentos clave o formales.", "Liderazgo ético. Decide pensando en el bien común y comparte una visión clara seguido.", "Sabiduría y Humildad. Inspira a ir más allá del mínimo esperado y maneja el caos con calma total."],
                        ["L6: Mentor (Hacer la Diferencia)", "Falta de empatía. Se enfoca solo en sus tareas y no en las relaciones externas o el entorno.", "Relaciones intermitentes. Colabora con otras áreas solo cuando es estrictamente necesario para un proyecto.", "Mentor activo. Dedica tiempo a enseñar y dar retroalimentación útil para resolver mejor y más rápido.", "Socio Estratégico. Maestro en coaching; crea alianzas que generan valor social y ambiental duradero."],
                        ["L5: Integrador (Cohesión Interna)", "Falta de pasión y visión. No actúa bajo los valores de la organización; genera desconfianza.", "Confianza selectiva. Explica el para qué de las tareas solo a personas de su círculo cercano.", "Valores en acción. Decide con los valores de Confa en mente y mantiene un buen ambiente de equipo.", "Inspirador auténtico. Su ejemplo hace que la gente se sienta profundamente orgullosa de su trabajo."],
                        ["L4: Facilitador (Transformación)", "Controlador y rígido. Teme al riesgo; se enfoca poco en la innovación o la estrategia de cambio.", "Cautela al cambio. Se adapta a las prioridades pero prefiere los métodos conocidos.", "Facilitador del aprendizaje. Delega con confianza y aprende de los errores para ayudar a otros.", "Evolución Valiente. Empodera a las personas y promueve activamente el equilibrio vida-trabajo."],
                        ["L3: Organizador (Autoestima)", "Burocrático o estatus. Falla al enfocarse en resultados; seguimiento inconsistente de metas.", "Productividad bajo procesos. Cumple acuerdos pero pone trámites de más que frenan el trabajo.", "Orientado a la excelencia. Define metas claras, usa métricas y busca formas sencillas de trabajar mejor.", "Maestro de la Eficiencia. Domina la complejidad; deja prácticas que funcionan perfectamente sin su presencia."],
                        ["L2: Relaciones (Relación)", "Conflictivo o evitativo. Evita conversaciones difíciles o da muchas vueltas para hablar.", "Comunicación puntual. Reconoce el buen trabajo pero no de forma constante o pública.", "Constructor de armonía. Gestiona conflictos, habla claro y a tiempo, incluso en temas difíciles.", "Conexión Total. Escucha de verdad, trata a todos con respeto y es accesible para todo el staff."],
                        ["L1: Crisis (Supervivencia)", "Dictatorial o incapaz de confiar. Descuida la seguridad y bienestar del equipo; malgasta recursos.", "Viabilidad básica. Se mantiene tranquilo ante problemas menores pero se desborda en crisis reales.", "Gestión prudente. Piensa en los riesgos antes de decidir y cuida los recursos como si fueran propios.", "Calma en la Adversidad. Maneja el caos con sabiduría; es el pilar de seguridad y bienestar del equipo."]
                    ]
                    
                    # Encabezados de tabla - CORRECCIÓN: Usar cell para evitar traslape
                    pdf.set_font('Helvetica', 'B', 7); pdf.set_fill_color(240, 240, 240)
                    col_w = [30, 40, 40, 40, 40]
                    headers = ["Nivel de Consciencia", "Bajo (Reactivo / Limitado)", "Medio (Funcional / En Desarrollo)", "Alto (Competente / Consistente)", "Superior (Ejemplar / Maestría)"]
                    
                    y_h = pdf.get_y()
                    for i, h in enumerate(headers):
                        pdf.set_xy(10 + sum(col_w[:i]), y_h)
                        # Usamos cell en lugar de multicell para que los encabezados cortos no traslapen
                        pdf.cell(col_w[i], 10, h, 1, 0, 'C', True)
                    pdf.ln(10)

                    # Cuerpo de la tabla con cálculo dinámico de altura por fila
                    pdf.set_font('Helvetica', '', 6)
                    for f in filas:
                        y_pre = pdf.get_y()
                        
                        # PASO 1: Calcular la altura que necesita la fila basándose en la columna con más texto
                        alturas = []
                        for i, txt in enumerate(f):
                            # Obtenemos la cantidad de líneas que ocupará el texto
                            n_lines = len(pdf.multi_cell_text(txt, col_w[i]))
                            alturas.append(n_lines * 3.2) # 3.2 es el interlineado estándar para fuente 6
                        
                        max_h = max(alturas)
                        if max_h < 8: max_h = 8 # Altura mínima
                        
                        # Salto de página si no cabe la fila completa
                        if y_pre + max_h > 265:
                            pdf.add_page()
                            y_pre = pdf.get_y()
                        
                        # PASO 2: Dibujar las celdas asegurando que todas cierren con la misma altura
                        for i, txt in enumerate(f):
                            pdf.set_xy(10 + sum(col_w[:i]), y_pre)
                            # Dibujamos el borde con la altura máxima
                            pdf.rect(10 + sum(col_w[:i]), y_pre, col_w[i], max_h)
                            # Escribimos el texto con multicell (interlineado 3.2)
                            pdf.multi_cell(col_w[i], 3.2, txt, 0, 'L')
                        
                        pdf.set_y(y_pre + max_h)

                # --- PÁGINA DASHBOARD (AMBOS) ---
                pdf.add_page()
                pdf.set_font('Helvetica', 'B', 16); pdf.cell(0, 10, 'REPORTE ESTRATÉGICO INTEGRAL', ln=True, align='C')
                pdf.set_font('Helvetica', '', 12); pdf.cell(0, 8, f'Evaluado: {lider_sel}', ln=True, align='C')
                pdf.set_font('Helvetica', 'B', 10); pdf.cell(0, 8, f'Total Evaluadores: {int(d.CANT_EVAL)} | Auto: {int(d.CANT_AUTO)} | Jefe: {int(d.CANT_JEFE)} | Pares: {int(d.CANT_PAR)} | Colab: {int(d.CANT_COL)}', ln=True, align='C')
                
                pdf.ln(2); pdf.set_font('Helvetica', 'B', 11); pdf.cell(0, 10, 'Frecuencia de comportamientos por niveles (%)', ln=True)
                y_frec = pdf.get_y()
                pdf.image(save_pdf_chart(generar_fig_barras(v_auto, "", "#3498db"), "b1.png", "Autoevaluacion"), x=10, y=y_frec, w=60)
                pdf.image(save_pdf_chart(generar_fig_barras(v_ind, "", "#2ecc71"), "b2.png", "Evaluacion 360"), x=75, y=y_frec, w=60)
                pdf.image(save_pdf_chart(generar_fig_barras(v_org, "", "#e74c3c"), "b3.png", "Promedio Organizacional"), x=140, y=y_frec, w=60)
                
                pdf.set_y(y_frec + 43); pdf.set_font('Helvetica', 'B', 11); pdf.cell(0, 10, 'Resultados Evaluación 360 (Niveles Barrett)', ln=True)
                y_relojes_base = pdf.get_y()
                pdf.image(save_pdf_chart(generar_fig_reloj(v_auto, False), "r1p.png", "Autoevaluacion"), x=35, y=y_relojes_base+3, w=60)
                pdf.image(save_pdf_chart(generar_fig_reloj(v_ind, False), "r2p.png", "Evaluacion 360"), x=88, y=y_relojes_base+3, w=60)
                pdf.image(save_pdf_chart(generar_fig_reloj(v_org, False), "r3p.png", "Promedio organizacional"), x=141, y=y_relojes_base+3, w=60)
                
                pdf.set_font('Helvetica', '', 7); pdf.set_text_color(100, 100, 100)
                niv_m = ["L7-Visionario", "L6-Mentor Socio", "L5-Autentico", "L4-Facilitador Innovador", "L3-Gestor de Desempeño", "L2-Gestor de Relaciones", "L1-Gestor de Crisis"]
                for i, txt in enumerate(niv_m): pdf.text(10, y_relojes_base + 10 + (i * 4), txt)
                pdf.set_text_color(0, 0, 0)
                
                pdf.set_y(y_relojes_base + 45); pdf.set_font('Helvetica', 'B', 11); pdf.cell(0, 10, 'Alineacion de Consciencia e Indice de Equilibrio', ln=True)
                y_radar = pdf.get_y()
                pdf.image(save_pdf_chart(fig_radar, "radar.png", ""), x=10, y=y_radar, w=95)
                pdf.image(save_pdf_chart(fig_dim, "dim.png", ""), x=110, y=y_radar + 5, w=90)

                if tipo == "GH":
                    pdf.add_page(); pdf.set_font('Helvetica', 'B', 11); pdf.cell(0, 10, 'Mapa de Talento NineBox Confa', ln=True)
                    fig_nb.update_layout(template="plotly", paper_bgcolor='white', plot_bgcolor='white', font=dict(color='black'))
                    img_nb = os.path.join(tmp_dir, "nb.png"); fig_nb.write_image(img_nb, engine="kaleido", scale=4); pdf.image(img_nb, x=25, w=160)

                pdf.add_page(); pdf.set_font('Helvetica', 'B', 13); pdf.cell(0, 10, 'Analisis Ejecutivo Estrategico', ln=True); pdf.ln(5)
                pdf.set_font('Helvetica', '', 10)
                
                texto_ia = st.session_state.informe_cache[lider_sel]
                if tipo == "COLABORADOR":
                    patron_corte = r'(?m)^\s*\**5[\.\s:]+POSICIONAMIENTO.*'
                    texto_ia = re.split(patron_corte, texto_ia, flags=re.IGNORECASE | re.DOTALL)[0]
                
                limpio = texto_ia.replace("**", "").encode('latin-1', 'replace').decode('latin-1')
                pdf.multi_cell(0, 6, limpio)

            return pdf.output()

        with col_btn1: st.download_button("📄 INFORME GESTIÓN HUMANA", data=bytes(generar_pdf_final(tipo="GH")), file_name=f"Reporte_GH_{lider_sel}.pdf", mime="application/pdf")
        with col_btn2: st.download_button("👤 INFORME COLABORADOR", data=bytes(generar_pdf_final(tipo="COLABORADOR")), file_name=f"Reporte_Colaborador_{lider_sel}.pdf", mime="application/pdf")
