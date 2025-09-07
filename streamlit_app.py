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
st.sidebar.markdown("## ⚙️ Configuración")
intervalo = st.sidebar.slider("Intervalo de actualización (segundos)", 10, 120, 30)

CHANNEL_ID = "3031360"
READ_API_KEY = st.secrets.get("READ_API_KEY", "")
VOLUMEN_MAX = 80.0   # m³

st.title("🌊 Acueducto Ovejas Tangua \n Ingeniería Mecatrónica - Universidad Mariana ")
st.write("**Autores: Titopia**")

# Estado inicial
if "nivel_anterior" not in st.session_state:
    st.session_state.nivel_anterior = 0.0

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
# 🔹 Contenedores para refresco
# =============================
tab1, tab2 = st.tabs(["🌀 Tanque 3D (Volumen %)", "📈 Gráficas históricas"])
contenedor_tab1 = tab1.empty()
contenedor_tab2 = tab2.empty()

# =============================
# 🔹 Loop de actualización
# =============================
def actualizar_datos():
    df_ultimo = obtener_datos(resultados=1)
    df_historico = obtener_datos(resultados=10)

    # --- Tanque 3D ---
    with contenedor_tab1.container():
        st.subheader("Tanque en 3D mostrando % de Volumen")

        if not df_ultimo.empty:
            altura = df_ultimo["altura"].iloc[-1]
            caudal = df_ultimo["caudal"].iloc[-1]
            volumen = df_ultimo["volumen"].iloc[-1]
        else:
            altura, caudal, volumen = 0.0, 0.0, 0.0

        nivel_objetivo = max(0.0, min(1.0, volumen / VOLUMEN_MAX))
        niveles = np.linspace(st.session_state.nivel_anterior, nivel_objetivo, 20)
        st.session_state.nivel_anterior = nivel_objetivo
        nivel_suave = niveles[-1]
        ALTURA_ESCALA = 100
        altura_agua = nivel_suave * ALTURA_ESCALA
