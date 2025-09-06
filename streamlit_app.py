import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# =========================
# 🔹 Estilos para encabezado fijo
# =========================
st.markdown(
    """
    <style>
    .fixed-header {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        background-color: white;
        padding: 10px 0;
        z-index: 100;
        border-bottom: 3px solid #004080;
    }
    .fixed-header img {
        max-height: 80px;
    }
    .fixed-header h1 {
        margin: 0;
        font-size: 28px;
        color: #004080;
        text-align: center;
    }
    .stApp {
        margin-top: 140px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# 🔹 Encabezado
# =========================
st.markdown(
    """
    <div class="fixed-header">
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0 40px;">
            <img src="umariana.png" alt="UMariana" />
            <h1>🌊 Monitoreo de Tanque de Agua</h1>
            <img src="grupo_social.png" alt="Fundación Grupo Social" />
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# =========================
# 🔹 Obtener datos ThingSpeak
# =========================
def get_data():
    url = "https://api.thingspeak.com/channels/3031360/feeds.json?results=10"
    data = requests.get(url).json()
    feeds = data["feeds"]
    df = pd.DataFrame(feeds)
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["field1"] = pd.to_numeric(df["field1"], errors="coerce")  # altura
    df["field2"] = pd.to_numeric(df["field2"], errors="coerce")  # caudal
    df["field3"] = pd.to_numeric(df["field3"], errors="coerce")  # volumen
    return df

df = get_data()

# =========================
# 🔹 Tabs
# =========================
tab1, tab2, tab3, tab4 = st.tabs(["📏 Altura", "📦 Volumen", "💧 Caudal", "🛢️ Tanque 3D"])

# --- Altura ---
with tab1:
    st.subheader("Altura del Agua (m)")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["created_at"], y=df["field1"], mode="lines+markers", name="Altura"))
    fig.update_layout(yaxis_title="Altura (m)", xaxis_title="Tiempo")
    st.plotly_chart(fig, use_container_width=True)

# --- Volumen ---
with tab2:
    st.subheader("Volumen del Tanque (m³)")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["created_at"], y=df["field3"], mode="lines+markers", name="Volumen"))
    fig.update_layout(yaxis_title="Volumen (m³)", xaxis_title="Tiempo")
    st.plotly_chart(fig, use_container_width=True)

# --- Caudal ---
with tab3:
    st.subheader("Caudal (L/min)")
    st.metric("Último valor", f"{df['field2'].iloc[-1]:.2f} L/min")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["created_at"], y=df["field2"], name="Caudal"))
    fig.update_layout(yaxis_title="Caudal (L/min)", xaxis_title="Tiempo")
    st.plotly_chart(fig, use_container_width=True)

# --- Tanque 3D ---
with tab4:
    st.subheader("Nivel del Tanque (3D Realista)")

    volumen_actual = df["field3"].iloc[-1]
    porcentaje = (volumen_actual / 80) * 100  # escala 0-80 m³ → 0-100%

    # Altura del agua proporcional al tanque (altura máxima = 2)
    altura_agua = 2 * (porcentaje / 100)

    fig = go.Figure()

    # 🔹 Tanque (cilindro transparente)
    fig.add_trace(go.Mesh3d(
        x=[1,1,-1,-1,1,1,-1,-1],
        y=[1,-1,-1,1,1,-1,-1,1],
        z=[0,0,0,0,2,2,2,2],  # altura fija del tanque
        color="lightgrey",
        opacity=0.2,
        name="Tanque",
        alphahull=0
    ))

    # 🔹 Agua (relleno azul hasta la altura proporcional)
    fig.add_trace(go.Mesh3d(
        x=[1,1,-1,-1,1,1,-1,-1],
        y=[1,-1,-1,1,1,-1,-1,1],
        z=[0,0,0,0,altura_agua,altura_agua,altura_agua,altura_agua],
        color="blue",
        opacity=0.6,
        name="Agua",
        alphahull=0
    ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(range=[0,2], title="Altura"),
        ),
        title=f"Volumen actual: {volumen_actual:.2f} m³ ({porcentaje:.1f} %)"
    )

    st.plotly_chart(fig, use_container_width=True)
