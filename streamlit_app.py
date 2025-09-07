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

intervalo = st.sidebar.slider("⏱ Intervalo de actualización (segundos)", 10, 120, 30)
estilo = st.sidebar.radio("🎨 Estilo del tanque", ["Realista (cielo azul)", "Técnico (blanco)"])

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
# 🔹 Pestañas
# =============================
tab1, tab2 = st.tabs(["🌀 Tanque 3D (Volumen %)", "📈 Gráficas históricas"])

with tab1:
    st.subheader("Tanque en 3D mostrando % de Volumen")

    df = obtener_datos(resultados=1)
    if not df.empty:
        altura = df["altura"].iloc[-1]
        caudal = df["caudal"].iloc[-1]
        volumen = df["volumen"].iloc[-1]
    else:
        altura, caudal, volumen = 0.0, 0.0, 0.0

    # Normalizar volumen (0 a 1)
    nivel_objetivo = max(0.0, min(1.0, volumen / VOLUMEN_MAX))
    niveles = np.linspace(st.session_state.nivel_anterior, nivel_objetivo, 20)
    st.session_state.nivel_anterior = nivel_objetivo
    nivel_suave = niveles[-1]

    # Escala del tanque en %
    ALTURA_ESCALA = 100
    altura_agua = nivel_suave * ALTURA_ESCALA

    # Geometría del tanque
    theta = np.linspace(0, 2*np.pi, 50)
    x, y = np.cos(theta), np.sin(theta)
    z_tanque = np.linspace(0, ALTURA_ESCALA, 2)
    x_tanque, z1 = np.meshgrid(x, z_tanque)
    y_tanque, z2 = np.meshgrid(y, z_tanque)
    z_agua = np.linspace(0, altura_agua, 2)
    x_agua, z3 = np.meshgrid(x, z_agua)
    y_agua, z4 = np.meshgrid(y, z_agua)

    # --- Gráfico 3D ---
    fig = go.Figure()
    fig.add_surface(x=x_tanque, y=y_tanque, z=z1, showscale=False, opacity=0.3, colorscale="Greys")
    fig.add_surface(x=x_agua, y=y_agua, z=z3, showscale=False, opacity=0.6, colorscale="Blues")

    # 🎨 Estilo del tanque
    if estilo == "Realista (cielo azul)":
        scene_config = dict(
            xaxis=dict(visible=False, backgroundcolor="skyblue", gridcolor="white"),
            yaxis=dict(visible=False, backgroundcolor="skyblue", gridcolor="white"),
            zaxis=dict(range=[0, ALTURA_ESCALA], title="Volumen (%)", backgroundcolor="skyblue", gridcolor="white", showbackground=True)
        )
        paper_bg = "skyblue"
    else:  # Técnico
        scene_config = dict(
            xaxis=dict(visible=False, backgroundcolor="white", gridcolor="lightgrey"),
            yaxis=dict(visible=False, backgroundcolor="white", gridcolor="lightgrey"),
            zaxis=dict(range=[0, ALTURA_ESCALA], title="Volumen (%)", backgroundcolor="white", gridcolor="lightgrey", showbackground=True)
        )
        paper_bg = "white"

    fig.update_layout(
       scene=scene_config,
        margin=dict(l=0, r=0, t=0, b=0),
        height=500,
        paper_bgcolor=paper_bg,
        plot_bgcolor=paper_bg,
        scene_camera=dict(eye=dict(x=1.5, y=1.5, z=1.2)),  # 📌 mueve la cámara
        scene=dict(
            zaxis=dict(
                range=[0, ALTURA_ESCALA],
                title="Volumen (%)",
                titlefont=dict(size=14, color="black"),
                tickfont=dict(size=12, color="black"),
                showgrid=True,
                gridcolor="black",
                zeroline=False
            )
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- Métricas ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Nivel (%)", f"{nivel_objetivo*100:.1f}%")
    c2.metric("Volumen (m³)", f"{volumen:.2f} / {VOLUMEN_MAX:.0f}")
    c3.metric("Altura (m)", f"{altura:.2f}")
    c4.metric("Caudal (L/min)", f"{caudal:.2f}")

with tab2:
    st.subheader("Últimos 10 valores")
    df_hist = obtener_datos(resultados=10)
    if not df_hist.empty:
        fig1 = px.line(df_hist, x="created_at", y="volumen", markers=True, title="Volumen (m³)")
        fig2 = px.line(df_hist, x="created_at", y="altura", markers=True, title="Altura (m)")
        fig3 = px.line(df_hist, x="created_at", y="caudal", markers=True, title="Caudal (L/min)")

        st.plotly_chart(fig1, use_container_width=True)
        st.plotly_chart(fig2, use_container_width=True)
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.warning("No hay datos disponibles para graficar.")
