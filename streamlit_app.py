# streamlit_app.py
import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import time

# --- Config ---
CHANNEL_ID = "3031360"
READ_API_KEY = st.secrets.get("READ_API_KEY", "")  # secreto en Streamlit Cloud si es privado

ALTURA_MIN, ALTURA_MAX = 0.0, 2.53   # m
VOLUMEN_MIN, VOLUMEN_MAX = 0.0, 80.0 # m³
ANCHO, ALTO = 2, 4

st.set_page_config(page_title="Monitoreo Tanque", layout="wide")
st.title("🌊 Monitoreo de Tanque (ThingSpeak)")

# Dataframe en sesión para histórico
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["timestamp", "altura_m", "volumen_m3", "field2"])

# Función que obtiene la última lectura
def obtener_datos():
    url = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json?api_key={READ_API_KEY}&results=1"
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()
        feeds = data.get("feeds", [])
        if feeds:
            f = feeds[0]
            altura = float(f.get("field1") or ALTURA_MIN)
            valor2 = float(f.get("field2") or 0.0)
            volumen = float(f.get("field3") or VOLUMEN_MIN)
        else:
            altura, valor2, volumen = ALTURA_MIN, 0.0, VOLUMEN_MIN
    except Exception as e:
        st.error(f"Error consultando ThingSpeak: {e}")
        altura, valor2, volumen = ALTURA_MIN, 0.0, VOLUMEN_MIN

    nivel = (volumen - VOLUMEN_MIN) / (VOLUMEN_MAX - VOLUMEN_MIN)
    nivel = max(0.0, min(1.0, nivel))
    return altura, valor2, volumen, nivel

# Obtener lectura actual y guardar en histórico
altura, valor2, volumen, nivel = obtener_datos()
ts = time.strftime("%Y-%m-%d %H:%M:%S")
st.session_state.df.loc[len(st.session_state.df)] = [ts, altura, volumen, valor2]

# Layout: 2 columnas
col1, col2 = st.columns([1, 2])

with col1:
    # Dibujo del tanque
    fig, ax = plt.subplots(figsize=(3, 5))
    tanque = patches.Rectangle((0, 0), ANCHO, ALTO, fill=False, linewidth=2)
    ax.add_patch(tanque)
    agua = patches.Rectangle((0, 0), ANCHO, ALTO * nivel, fill=True, alpha=0.6)
    ax.add_patch(agua)

    # Graduaciones (volumen m³ y altura m)
    num_div = 8
    for i in range(num_div + 1):
        vol = i * (VOLUMEN_MAX / num_div)
        y = (vol / VOLUMEN_MAX) * ALTO
        alt = (vol / VOLUMEN_MAX) * ALTURA_MAX
        ax.hlines(y, -0.4, 0, colors="black", linewidth=1)
        ax.text(-0.5, y, f"{vol:.0f} m³", va="center", ha="right", fontsize=8)
        ax.text(-1.2, y, f"{alt:.2f} m", va="center", ha="right", fontsize=8, color="gray")

    ax.set_xlim(-2, ANCHO + 2)
    ax.set_ylim(0, ALTO * 1.05)
    ax.axis("off")
    ax.set_title("Tanque (nivel por volumen)")

    st.pyplot(fig)
    st.metric("Nivel (%)", f"{nivel*100:.1f}%")
    st.metric("Altura (m)", f"{altura:.2f} m")
    st.metric("Volumen (m³)", f"{volumen:.2f} m³")
    st.metric("Field2", f"{valor2:.2f}")

with col2:
    df_show = st.session_state.df.copy()
    df_show.index = df_show["timestamp"]

    st.subheader("📈 Histórico por variable")

    # Gráfico Altura
    st.line_chart(df_show[["altura_m"]], height=200)

    # Gráfico Volumen
    st.line_chart(df_show[["volumen_m3"]], height=200)

    # Descargar CSV
    csv = st.session_state.df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Descargar histórico (CSV)", csv, "historico_tanque.csv", "text/csv")

st.caption("La app consulta ThingSpeak cada vez que se recarga o se actualiza automáticamente si usas streamlit-autorefresh.")
