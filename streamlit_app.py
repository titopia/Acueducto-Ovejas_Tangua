import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

# =============================
# 🔐 Credenciales Telegram
# =============================
TELEGRAM_BOT_TOKEN = "8433361405:AAGKl5s6zSYmzUArzbGFFAIowICKp1hlY6Y"
TELEGRAM_CHAT_ID = "8433361405"  # tu chat ID

# =============================
# ⚙️ Configuración
# =============================
CHANNEL_ID = "2569089"
READ_API_KEY = "DLU1YX0VYQ2R5C65"
st.set_page_config(page_title="Acueducto Tangua", layout="wide")

# =============================
# 📌 Estado de sesión
# =============================
if "last_data_time" not in st.session_state:
    st.session_state["last_data_time"] = datetime.now()
if "alert_sent" not in st.session_state:
    st.session_state["alert_sent"] = False

# =============================
# 📡 Obtener datos de ThingSpeak
# =============================
def obtener_datos(resultados=1000):
    url = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json?api_key={READ_API_KEY}&results={resultados}"
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()
        feeds = data.get("feeds", [])
        if not feeds:
            return pd.DataFrame()

        df = pd.DataFrame(feeds)
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

        # Normalización de zona horaria
        if df["created_at"].dt.tz is None:
            df["created_at"] = df["created_at"].dt.tz_localize("UTC")
        else:
            df["created_at"] = df["created_at"].dt.tz_convert("UTC")

        df["created_at"] = df["created_at"].dt.tz_convert("America/Bogota")

        # Conversión de campos
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
# 🚨 Alerta Telegram
# =============================
def enviar_alerta(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    try:
        requests.post(url, data=payload, timeout=5)
    except Exception as e:
        st.warning(f"No se pudo enviar alerta a Telegram: {e}")

# =============================
# 📊 Interfaz con pestañas
# =============================
st.title("🌍 Monitoreo Acueducto Tangua - Colombia")

tabs = st.tabs(["📦 Tanque 3D", "🌡️ Temp & Humedad", "📂 Descargar CSV"])

# =============================
# 📦 Tanque 3D
# =============================
with tabs[0]:
    st.subheader("Visualización 3D del Tanque")

    df = obtener_datos(200)
    if not df.empty:
        altura = df["altura"].iloc[-1]
        volumen = df["volumen"].iloc[-1]
        fecha = df["created_at"].iloc[-1]

        # Guardar última actualización
        st.session_state["last_data_time"] = datetime.now()
        st.session_state["alert_sent"] = False

        fig = go.Figure(data=[
            go.Mesh3d(
                x=[0, 1, 1, 0, 0, 1, 1, 0],
                y=[0, 0, 1, 1, 0, 0, 1, 1],
                z=[0, 0, 0, 0, 1, 1, 1, 1],
                color='lightblue',
                opacity=0.50
            )
        ])

        fig.update_layout(
            scene=dict(
                zaxis=dict(
                    title="Altura (m)",
                    range=[0, 5],
                    backgroundcolor="black",
                    color="white",
                    gridcolor="gray"
                )
            ),
            title=f"Nivel actual: {altura:.2f} m | Volumen: {volumen:.2f} L"
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Última actualización: {fecha}")
    else:
        st.warning("No se recibieron datos del tanque.")

# =============================
# 🌡️ Termómetro & Humedad
# =============================
with tabs[1]:
    st.subheader("Temperatura y Humedad Ambiente")

    df = obtener_datos(200)
    if not df.empty:
        temp = df["temperatura"].iloc[-1]
        hum = df["humedad"].iloc[-1]
        fecha = df["created_at"].iloc[-1]

        col1, col2 = st.columns(2)

        with col1:
            st.metric("🌡️ Temperatura (°C)", f"{temp:.2f}")
        with col2:
            st.metric("💧 Humedad (%)", f"{hum:.2f}")

        st.caption(f"Última actualización: {fecha}")
    else:
        st.warning("No se recibieron datos de sensores.")

# =============================
# 📂 Descarga CSV
# =============================
with tabs[2]:
    st.subheader("Descargar Datos en CSV")

    df = obtener_datos(2000)
    if not df.empty:
        fecha_min = df["created_at"].min().date()
        fecha_max = df["created_at"].max().date()

        rango = st.date_input("📅 Selecciona rango de fechas:",
                              [fecha_min, fecha_max])

        if len(rango) == 2:
            inicio, fin = rango
            mask = (df["created_at"].dt.date >= inicio) & (df["created_at"].dt.date <= fin)
            df_filtrado = df.loc[mask]

            csv = df_filtrado.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Descargar CSV", csv, "datos_filtrados.csv", "text/csv")
    else:
        st.warning("No hay datos para exportar.")

# =============================
# ⏰ Verificar si llegan datos
# =============================
if (datetime.now() - st.session_state["last_data_time"]) > timedelta(minutes=5):
    if not st.session_state["alert_sent"]:
        enviar_alerta("🚨 ALERTA: No se reciben datos en los últimos 5 minutos del Acueducto Tangua.")
        st.session_state["alert_sent"] = True
    st.error("⚠️ No se reciben datos desde hace más de 5 minutos.")
