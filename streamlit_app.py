import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timezone
import pytz
import time

# =========================
# 🔐 Credenciales Telegram
# =========================
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

# =========================
# 🎨 Estilos
# =========================
st.markdown(
    """
    <style>
        .stApp {
            background-color: #f0f8ff;
        }
        .encabezado {
            text-align: center;
            margin-bottom: 20px;
        }
        .encabezado img {
            max-width: 140px;
        }
        .titulo-proyecto {
            color: #004080;
            font-size: 28px;
            font-weight: bold;
        }
        .subtitulo {
            font-size: 18px;
            color: #444;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# 🏫 Encabezado institucional
# =========================
st.markdown(
    """
    <div class="encabezado">
        <img src="https://upload.wikimedia.org/wikipedia/commons/3/3f/Logo_Unimar.png" alt="Logo Universidad Mariana">
        <div class="titulo-proyecto">💧 Sistema de Monitoreo Acueducto Ovejas - Tangua</div>
        <div class="subtitulo">Universidad Mariana | Programa de Ingeniería Mecatrónica</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================
# 📡 Configuración canal ThingSpeak
# =========================
CHANNEL_ID = "3031360"
API_KEY = "DLU1YX0VYQ2R5C65"
BASE_URL = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json"

# =========================
# ⏳ Funciones
# =========================
def obtener_datos(resultados=200, start=None, end=None):
    try:
        params = {"api_key": API_KEY, "results": resultados}
        if start and end:
            params["start"] = start
            params["end"] = end
        r = requests.get(BASE_URL, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        feeds = data.get("feeds", [])
        if not feeds:
            return pd.DataFrame()

        df = pd.DataFrame(feeds)
        df["created_at"] = pd.to_datetime(df["created_at"])
        for i in range(1, 9):
            df[f"field{i}"] = pd.to_numeric(df.get(f"field{i}"), errors="coerce")
        return df
    except Exception as e:
        st.error(f"Error obteniendo datos: {e}")
        return pd.DataFrame()

def enviar_alerta_telegram(mensaje: str):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                params={"chat_id": TELEGRAM_CHAT_ID, "text": mensaje},
                timeout=10
            )
        except Exception as e:
            st.warning(f"Error enviando alerta a Telegram: {e}")

# =========================
# 🗂 Pestañas
# =========================
tab1, tab2, tab3, tab4 = st.tabs(["🌀 Tanque 3D", "🌡️ Sensores", "📈 Gráficos", "📥 Descargas"])

# =========================
# 🌀 TAB 1: Tanque 3D + Alarma
# =========================
with tab1:
    st.header("Nivel del tanque en 3D")

    df_ultimo = obtener_datos(resultados=1)

    if not df_ultimo.empty:
        # --- Verificar última fecha ---
        ultima_fecha = df_ultimo["created_at"].iloc[-1]
        bogota_tz = pytz.timezone("America/Bogota")
        if ultima_fecha.tzinfo is None:
            ultima_fecha = ultima_fecha.tz_localize("UTC").tz_convert(bogota_tz)
        ahora = datetime.now(timezone.utc).astimezone(bogota_tz)
        diferencia = (ahora - ultima_fecha).total_seconds() / 60

        if diferencia > 5:
            st.error(f"🚨 No llegan datos desde hace {diferencia:.1f} minutos (último: {ultima_fecha})")
            if "ultima_alarma" not in st.session_state or (ahora - st.session_state.ultima_alarma).total_seconds() > 300:
                enviar_alerta_telegram(f"🚨 ALERTA: No llegan datos desde hace {diferencia:.1f} minutos.\nÚltimo dato: {ultima_fecha}")
                st.session_state.ultima_alarma = ahora

        # --- Mostrar últimos datos ---
        st.success(f"✅ Último dato recibido: {ultima_fecha}")
        st.write(df_ultimo.tail())

# =========================
# 🌡️ TAB 2: Sensores
# =========================
with tab2:
    st.header("Sensores de Temperatura y Humedad")

    df = obtener_datos(resultados=10)
    if not df.empty:
        col1, col2 = st.columns(2)

        with col1:
            temperatura = df["field7"].iloc[-1]
            st.metric("🌡️ Temperatura (°C)", f"{temperatura:.1f}" if pd.notna(temperatura) else "N/D")

        with col2:
            humedad = df["field6"].iloc[-1]
            st.metric("💧 Humedad (%)", f"{humedad:.1f}" if pd.notna(humedad) else "N/D")

# =========================
# 📈 TAB 3: Gráficos
# =========================
with tab3:
    st.header("Gráficos de los sensores")
    df = obtener_datos(resultados=100)
    if not df.empty:
        st.line_chart(df.set_index("created_at")[["field1", "field2", "field3", "field4", "field5", "field6", "field7"]])

# =========================
# 📥 TAB 4: Descargas
# =========================
with tab4:
    st.header("Descargar datos")

    fecha_inicio = st.date_input

