import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# =============================
# 🔹 Configuración general
# =============================
st.set_page_config(page_title="Tanque 3D", layout="wide")
st.sidebar.markdown("## ⚙️ Configuración")
intervalo = st.sidebar.slider("Intervalo de actualización (segundos)", 10, 120, 30)

CHANNEL_ID = "3031360"   # ✅ Tu canal correcto
READ_API_KEY = st.secrets.get("READ_API_KEY", "")
VOLUMEN_MAX = 80.0   # m³

# Telegram
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

# Auto-refresh compatible
try:
    from streamlit.runtime.scriptrunner import st_autorefresh
    st_autorefresh(interval=intervalo*1000, key="autorefresh")
except Exception:
    try:
        st.experimental_autorefresh(interval=intervalo*1000, key="autorefresh")
    except Exception:
        st.info("⚠️ Tu versión de Streamlit no soporta autorefresh automático.")

st.title("🌊 Acueducto Ovejas Tangua \n Ingeniería Mecatrónica - Universidad Mariana")
st.write("**Autores: Titopia**")

# =============================
# 🔹 Estado inicial
# =============================
if "nivel_anterior" not in st.session_state:
    st.session_state.nivel_anterior = 0.0

if "last_alert" not in st.session_state:
    st.session_state.last_alert = None

# =============================
# 🔹 Función para enviar Telegram
# =============================
def enviar_telegram(mensaje: str):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
            requests.post(url, data=payload, timeout=5)
        except Exception as e:
            st.error(f"Error enviando alerta a Telegram: {e}")

# =============================
# 🔹 Función para obtener datos
# =============================
def obtener_datos(resultados=10):
    url = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json?api_key={READ_API_KEY}&results={resultados}"
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()
        feeds = data.get("feeds", [])
        if not feeds:
            return pd.DataFrame()
        df = pd.DataFrame(feeds)
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
        df["altura"] = pd.to_numeric(df["field1"], errors="coerce")
        df["caudal"] = pd.to_numeric(df["field2"], errors="coerce")
        df["volumen"] = pd.to_numeric(df["field3"], errors="coerce")
        df["humedad"] = pd.to_numeric(df["field6"], errors="coerce")
        df["temperatura"] = pd.to_numeric(df["field7"], errors="coerce")
        df["cloro"] = pd.to_numeric(df["field4"], errors="coerce")
        df["energia"] = pd.to_numeric(df["field5"], errors="coerce")
        return df.dropna(subset=["created_at"])
    except Exception as e:
        st.error(f"Error obteniendo datos: {e}")
        return pd.DataFrame()

# =============================
# 🔹 Función para verificar tiempo de última muestra
# =============================
def verificar_ultima_muestra(df):
    if df.empty:
        return
    fecha = df["created_at"].iloc[-1]

    # ✅ Asegurar que siempre tenga zona horaria
    if fecha.tzinfo is None:
        fecha = fecha.tz_localize("UTC")
    fecha = fecha.tz_convert("America/Bogota")

    ahora = datetime.now().astimezone(fecha.tzinfo)
    diff = ahora - fecha

    if diff > timedelta(minutes=5):
        st.warning(f"⚠️ No se reciben datos desde hace {diff.seconds//60} minutos")
        if st.session_state.last_alert is None or (ahora - st.session_state.last_alert) > timedelta(minutes=5):
            enviar_telegram(f"🚨 Alerta: No se reciben datos desde hace {diff.seconds//60} minutos en el acueducto Ovejas Tangua.")
            st.session_state.last_alert = ahora

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
    "🌡️ Ambiente",
    "⬇️ Descargas"
])

# -----------------------------
# Tab 1 - Tanque
# -----------------------------
with tab1:
    st.subheader("Tanque en 3D mostrando % de Volumen")
    df_ultimo = obtener_datos(resultados=1)

    if not df_ultimo.empty:
        verificar_ultima_muestra(df_ultimo)

        altura = df_ultimo["altura"].iloc[-1]
        caudal = df_ultimo["caudal"].iloc[-1]
        volumen = df_ultimo["volumen"].iloc[-1]

        fecha = df_ultimo["created_at"].iloc[-1]
        if fecha.tzinfo is None:
            fecha = fecha.tz_localize("UTC")
        ultima_fecha = fecha.tz_convert("America/Bogota")
    else:
        altura, caudal, volumen = 0.0, 0.0, 0.0
        ultima_fecha = "Sin datos"

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
    st.caption(f"⏰ Última muestra: {ultima_fecha}")

# -----------------------------
# Tab 2 - Gráficas históricas
# -----------------------------
with tab2:
    st.subheader("Últimos 10 valores")
    df_historico = obtener_datos(resultados=10)

    if not df_historico.empty:
        verificar_ultima_muestra(df_historico)

        fig1 = px.line(df_historico, x="created_at", y="volumen", markers=True, title="Volumen (m³)")
        fig2 = px.line(df_historico, x="created_at", y="altura", markers=True, title="Altura (m)")
        fig3 = px.line(df_historico, x="created_at", y="caudal", markers=True, title="Caudal (L/min)")

        st.plotly_chart(fig1, use_container_width=True)
        st.plotly_chart(fig2, use_container_width=True)
        st.plotly_chart(fig3, use_container_width=True)

        ultima_fecha = df_historico["created_at"].iloc[-1]
        if ultima_fecha.tzinfo is None:
            ultima_fecha = ultima_fecha.tz_localize("UTC")
        ultima_fecha = ultima_fecha.tz_convert("America/Bogota")
        st.caption(f"⏰ Última muestra: {ultima_fecha}")
    else:
        st.warning("No hay datos disponibles para graficar.")

# -----------------------------
# Tab 3 - Ambiente
# -----------------------------
with tab3:
    st.subheader("🌡️ Termómetro y Humedad")
    df_ultimo = obtener_datos(resultados=1)

    if not df_ultimo.empty:
        verificar_ultima_muestra(df_ultimo)

        temp = df_ultimo["temperatura"].iloc[-1]
        hum = df_ultimo["humedad"].iloc[-1]

        col1, col2 = st.columns(2)
        col1.metric("Temperatura (°C)", f"{temp:.1f}")
        col2.metric("Humedad (%)", f"{hum:.1f}")

        fecha = df_ultimo["created_at"].iloc[-1]
        if fecha.tzinfo is None:
            fecha = fecha.tz_localize("UTC")
        ultima_fecha = fecha.tz_convert("America/Bogota")
        st.caption(f"⏰ Última muestra: {ultima_fecha}")
    else:
        st.warning("No hay datos de ambiente disponibles.")

# -----------------------------
# Tab 4 - Descargas
# -----------------------------
with tab4:
    st.subheader("⬇️ Descargar datos históricos")
    df_historico = obtener_datos(resultados=200)

    if not df_historico.empty:
        verificar_ultima_muestra(df_historico)

        fecha_inicio = st.date_input("Fecha inicio", datetime.now().date() - timedelta(days=1))
        fecha_fin = st.date_input("Fecha fin", datetime.now().date())

        mask = (df_historico["created_at"].dt.date >= fecha_inicio) & (df_historico["created_at"].dt.date <= fecha_fin)
        df_filtrado = df_historico.loc[mask, ["created_at", "cloro", "energia"]]

        st.dataframe(df_filtrado)

        csv = df_filtrado.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Descargar CSV",
            data=csv,
            file_name=f"datos_{fecha_inicio}_{fecha_fin}.csv",
            mime="text/csv"
        )

        ultima_fecha = df_historico["created_at"].iloc[-1]
        if ultima_fecha.tzinfo is None:
            ultima_fecha = ultima_fecha.tz_localize("UTC")
        ultima_fecha = ultima_fecha.tz_convert("America/Bogota")
        st.caption(f"⏰ Última muestra: {ultima_fecha}")
    else:
        st.warning("No hay datos disponibles para descargar.")
