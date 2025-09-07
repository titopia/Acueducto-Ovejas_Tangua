import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# =============================
# 🔹 Configuración general
# =============================
st.set_page_config(page_title="Tanque 3D", layout="wide")

# Intervalo fijo de actualización: 60 segundos
INTERVALO = 60  

CHANNEL_ID = "3031360"
READ_API_KEY = st.secrets.get("READ_API_KEY", "")
VOLUMEN_MAX = 80.0   # m³

# 🔄 Auto-refresh compatible
try:
    from streamlit.runtime.scriptrunner import st_autorefresh
    st_autorefresh(interval=INTERVALO*1000, key="autorefresh")
except Exception:
    try:
        st.experimental_autorefresh(interval=INTERVALO*1000, key="autorefresh")
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
def obtener_datos(resultados=100):
    url = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json?api_key={READ_API_KEY}&results={resultados}"
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()
        feeds = data.get("feeds", [])
        if not feeds:
            return pd.DataFrame()
        df = pd.DataFrame(feeds)
        df["created_at"] = pd.to_datetime(df["created_at"])
        df["altura"] = pd.to_numeric(df["field1"], errors="coerce")
        df["caudal"] = pd.to_numeric(df["field2"], errors="coerce")
        df["volumen"] = pd.to_numeric(df["field3"], errors="coerce")
        df["dosificador"] = pd.to_numeric(df["field4"], errors="coerce")
        df["energia"] = pd.to_numeric(df["field5"], errors="coerce")
        df["humedad"] = pd.to_numeric(df["field6"], errors="coerce")
        df["temperatura"] = pd.to_numeric(df["field7"], errors="coerce")
        return df.dropna()
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
    "🌡️ Ambiente (Temp & Humedad)",
    "📥 Descargas y Displays"
])

# =============================
# 🔹 TAB 1: Tanque 3D
# =============================
with tab1:
    st.subheader("Tanque en 3D mostrando % de Volumen")
    df_ultimo = obtener_datos(resultados=1)

    if not df_ultimo.empty:
        altura = df_ultimo["altura"].iloc[-1]
        caudal = df_ultimo["caudal"].iloc[-1]
        volumen = df_ultimo["volumen"].iloc[-1]
    else:
        altura, caudal, volumen = 0.0, 0.0, 0.0

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
    y_tanque, z2 = np.meshgrid(y, z_tanque)
    z_agua = np.linspace(0, altura_agua, 2)
    x_agua, z3 = np.meshgrid(x, z_agua)
    y_agua, z4 = np.meshgrid(y, z_agua)

    # --- Color dinámico del tanque según nivel ---
    if nivel_objetivo <= 0.3:  # ≤ 30 %
        tanque_color = "Reds"
        tanque_opacidad = 0.5
        st.error(f"⚠️ El tanque está en nivel crítico ({nivel_objetivo*100:.1f}%)")
    else:
        tanque_color = "Greys"
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

# =============================
# 🔹 TAB 2: Gráficas históricas
# =============================
with tab2:
    st.subheader("Últimos 10 valores")
    df_historico = obtener_datos(resultados=10)

    if not df_historico.empty:
        fig1 = px.line(df_historico, x="created_at", y="volumen", markers=True, title="Volumen (m³)")
        fig2 = px.line(df_historico, x="created_at", y="altura", markers=True, title="Altura (m)")
        fig3 = px.line(df_historico, x="created_at", y="caudal", markers=True, title="Caudal (L/min)")

        st.plotly_chart(fig1, use_container_width=True)
        st.plotly_chart(fig2, use_container_width=True)
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.warning("No hay datos disponibles para graficar.")

# =============================
# 🔹 TAB 3: Temperatura y Humedad
# =============================
with tab3:
    st.subheader("🌡️ Temperatura y Humedad ambiente")
    df_ambiente = obtener_datos(resultados=1)

    if not df_ambiente.empty:
        temp = df_ambiente["temperatura"].iloc[-1]
        hum = df_ambiente["humedad"].iloc[-1]

        col1, col2 = st.columns(2)
        with col1:
            fig_temp = go.Figure(go.Indicator(
                mode="gauge+number",
                value=temp,
                title={"text": "Temperatura (°C)"},
                gauge={
                    "axis": {"range": [0, 50]},
                    "bar": {"color": "red"},
                    "steps": [
                        {"range": [0, 15], "color": "lightblue"},
                        {"range": [15, 30], "color": "lightgreen"},
                        {"range": [30, 50], "color": "orange"}
                    ]
                }
            ))
            st.plotly_chart(fig_temp, use_container_width=True)

        with col2:
            fig_hum = go.Figure(go.Indicator(
                mode="gauge+number",
                value=hum,
                title={"text": "Humedad (%)"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "blue"},
                    "steps": [
                        {"range": [0, 30], "color": "lightyellow"},
                        {"range": [30, 70], "color": "lightgreen"},
                        {"range": [70, 100], "color": "lightblue"}
                    ]
                }
            ))
            st.plotly_chart(fig_hum, use_container_width=True)

        c1, c2 = st.columns(2)
        c1.metric("🌡️ Temp. actual (°C)", f"{temp:.1f}")
        c2.metric("💧 Humedad (%)", f"{hum:.1f}")
    else:
        st.warning("No hay datos de temperatura y humedad disponibles.")

# =============================
# 🔹 TAB 4: Descargas y Displays
# =============================
with tab4:
    st.subheader("📥 Dosificador y Energía + Descarga CSV")
    df_all = obtener_datos(resultados=200)

    if not df_all.empty:
        dosificador = df_all["dosificador"].iloc[-1]
        energia = df_all["energia"].iloc[-1]

        c1, c2 = st.columns(2)
        c1.metric("⚙️ Dosificador de cloro (golpes)", f"{dosificador:.0f}")
        c2.metric("⚡ Energía AC (kWh)", f"{energia:.2f}")

        # Botón para descargar CSV
        csv = df_all.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Descargar CSV completo",
            data=csv,
            file_name="acueducto_datos.csv",
            mime="text/csv"
        )
    else:
        st.warning("No hay datos disponibles para mostrar ni descargar.")
