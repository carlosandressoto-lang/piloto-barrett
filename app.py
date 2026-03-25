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

st.markdown("""
<style>
    .main { font-family: 'Helvetica Neue', sans-serif; }
    h1 { color: #BFDBFE !important; text-align: center; }
    .titulo-col { text-align: center; font-weight: bold; margin-bottom: 10px; font-size: 1.1rem; }
    .leyenda-v3 { display: flex; flex-direction: column; justify-content: space-between; height: 340px; margin-top: 35px; padding-right: 10px; border-right: 1px solid #334155; }
    .item-ley { height: 48px; display: flex; align-items: center; justify-content: flex-end; font-size: 0.85rem; font-weight: bold; }
    .metric-box { background-color: rgba(30, 41, 59, 0.5); padding: 10px; border-radius: 10px; text-align: center; border: 1px solid #334155; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN IA SEGURA ---
try:
    api_key_segura = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key_segura)
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error("Error: Configura 'GEMINI_API_KEY' en los Secrets.")

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
        cols_to_fix = [c for c in df.columns if ('L' in c and any(x in c for x in ['AUTO', 'INDIV', 'ORG'])) or 'CANT_' in c or 'POT' in c or 'DES' == c]
        for col in cols_to_fix:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except Exception as e:
        st.error(f"Error crítico al conectar con Google Sheets: {e}")
        return None

df = load_data()

# --- 4. LÓGICA NINEBOX CONFA (9 CUADRANTES PDF) ---
def obtener_cuadrante_confa(pot, des):
    if pot < 60: p_label = "BAJO"
    elif pot < 80: p_label = "MEDIO"
    else: p_label = "ALTO"
    if des <= 1: d_label = "BAJO"
    elif des <= 2: d_label = "MEDIO"
    else: d_label = "ALTO"
    mapping = {
        ("ALTO", "BAJO"): "ENIGMA DIAMANTE EN BRUTO", ("ALTO", "MEDIO"): "FUTURA ESTRELLA EN CRECIMIENTO", ("ALTO", "ALTO"): "FUTUROS LIDERES SUPERESTRELLAS",
        ("MEDIO", "BAJO"): "DILEMA", ("MEDIO", "MEDIO"): "EMPLEADOS CLAVES", ("MEDIO", "ALTO"): "FUTURAS ESTRELLAS",
        ("BAJO", "BAJO"): "ICEBERG", ("BAJO", "MEDIO"): "EFECTIVOS", ("BAJO", "ALTO"): "PROFESIONALES CONFIABLES"
    }
    return mapping.get((p_label, d_label), "No clasificado")

def escalar_visual_potencial(val):
    if val <= 60: return (val / 60) * 33.33
    elif val <= 80: return 33.33 + ((val - 60) / 20) * 33.33
    else: return 66.66 + ((val - 80) / 20) * 33.33

if df is not None:
    lideres = sorted(df['Nombre_Lider'].unique())
    lider_sel = st.selectbox("Seleccione el líder para el análisis detallado:", lideres)
    d = df[df['Nombre_Lider'] == lider_sel].iloc[0]
    es_gerencia = lider_sel.startswith("GER_")

    v_auto = [d.AUTO_L1, d.AUTO_L2, d.AUTO_L3, d.AUTO_L4, d.AUTO_L5, d.AUTO_L6, d.AUTO_L7]
    v_ind = [d.INDIV_L1, d.INDIV_L2, d.INDIV_L3, d.INDIV_L4, d.INDIV_L5, d.INDIV_L6, d.INDIV_L7]
    v_org = [d.ORG_L1, d.ORG_L2, d.ORG_L3, d.ORG_L4, d.ORG_L5, d.ORG_L6, d.ORG_L7]
    liderazgo_prom = (d.INDIV_L5 + d.INDIV_L6 + d.INDIV_L7) / 3
    transicion_prom = d.INDIV_L4
    gerencia_prom = (d.INDIV_L1 + d.INDIV_L2 + d.INDIV_L3) / 3

    # Funciones de color Barrett
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
        labels = ['L7 - Visionario', 'L6 - Mentor', 'L5 - Auténtico', 'L4 - Facilitador', 'L3 - Desempeño', 'L2 - Relaciones', 'L1 - Crisis']
        v_plot = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
        fig = go.Figure(go.Bar(x=v_plot, y=labels, orientation='h', marker_color=color, text=[f"{round(v,1)}%" for v in v_plot], textposition='inside'))
        fig.update_layout(title=dict(text=titulo, x=0.5), xaxis_range=[0, 105], height=350, template="plotly_dark", margin=dict(l=0, r=10, t=40, b=20), yaxis=dict(autorange="reversed"))
        return fig

    def generar_fig_reloj(vals, incluir_leyenda=False, forzar_pdf=False):
        anchos_base = [6, 5, 4, 3.2, 4, 5, 6] 
        v_rev = [vals[6], vals[5], vals[4], vals[3], vals[2], vals[1], vals[0]]
        colors_barrett = ["rgb(33,115,182)"]*3 + ["rgb(140,183,42)"] + ["rgb(241,102,35)"]*3
        labels_niveles = ["L7-Visionario", "L6-Mentor", "L5-Auténtico", "L4-Facilitador", "L3-Desempeño", "L2-Relaciones", "L1-Crisis"]
        fig = go.Figure()
        fig.add_trace(go.Funnel(y=labels_niveles if incluir_leyenda else [1,2,3,4,5,6,7], x=anchos_base, textinfo="none", hoverinfo="none", marker={"color": colors_barrett, "line": {"width": 1, "color": "rgba(255,255,255,0.3)"}}, connector={"visible": False}))
        for i, (val, ancho) in enumerate(zip(v_rev, anchos_base)):
            fig.add_annotation(x=0, y=i if incluir_leyenda else i+1, text=obtener_etiqueta(val), showarrow=False, font=dict(color=obtener_color_desarrollo(val), size=12, family='Arial Black'), bgcolor="white", bordercolor="rgba(255,255,255,0)", borderpad=4, width=ancho * 22.0)
        margen_l = 100 if (incluir_leyenda or forzar_pdf) else 10
        fig.update_layout(height=400, margin=dict(l=margen_l, r=20, t=10, b=10), yaxis=dict(visible=incluir_leyenda, tickfont=dict(size=10)), xaxis=dict(visible=False), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        return fig

    # --- RENDER DASHBOARD ---
    st.divider()
    st.markdown(f"""
    <div style="display: flex; justify-content: center; gap: 20px; margin-bottom: 20px;">
        <div class="metric-box"><b>Total Evaluadores:</b><br><span style="font-size: 1.5rem; color: #BFDBFE;">{int(d.CANT_EVAL)}</span></div>
        <div class="metric-box"><b>Auto:</b> {int(d.CANT_AUTO)} | <b>Jefe:</b> {int(d.CANT_JEFE)} | <b>Pares:</b> {int(d.CANT_PAR)} | <b>Colab:</b> {int(d.CANT_COL)}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader("📊 Frecuencia de comportamientos por niveles (%)")
    c1, c2, c3 = st.columns(3)
    with c1: st.plotly_chart(generar_fig_barras(v_auto, "Autovaloración", "#3498db"), key="b1_v")
    with c2: st.plotly_chart(generar_fig_barras(v_ind, "Individual (360)", "#2ecc71"), key="b2_v")
    with c3: st.plotly_chart(generar_fig_barras(v_org, "Promedio Organizacional", "#e74c3c"), key="b3_v")

    st.divider()
    cl, cr1, cr2, cr3 = st.columns([1, 1, 1, 1])
    with cl:
        st.markdown('<div class="titulo-col">Nivel Barrett</div>', unsafe_allow_html=True)
        niveles_barrett = ["L7 - Visionario", "L6 - Mentor", "L5 - Auténtico", "L4 - Facilitador", "L3 - Desempeño", "L2 - Relaciones", "L1 - Crisis"]
        st.markdown('<div class="leyenda-v3">' + ''.join([f'<div class="item-ley">{n}</div>' for n in niveles_barrett]) + '</div>', unsafe_allow_html=True)
    with cr1: st.markdown('<div class="titulo-col">Autovaloración</div>', unsafe_allow_html=True); st.plotly_chart(generar_fig_reloj(v_auto), key="r1_v")
    with cr2: st.markdown('<div class="titulo-col">Individual (360)</div>', unsafe_allow_html=True); st.plotly_chart(generar_fig_reloj(v_ind), key="r2_v")
    with cr3: st.markdown('<div class="titulo-col">Organizacional</div>', unsafe_allow_html=True); st.plotly_chart(generar_fig_reloj(v_org), key="r3_v")

    st.divider()
    col_radar, col_dim = st.columns([1.5, 1])
    with col_radar:
        st.subheader("🎯 Alineación de Consciencia y Entorno")
        fig_radar = go.Figure()
        cats = ['L1','L2','L3','L4','L5','L6','L7']
        for val, name, color in zip([v_auto, v_ind, v_org], ['Auto', 'Individual', 'Organizacional'], ['#3498db', '#2ecc71', '#e74c3c']):
            fig_radar.add_trace(go.Scatterpolar(r=val, theta=cats, fill='toself', name=name, line_color=color))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=500, template="plotly_dark", legend=dict(orientation="h", y=1.25, x=0.5, xanchor="center"))
        st.plotly_chart(fig_radar, key="radar_v")
    with col_dim:
        st.subheader("⚖️ Índice del Equilibrio de Liderazgo")
        vals_dim = [liderazgo_prom, transicion_prom, gerencia_prom]
        fig_dim = go.Figure(go.Bar(x=vals_dim, y=['Liderazgo (L5-L7)', 'Transición (L4)', 'Gerencia (L1-L3)'], orientation='h', marker_color=[obtener_color_desarrollo(v) for v in vals_dim], text=[f"{round(v,1)}% - {obtener_etiqueta(v)}" for v in vals_dim], textposition='inside'))
        fig_dim.update_layout(xaxis_range=[0, 105], height=400, template="plotly_dark", yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_dim, key="dim_v")

    # --- SECCIÓN NINEBOX DINÁMICA ---
    st.divider()
    st.subheader("🟦 Mapa de Talento NineBox Confa")
    cnb1, cnb2 = st.columns([1.5, 1])
    cuadrante = obtener_cuadrante_confa(d.IND_POT, d.DES)
    
    with cnb1:
        # LÓGICA DE COLOR DINÁMICO SEGÚN EL TEMA
        theme_is_dark = st.get_option("theme.base") == "dark"
        color_dinamico = "white" if theme_is_dark else "black"
        
        fig_nb = go.Figure()
        cuadrantes_specs = [
            (0.5, 1.5, 0, 33.33, "#440154", "ICEBERG"), (1.5, 2.5, 0, 33.33, "#482878", "EFECTIVOS"), (2.5, 3.5, 0, 33.33, "#3b528b", "PROF. CONFIABLES"),
            (0.5, 1.5, 33.33, 66.66, "#31688e", "DILEMA"), (1.5, 2.5, 33.33, 66.66, "#21918c", "EMP. CLAVE"), (2.5, 3.5, 33.33, 66.66, "#5ec962", "FUT. ESTRELLAS"),
            (0.5, 1.5, 66.66, 100, "#b5de2b", "ENIGMA"), (1.5, 2.5, 66.66, 100, "#fde725", "ESTRELLA CREC."), (2.5, 3.5, 66.66, 100, "#f89441", "SUPERESTRELLAS")
        ]
        for x0, x1, y0, y1, color, label in cuadrantes_specs:
            fig_nb.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1, fillcolor=color, opacity=0.4, line=dict(color="white", width=1))
            fig_nb.add_annotation(x=(x0+x1)/2, y=y1-2, text=f"<b>{label}</b>", showarrow=False, font=dict(size=8, color=color_dinamico))

        val_p = d.IND_POT
        if val_p < 10: pos = "top center"
        elif 28 <= val_p <= 38 or 62 <= val_p <= 70 or 76 <= val_p <= 84 or val_p >= 90: pos = "bottom center"
        else: pos = "top center"

        # WRAP DE NOMBRE RECALIBRADO
        nombre_wrap = lider_sel.replace(' ', '<br>', 1) if len(lider_sel) > 15 else lider_sel
        fig_nb.add_trace(go.Scatter(
            x=[d.DES], y=[d.IND_POT)], mode='markers+text', 
            marker=dict(size=12, color='white', symbol='diamond', line=dict(width=2, color='#BFDBFE')), 
            text=[f"<b>{nombre_wrap}</b><br>({round(d.IND_POT,2)}%)"], textposition=pos,
            hovertemplate=f"Potencial: {round(d.IND_POT,2)}%<br>Desempeño: {d.DES}<extra></extra>",
            textfont=dict(size=9, color=color_dinamico)
        ))
        fig_nb.update_layout(xaxis=dict(title="Desempeño (1-3)", tickvals=[1,2,3], range=[0.5, 3.5]), yaxis=dict(title="Potencial (Escala Confa)", tickvals=[0, 33.33, 66.66, 100], ticktext=["0%", "60%", "80%", "100%"], range=[-5, 105]), template="plotly_dark" if theme_is_dark else "plotly", height=500)
        st.plotly_chart(fig_nb, key="nb_v", use_container_width=True)

    with cnb2:
        st.markdown(f"""
        <div class="metric-box" style="text-align: left;">
            <h3 style="color:#BFDBFE; margin:0;">{cuadrante}</h3>
            <p><b>Potencial:</b> {d.IND_POT}% | <b>Desempeño:</b> {d.DES}</p>
            <p><b>Autoevaluación Potencial:</b> {d.AUTO_POT}%</p>
            <hr style="border:0.5px solid #334155;">
            <p style="font-size:0.85rem;">Cruce estratégico basado en el Análisis de Talento Confa 2026.</p>
        </div>
        """, unsafe_allow_html=True)

    if "informe_cache" not in st.session_state: st.session_state.informe_cache = {}

    st.divider()
    if st.button("🚀 GENERAR INFORME"):
        tipo_sujeto = "GERENCIA" if es_gerencia else "LÍDER"
        prompt_maestro = f"""
        Actúa como consultor senior de DESARROLLO DE LIDERAZGO Barrett. Genera un reporte para {lider_sel}. DATOS: {d.to_json()} donde AUTO es Autoevaluación, INDI es Ponderado Individual, ORG es Ponderado organizacional (Promedio de resultados organizacionales) y CANT es cantidad de respuestas o evaluadores. Si alguien tiene todo 0 en AUTO es porque no hizo Autoevalaucion para que lo tengas presente en la comparativa. Si ves que sus resultados INDI son muy bajos, revisa que al menos CANT_JEFE y CANT_PAR sean mínimo 1, si no ahí esta el error y dejaremos en el reporte ese hallazgo de forma obligatoria pues seria un sesgo matemático. Si no encontramos esas inconsistencias no mencionaremos por nada del mundo esta información en el resto del informe, si y solo si se cumplen una de esas restricciones.
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
        - INICIA DIRECTAMENTE. PROHIBIDO SALUDOS O INTRODUCCIONES o RESMENES O APRECIACIONES.
        - PROHIBIDO USAR: "desempeño", "brechas", "puntos ciegos" o hablar desde defectos o fallos, debe ser un feedback totalmente apreciativo.
        - USA: "desarrollo", "alineación", "influencia", "oportunidad de expansión".
        - RÚBRICA: Bajo (<65), Medio (65-75), Alto (75-85), Superior (>85).
        - SI CANT_JEFE es 0: Debes iniciar el informe con una ADVERTENCIA ESTRATÉGICA indicando que el ponderado individual se ve severamente afectado (sesgo a la baja) debido a la ausencia de la valoración del líder directo (40% del peso).
        - SI CANT_PAR es 0: Debes iniciar el informe con una ADVERTENCIA ESTRATÉGICA indicando que el ponderado individual se ve severamente afectado (sesgo a la baja) debido a la ausencia de la valoración del minimo 1 par (20% del peso si tiene colaboradores a cargo, 40% si no tiene colaboradores a cargo).
        - SI CANT_AUTO es 0: Indica que no existe punto de comparación interno.
        - Si no hay estos ceros, no menciones nada de esto.

        ESTRUCTURA informe OBLIGATORIA:
        1. DESCRIPCIÓN POR NIVELES: Lista de L1 a L7 con el nombre de contexto Barret (Ejemplo L1: Gestor de Crisis). Clasifica cada nivel basándote en el 'Ponderado Individual' usando la rúbrica (Bajo, Medio, Alto, Superior) y las definiciones Barrett anteriores para generar una descripción según el modelo Barret y el nivel de la rubrica del líder. Siempre una lista de Nivel 1 a Nivel 7 no lo hagas en 1 solo párrafo porque confunde
        2. ANÁLISIS DE AUTOVALORACIÓN: Un párrafo. Analiza alineación percepción interna (Autoevaluacion) vs colectiva (Ponderado individual que es la evaluación de Jefe directo, Colaboradores a cargo y Pares). Resalta donde la influencia externa es mayor a la autopercepción, o aquellos puntos donde la autoevaluacion sea mayor en rubrica a lo evaluado pues son 2 cosas diferentes a trabajar según el nivel de conciencia.
        3. MATRIZ DE MADUREZ: Un párrafo sólido. Analiza sintonía del líder (Ponderado Individual) con el Ponderado Organizacional basándote en la Rúbrica.
        4. PERFIL DE LIDERAZGO: Un párrafo sólido. Define el estilo predominante según el promedio más alto (Liderazgo: {round(liderazgo_prom,1)}%, Transición: {round(transicion_prom,1)}%, Gerencia: {round(gerencia_prom,1)}%) y ofrece 3 recomendaciones de expansión para llegar a un equilibrio de las 3 dimensiones (Liderazgo Transicion y Gerencia) punto seguido.
        5. POSICIONAMIENTO ESTRATÉGICO DE TALENTO (Potencial y NineBox): Un párrafo sólido y técnico. Identifica el cuadrante asignado ({cuadrante}) y utiliza su definición estratégica de Confa 2018 para explicar la situación actual del evaluado. Analiza la brecha o alineación entre la AUTO_POT ({d.AUTO_POT}%) y el IND_POT ({d.IND_POT}%), determinando si existe una sobrevaloración o una subvaloración del propio potencial de crecimiento. Establece la 'Tendencia de Transición' evaluando qué tan cerca está de los límites de la rúbrica (Bajo <60, Medio 60-80, Alto >80) y define, basándose en el cruce con DES (Nivel {d.DES}), qué acciones de retención, motivación o movilidad interna son imperativas para maximizar su valor en la organización. Si el IND_POT es significativamente más alto que la AUTO_POT, resalta el "Talento Oculto"; si es al contrario, analiza la necesidad de un ajuste de expectativas de carrera. Termina con una frase sobre la proyección de este perfil hacia posiciones de mayor jerarquía o roles técnicos expertos según sea el caso.
        """
        try:
            with st.spinner('Consolidando informe...'):
                response = model.generate_content(prompt_maestro)
                st.session_state.informe_cache[lider_sel] = response.text
        except Exception as e: st.error(f"Error IA: {e}")

    if lider_sel in st.session_state.informe_cache:
        st.markdown(f"### 📋 Informe Estratégico Integral: {lider_sel}")
        st.write(st.session_state.informe_cache[lider_sel])

        if st.button("📄 GENERAR REPORTE PDF"):
            with st.spinner('Procesando PDF...'):
                try:
                    pdf = FPDF()
                    pdf.set_auto_page_break(auto=True, margin=15)
                    pdf.add_page()
                    pdf.set_font('Helvetica', 'B', 14)
                    pdf.cell(0, 10, 'REPORTE ESTRATEGICO INTEGRAL (BARRETT + TALENTO)', ln=True, align='C')
                    pdf.set_font('Helvetica', '', 11)
                    pdf.cell(0, 10, f'Evaluado: {lider_sel}', ln=True, align='C')
                    pdf.ln(5)
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        def save_chart(fig, name, w=600, h=300):
                            fig.update_layout(template="plotly_dark" if theme_is_dark else "plotly", paper_bgcolor='white', font=dict(color="black", size=12), width=w, height=h)
                            path = os.path.join(tmp_dir, name)
                            fig.write_image(path, engine="kaleido", scale=2) 
                            return path
                        pdf.set_font('Helvetica', 'B', 10)
                        pdf.text(10, 43, "1. Frecuencia de comportamientos por niveles (%)")
                        pdf.image(save_chart(generar_fig_barras(v_auto, "Auto", "#3498db"), "b1.png"), x=10, y=45, w=60)
                        pdf.image(save_chart(generar_fig_barras(v_ind, "Individual", "#2ecc71"), "b2.png"), x=75, y=45, w=60)
                        pdf.image(save_chart(generar_fig_barras(v_org, "Organizacional", "#e74c3c"), "b3.png"), x=140, y=45, w=60)
                        pdf.text(10, 98, "2. Alineación de Consciencia y Entorno")
                        pdf.image(save_chart(fig_radar, "radar.png", 500, 400), x=10, y=101, w=95)
                        pdf.text(110, 98, "3. Índice del Equilibrio de Liderazgo")
                        pdf.image(save_chart(fig_dim, "dim.png", 500, 350), x=110, y=108, w=90)
                        pdf.text(15, 178, "4. Resultados Evaluación 360° (Niveles Barrett)")
                        r1_pdf = generar_fig_reloj(v_auto, incluir_leyenda=True); r2_pdf = generar_fig_reloj(v_ind, incluir_leyenda=False, forzar_pdf=True); r3_pdf = generar_fig_reloj(v_org, incluir_leyenda=False, forzar_pdf=True)
                        pdf.image(save_chart(r1_pdf, "r1.png", 500, 400), x=15, y=187, w=60); pdf.image(save_chart(r2_pdf, "r2.png", 500, 400), x=75, y=187, w=60); pdf.image(save_chart(r3_pdf, "r3.png", 500, 400), x=135, y=187, w=60)
                        pdf.add_page(); pdf.set_font('Helvetica', 'B', 12); pdf.cell(0, 10, '5. Posicionamiento Estratégico NineBox Confa', ln=True)
                        pdf.image(save_chart(fig_nb, "ninebox_pdf.png", 600, 400), x=35, y=25, w=140); pdf.set_y(105); pdf.set_font('Helvetica', 'B', 12); pdf.cell(0, 10, 'Análisis Ejecutivo Integral', ln=True); pdf.ln(2); pdf.set_font('Helvetica', '', 10)
                        limpio = st.session_state.informe_cache[lider_sel].replace("**", "").replace("###", "").replace("- ", "• ").encode('latin-1', 'replace').decode('latin-1')
                        pdf.multi_cell(0, 6, limpio)
                    output = pdf.output()
                    st.download_button(label="📥 Descargar Reporte Integral PDF", data=bytes(output), file_name=f"Reporte_Integral_{lider_sel}.pdf", mime="application/pdf")
                except Exception as e: st.error(f"Error PDF: {e}")
