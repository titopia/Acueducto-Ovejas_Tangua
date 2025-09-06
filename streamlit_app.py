import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import time

# --- Configuración ---
CHANNEL_ID = "3031360"
READ_API_KEY = st.secrets.get("READ_API_KEY", "")  # Si el canal es privado, poner en secrets

# Rango de datos
ALTURA_MIN, ALTURA_MAX = 0.0, 2.53   # metros
VOLUMEN_MIN, VOLUMEN_MAX = 0.0, 80.0 # m³
ANCHO, ALTO = 2, 4                   # dimensiones tanque

st.set_page_config(page_title="Monitoreo Tanque", layout="wide")
st.title("🌊 Monitoreo de Tanque en Tiempo Real")

# DataFrame histórico en sesión
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["timestamp", "altura_m", "volumen_m3", "caudal_Lmin"])

# Función para obtener datos de ThingSpeak
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
            caudal = float(f.get("field2") or 0.0)
            volumen = float(f.get("field3") or VOLUMEN_MIN)
        else:
            altura, caudal, volumen = ALTURA_MIN, 0.0, VOLUMEN_MIN
    except Exception as e:
        st.error(f"Error consultando ThingSpeak: {e}")
        altura, caudal, volumen = ALTURA_MIN, 0.0, VOLUMEN_MIN

    # Normalizar volumen para tanque
    nivel = (volumen - VOLUMEN_MIN) / (VOLUMEN_MAX - VOLUMEN_MIN)
    nivel = max(0.0, min(1.0, nivel))
    return altura, caudal, volumen, nivel

# --- Obtener datos actuales ---
altura, caudal, volumen, nivel = obtener_datos()
ts = time.strftime("%Y-%m-%d %H:%M:%S")

# Guardar en histórico usando concat (para evitar error iloc)
nueva_fila = pd.DataFrame(
    [[ts, altura, volumen, caudal]],
    columns=["timestamp", "altura_m", "volumen_m3", "caudal_Lmin"]
)
st.session_state.df = pd.concat([st.session_state.df, nueva_fila], ignore_index=True)

# --- Layout ---
col1, col2 = st.columns([1, 2])

with col1:
    # Dibujo del tanque
    fig, ax = plt.subplots(figsize=(3, 5))
    tanque = patches.Rectangle((0, 0), ANCHO, ALTO, fill=False, linewidth=2)
    ax.add_patch(tanque)
    agua = patches.Rectangle((0, 0), ANCHO, ALTO * nivel, fill=True, alpha=0.6, color="skyblue")
    ax.add_patch(agua)

    # Graduaciones de volumen y altura
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

    # Displays de variables
    st.metric("Nivel (%)", f"{nivel*100:.1f}%")
    st.metric("Altura (m)", f"{altura:.2f} m")
    st.metric("Volumen (m³)", f"{volumen:.2f} m³")
    st.metric("Caudal (L/min)", f"{caudal:.2f}")

with col2:
    df_show = st.session_state.df.copy()
    df_show.index = df_show["timestamp"]

    st.subheader("📈 Histórico de Variables")

    # Gráfico de altura
    st.line_chart(df_show[["altura_m"]], height=200)

    # Gráfico de volumen
    st.line_chart(df_show[["volumen_m3"]], height=200)

    # Gráfico de caudal
    st.line_chart(df_show[["caudal_Lmin"]], height=200)

    # Botón para descargar CSV
    csv = st.session_state.df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Descargar histórico (CSV)", csv, "historico_tanque.csv", "text/csv")

st.caption("La app se actualiza al recargar. En Streamlit Cloud puedes usar `st_autorefresh` para actualizar cada X segundos.")
