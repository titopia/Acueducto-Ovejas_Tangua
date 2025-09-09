import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import pytz
from datetime import datetime, timedelta

# =============================
# 🔹 Configuración general
# =============================
st.set_page_config(page_title="Tanque 3D", layout="wide")
st.sidebar.markdown("## ⚙️ Configuración")
intervalo = st.sidebar.slider("Intervalo de actualización (segundos)", 10, 120, 30)

CHANNEL_ID = "3031360"
READ_API_KEY = st.secrets.get("READ_API_KEY", "")
VOLUMEN_MAX = 80.0   # m³
TIEMPO_MAX_SIN_DATOS = 300  # 5 minutos

# 🔹 Configuración Telegram
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

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
if "ultima_alarma" not in st.session_state:
    st.session_state.ultima_alarma = None

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
        df["created_at"] = pd.to_datetime(df["created_at"])
        df["altura"] = pd.to_numeric(df["field1"], errors="coerce")
        df["caudal"] = pd.to_numeric(df["field2"], errors="coerce")
        df["volumen"] = pd.to_numeric(df["field3"], errors="coerce")
        df["humedad"] = pd.to_numeric(df["field6"], errors="coerce")
        df["temperatura"] = pd.to_numeric(df["field7"], errors="coerce")
        df["cloro"] = pd.to_numeric(df["field4"], errors="coerce")
        df["energia"] = pd.to_numeric(df["field5"], errors="coerce")
        return df.dropna()
    except Exception as e:
        st.error(f"Error obteniendo datos: {e}")
        return pd.DataFrame()

# =============================
# 🔹 Notificación a Telegram
# =============================
def enviar_telegram(mensaje: str):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
        try:
            requests.post(url, data=payload, timeout=5)
        except Exception as e:
            st.error(f"Error enviando alerta a Telegram: {e}")

# =============================
# 🔹 Verificación de datos recientes
# =============================
def verificar_datos_recientes(df):
    if df.empty:
        return "❌ Sin datos", "red"

    ultima_fecha = df["created_at"].max()
    ahora = datetime.utcnow().replace(tzinfo=pytz.UTC)
    delta = (ahora - ultima_fecha).total_seconds()

    if delta > TIEMPO_MAX_SIN_DATOS:
        # Enviar alerta solo si no se ha enviado antes
        if not st.session_state.ultima_alarma:
            mensaje = f"🚨 ALERTA: No se reciben datos del acueducto desde hace más de 5 minutos.\nÚltima actualización: {ultima_fecha}"
            enviar_telegram(mensaje)
            st.session_state.ultima_alarma = datetime.utcnow()
        return "⚠️ Sin actualización (>5 min)", "orange"

    # Resetear alarma si vuelven los datos
    st.session_state.ultima_alarma = None
    return "✅ Conectado", "green"

# =============================
# 🔹 Encabezado con logos y estado
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

# Estado general
df_estado = obtener_datos(resultados=1)
estado, color = verificar_datos_recientes(df_estado)

# Zona horaria Colombia
zona_colombia = pytz.timezone("America/Bogota")
if not df_estado.empty:
    ultima_fecha = (
        df_estado["created_at"].max()
        .tz_localize("UTC")
        .astimezone(zona_colombia)
        .strftime("%Y-%m-%d %H:%M:%S")
    )
else:
    ultima_fecha = "Sin datos"

st.markdown(
    f"""
    <h3 style='text-align:center; color:{color};'>
        📡 Estado del sistema: {estado}
    </h3>
    <p style='text-align:center; font-size:16px; color:gray;'>
        ⏱️ Última actualización: {ultima_fecha} (hora Colombia)
    </p>
    """,
    unsafe_allow_html=True
)

# =============================
# 🔹 Pestañas (tanque, gráficas, clima, descarga)
# =============================
# (Aquí mantienes el mismo contenido que ya tienes en las pestañas anteriores)
