import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# =============================
# 🔹 Configuración general
# =============================
page_bg = """
<style>
[data-testid="stAppViewContainer"] {
    background-color: #E6F2FF; /* Azul muy claro */
}
[data-testid="stHeader"] {
    background-color: #004080; /* Azul oscuro en encabezado */
}
</style>
"""
st.set_page_config(page_title="Tanque 3D", layout="wide")
st.sidebar.markdown("## ⚙️ Configuración")
intervalo = st.sidebar.slider("Intervalo de actualización (segundos)", 10, 120, 60)

CHANNEL_ID = "3031360"
READ_API_KEY = st.secrets.get("READ_API_KEY", "")
VOLUMEN_MAX = 80.0   # m³

# 🔄 Auto-refresh
try:
    from streamlit.runtime.scriptrunner import st_autorefresh
    st_autorefresh(interval=intervalo*1000, key="autorefresh")
except Exception:
    try:
        st.experimental_autorefresh(interval=intervalo*1000, key="autorefresh")
    except Exception:
        st.info("⚠️ Tu versión de Streamlit no soporta autorefresh automático.")

st.title("🌊 Acueducto Ovejas Tangua \n Ingeniería Mecatrónica - Universidad Mariana ")
st.write("**Autores: Titopia**")

# =============================
# 🔹 Estado inicial
# =============================
if "nivel_anterior" not in st.session_state:
    st.session_state.nivel_anterior = 0.0

# =============================
# 🔹 Función para obtener datos
# =============================
def obtener_datos(resultados=1000, start=None, end=None):
    if start and end:
        url = (
            f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json"
            f"?api_key={READ_API_KEY}&start={start}&end={end}"
        )
    else:
        url = (
            f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json"
            f"?api_key={READ_API_KEY}&results={resultados}"
        )

    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        feeds = data.get("feeds", [])
        if not feeds:
            return pd.DataFrame()

        df = pd.DataFrame(feeds)
        df["created_at"] = pd.to_datetime(df["created_at"])

        # Convertir todos los fields posibles
        for i in range(1, 9):  
            df[f"field{i}"] = pd.to_numeric(df.get(f"field{i}"), errors="coerce")

        return df.dropna(how="all", subset=[f"field{i}" for i in range(1, 9)])
    except Exception as e:
        st.error(f"Error obteniendo datos: {e}")
        return pd.DataFrame()

# =============================
# 🔹 Encabezado con logos
# =============================
col1, col2, col3 = st.columns([1, 3, 1])
with col1:
    st.image("umariana.png", width=200)
with col2:
    st.markdown(
        "<h2 style='text-align: center; background-color: white; color: #004080;'>"
        "🌊 Monitoreo acueducto Tambor-Ovejas</h2>",
        unsafe_allow_html=True
    )
with col3:
    st.image("grupo_social.png", width=200)

# =============================
# 🔹 Pestañas
# =============================
tab1, tab2, tab3, tab4 = st.tabs([
    "🌀 Tanque 3D (Volumen %)", 
    "📈 Gráficas históricas",
    "🌡️ Temp & Humedad",
    "📥 Descargas & Displays"
])

# =============================
# 🔹 TAB 1: Tanque 3D
# =============================
with tab1:
    st.subheader("Tanque en 3D mostrando % de Volumen")
    df_ultimo = obtener_datos(resultados=1)

    if not df_ultimo.empty:
        altura = df_ultimo["field1"].iloc[-1]
        caudal = df_ultimo["field2"].iloc[-1]
        volumen = df_ultimo["field3"].iloc[-1]
        ultima_fecha = df_ultimo["created_at"].iloc[-1].strftime("%Y-%m-%d %H:%M:%S")
    else:
        altura, caudal, volumen, ultima_fecha = 0.0, 0.0, 0.0, "Sin datos"

    # Nivel normalizado
    nivel_objetivo = max(0.0, min(1.0, volumen / VOLUMEN_MAX))
    niveles = np.linspace(st.session_state.nivel_anterior, nivel_objetivo, 20)
    st.session_state.nivel_anterior = nivel_objetivo
    nivel_suave = niveles[-1]

    ALTURA_ESCALA = 100
    altura_agua = nivel_suave * ALTURA_ESCALA

    # Geometría cilindro
    theta = np.linspace(0, 2*np.pi, 50)
    x, y = np.cos(theta), np.sin(theta)
    z_tanque = np.linspace(0, ALTURA_ESCALA, 2)
    x_tanque, z1 = np.meshgrid(x, z_tanque)
    y_tanque, _ = np.meshgrid(y, z_tanque)
    z_agua = np.linspace(0, altura_agua, 2)
    x_agua, z3 = np.meshgrid(x, z_agua)
    y_agua, _ = np.meshgrid(y, z_agua)

    # --- Color dinámico del tanque según nivel ---
    if nivel_objetivo <= 0.3:  # ≤ 30 %
        tanque_color = "Reds"
        tanque_opacidad = 0.5
        st.error(f"⚠️ El tanque está en nivel crítico ({nivel_objetivo*100:.1f}%)")
    else:
        tanque_color = "Greens"
        tanque_opacidad = 0.3

    # --- Plot ---
    fig = go.Figure()
    fig.add_surface(
        x=x_tanque, y=y_tanque, z=z1,
        showscale=False, opacity=tanque_opacidad, colorscale=tanque_color
    )

    if volumen > 0:
        fig.add_surface(
            x=x_agua, y=y_agua, z=z3,
            showscale=False, opacity=0.6, colorscale="Blues"
        )

    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(range=[0, ALTURA_ESCALA], title="Volumen (%)")
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Indicadores ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Nivel (%)", f"{nivel_objetivo*100:.1f}%")
    c2.metric("Volumen (m³)", f"{volumen:.2f} / {VOLUMEN_MAX:.0f}")
    c3.metric("Altura (m)", f"{altura:.2f}")
    c4.metric("Caudal (L/min)", f"{caudal:.2f}")

    st.caption(f"📅 Último dato recibido: {ultima_fecha}")

# =============================
# 🔹 TAB 2: Gráficas históricas
# =============================
with tab2:
    st.subheader("Últimos 50 valores")
    df_historico = obtener_datos(resultados=50)

    if not df_historico.empty:
        fig1 = px.line(df_historico, x="created_at", y="field3", markers=True, title="Volumen (m³)")
        fig2 = px.line(df_historico, x="created_at", y="field1", markers=True, title="Altura (m)")
        fig3 = px.line(df_historico, x="created_at", y="field2", markers=True, title="Caudal (L/min)")

        st.plotly_chart(fig1, use_container_width=True)
        st.plotly_chart(fig2, use_container_width=True)
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.warning("No hay datos disponibles para graficar.")

# =============================
# 🔹 TAB 3: Termómetro y Humedad
# =============================
with tab3:
    st.subheader("🌡️ Temperatura y Humedad ambiente")
    df_temp = obtener_datos(resultados=1)

    if not df_temp.empty:
        temperatura = df_temp["field7"].iloc[-1]
        humedad = df_temp["field6"].iloc[-1]

        c1, c2 = st.columns(2)

        with c1:
            fig_temp = go.Figure(go.Indicator(
                mode="gauge+number",
                value=temperatura,
                title={"text": "Temperatura (°C)"},
                gauge={"axis": {"range": [0, 50]}, "bar": {"color": "red"}}
            ))
            st.plotly_chart(fig_temp, use_container_width=True)

        with c2:
            fig_hum = go.Figure(go.Indicator(
                mode="gauge+number",
                value=humedad,
                title={"text": "Humedad (%)"},
                gauge={"axis": {"range": [0, 100]}, "bar": {"color": "blue"}}
            ))
            st.plotly_chart(fig_hum, use_container_width=True)
    else:
        st.warning("No hay datos de temperatura ni humedad disponibles.")

# =============================
# 🔹 TAB 4: Descargas y Displays
# =============================
with tab4:
    st.subheader("📥 Dosificador, Energía y Descarga CSV")

    # --- Displays de última lectura ---
    df_all = obtener_datos(resultados=1)
    if not df_all.empty:
        dosificador = df_all["field4"].iloc[-1]
        energia = df_all["field5"].iloc[-1]

        c1, c2 = st.columns(2)
        c1.metric("⚙️ Dosificador de cloro (golpes)", f"{dosificador:.0f}")
        c2.metric("⚡ Energía AC (kWh)", f"{energia:.2f}")

    # --- Filtro por rango de fechas ---
    st.subheader("📅 Descarga por rango de fechas")
    fecha_inicio = st.date_input("Fecha inicio")
    fecha_fin = st.date_input("Fecha fin")

    if fecha_inicio and fecha_fin:
        start_str = f"{fecha_inicio} 00:00:00"
        end_str = f"{fecha_fin} 23:59:59"

        df_filtrado = obtener_datos(start=start_str, end=end_str)

        if not df_filtrado.empty:
            st.success(f"✅ {len(df_filtrado)} registros entre {fecha_inicio} y {fecha_fin}")

            st.dataframe(df_filtrado)

            csv = df_filtrado.to_csv(index=False).encode("utf-8")
            st.download_button(
                label=f"⬇️ Descargar CSV ({fecha_inicio}_a_{fecha_fin})",
                data=csv,
                file_name=f"acueducto_{fecha_inicio}_a_{fecha_fin}.csv",
                mime="text/csv"
            )
        else:
            st.warning("⚠️ No hay registros en el rango seleccionado.")


