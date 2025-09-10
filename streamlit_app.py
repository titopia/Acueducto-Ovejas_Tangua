import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import pytz

# -----------------------------
# Config
# -----------------------------
st.set_page_config(page_title="Tanque 3D - Tangua", layout="wide")

CHANNEL_ID = "3031360"
READ_API_KEY = st.secrets.get("READ_API_KEY", "")   # si está vacío se asume canal público
VOLUMEN_MAX = 80.0  # m³

# Intervalo controlado desde sidebar (una sola definición)
intervalo = st.sidebar.slider("Intervalo de actualización (segundos)", 30, 600, 60, step=10)

# -----------------------------
# Auto-refresh inyectado con components.html
# (algunas plataformas bloquean scripts; si no funciona, usa el botón '🔄 Actualizar ahora')
# -----------------------------
components.html(
    f"""
    <script>
      // recarga la página después de intervalo segundos
      setTimeout(function(){{ window.location.reload(); }}, {int(intervalo)*1000});
    </script>
    """,
    height=0,
)

# Botón manual por si el JS queda bloqueado
if st.sidebar.button("🔄 Actualizar ahora"):
    st.rerun()

# -----------------------------
# Función para obtener datos (soporta start/end o results)
# -----------------------------
def obtener_datos(resultados=1000, start=None, end=None):
    base = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json"
    params = {}
    if READ_API_KEY:
        params["api_key"] = READ_API_KEY
    if start and end:
        params["start"] = start
        params["end"] = end
    else:
        params["results"] = resultados

    try:
        r = requests.get(base, params=params, timeout=12)
        r.raise_for_status()
        data = r.json()
        feeds = data.get("feeds", [])
        if not feeds:
            return pd.DataFrame()
        df = pd.DataFrame(feeds)

        # created_at -> tz-aware UTC, luego convertimos a Colombia
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
        df["created_at"] = df["created_at"].dt.tz_convert("America/Bogota")

        # convertir posibles fields 1..8 a numéricos
        fields = []
        for i in range(1, 9):
            col = f"field{i}"
            fields.append(col)
            df[col] = pd.to_numeric(df.get(col), errors="coerce")

        # devolver filas donde al menos un field tenga dato
        return df.dropna(how="all", subset=fields)
    except Exception as e:
        st.error(f"Error obteniendo datos: {e}")
        return pd.DataFrame()

# -----------------------------
# Descargar UNA vez y compartir entre pestañas
# -----------------------------
df_all = obtener_datos(resultados=2000)
df_last = df_all.tail(1) if not df_all.empty else pd.DataFrame()

# -----------------------------
# Cabecera (solo un st.markdown para el header)
# -----------------------------
col1, col2, col3 = st.columns([1, 3, 1])
with col1:
    st.image("umariana.png", width=160)
with col2:
    st.markdown(
        "<h2 style='text-align:center; color:#004080; margin:0;'>🌊 Monitoreo Acueducto Tambor los Ajos</h2>"
        "<p style='text-align:center; margin:0;'>Ingeniería Mecatrónica - Universidad Mariana</p>"
        "<p style='text-align:center; margin:0;'>Autores: Titopia</p>",
        unsafe_allow_html=True,
    )
with col3:
    st.image("grupo_social.png", width=160)

st.write("")  # separación ligera

# -----------------------------
# Pestañas
# -----------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "🌀 Tanque 3D (Volumen %)",
    "📈 Gráficas históricas",
    "🌡️ Temp & Humedad",
    "📥 Descargas"
])

# -----------------------------
# TAB 1 - Tanque 3D (último dato)
# -----------------------------
with tab1:
    st.subheader("Tanque (último dato recibido)")

    if not df_last.empty:
        # leer campos (field3 = volumen (m³), field1 = altura (m), field2 = caudal)
        volumen = float(df_last["field3"].iloc[-1]) if "field3" in df_last else 0.0
        altura = float(df_last["field1"].iloc[-1]) if "field1" in df_last else 0.0
        caudal = float(df_last["field2"].iloc[-1]) if "field2" in df_last else 0.0
        ts = df_last["created_at"].iloc[-1]
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
    else:
        volumen = altura = caudal = 0.0
        ts_str = "Sin datos"

    # normalizar a 0..1 y escalar visual % (0..100)
    nivel = max(0.0, min(1.0, volumen / VOLUMEN_MAX))
    nivel_pct = nivel * 100

    # cilindro 3D simple (como antes)
    ALTURA_ESCALA = 100
    altura_agua = nivel * ALTURA_ESCALA
    theta = np.linspace(0, 2*np.pi, 50)
    x, y = np.cos(theta), np.sin(theta)
    z_tanque = np.linspace(0, ALTURA_ESCALA, 2)
    x_tanque, z1 = np.meshgrid(x, z_tanque)
    y_tanque, z2 = np.meshgrid(y, z_tanque)
    z_agua = np.linspace(0, altura_agua, 2)
    x_agua, z3 = np.meshgrid(x, z_agua)
    y_agua, z4 = np.meshgrid(y, z_agua)

    tanque_color = "Reds" if nivel <= 0.3 else "Greens"
    tanque_opacidad = 0.5 if nivel <= 0.3 else 0.3

    fig = go.Figure()
    fig.add_surface(x=x_tanque, y=y_tanque, z=z1, showscale=False,
                    opacity=tanque_opacidad, colorscale=tanque_color)
    if volumen > 0:
        fig.add_surface(x=x_agua, y=y_agua, z=z3, showscale=False,
                        opacity=0.6, colorscale="Blues")
    fig.update_layout(
        plot_bgcolor='rgb(0, 0, 0)',
        paper_bgcolor='#6e6a6a',
        scene=dict(xaxis=dict(visible=False), yaxis=dict(visible=False),
                   zaxis=dict(range=[0, ALTURA_ESCALA], title="Volumen (%)")),
        margin=dict(l=0, r=0, t=0, b=0), height=480
    )
    st.plotly_chart(fig, use_container_width=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Nivel (%)", f"{nivel_pct:.1f}%")
    c2.metric("Volumen (m³)", f"{volumen:.2f} / {VOLUMEN_MAX:.0f}")
    c3.metric("Altura (m)", f"{altura:.2f}")
    c4.metric("Caudal (L/min)", f"{caudal:.2f}")

    st.caption(f"Último dato recibido (hora Colombia): {ts_str}")

# -----------------------------
# TAB 2 - Gráficas históricas (últimos N registros)
# -----------------------------
with tab2:
    st.subheader("Gráficas (últimos 50 registros)")
    if df_all.empty:
        st.warning("No hay datos históricos para graficar.")
    else:
        window = 50
        df_plot = df_all.tail(window).copy()
        # convertir columnas a numéricas si no lo están
        for col in ["field1", "field2", "field3"]:
            if col in df_plot.columns:
                df_plot[col] = pd.to_numeric(df_plot[col], errors="coerce")
        try:
            fig1 = px.line(df_plot, x="created_at", y="field3", markers=True, title="Volumen (m³)")
            fig2 = px.line(df_plot, x="created_at", y="field1", markers=True, title="Altura (m)")
            fig3 = px.line(df_plot, x="created_at", y="field2", markers=True, title="Caudal (L/min)")
            st.plotly_chart(fig1, use_container_width=True)
            st.plotly_chart(fig2, use_container_width=True)
            st.plotly_chart(fig3, use_container_width=True)
        except Exception as e:
            st.error(f"Error al graficar: {e}")

# -----------------------------
# TAB 3 - Temperatura y Humedad (último dato)
# -----------------------------
with tab3:
    st.subheader("Temperatura y Humedad (último dato)")
    if df_last.empty:
        st.warning("No hay datos de temperatura/humedad.")
    else:
        temp = float(df_last["field7"].iloc[-1]) if "field7" in df_last else np.nan
        hum = float(df_last["field6"].iloc[-1]) if "field6" in df_last else np.nan
        c1, c2 = st.columns(2)
        c1.metric("Temperatura (°C)", f"{temp:.1f}" if not np.isnan(temp) else "N/D")
        c2.metric("Humedad (%)", f"{hum:.1f}" if not np.isnan(hum) else "N/D")
        ts = df_last["created_at"].iloc[-1]
        st.caption(f"Última muestra: {ts.strftime('%Y-%m-%d %H:%M:%S')}")

# -----------------------------
# TAB 4 - Descargas (rango / todos los fields)
# -----------------------------
with tab4:
    st.subheader("Descargar datos por rango (todos los fields)")

    if df_all.empty:
        st.warning("No hay datos históricos disponibles para descargar.")
    else:
        min_fecha = df_all["created_at"].dt.date.min()
        max_fecha = df_all["created_at"].dt.date.max()
        fecha_inicio, fecha_fin = st.date_input("Rango de fechas", [min_fecha, max_fecha])

        if fecha_inicio > fecha_fin:
            st.error("Fecha inicio no puede ser mayor a fecha fin.")
        else:
            # pedir directamente a ThingSpeak por rango (más preciso para grandes históricos)
            start_str = f"{fecha_inicio} 00:00:00"
            end_str = f"{fecha_fin} 23:59:59"
            df_rango = obtener_datos(start=start_str, end=end_str)

            if df_rango.empty:
                st.warning("No hay registros en ese rango.")
            else:
                # mantener todas las columnas que vienen (created_at + field1..field8)
                st.success(f"{len(df_rango)} registros entre {fecha_inicio} y {fecha_fin}")
                st.dataframe(df_rango)
                csv = df_rango.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Descargar CSV", csv, file_name=f"datos_{fecha_inicio}_a_{fecha_fin}.csv")

# -----------------------------
# Nota: si el script inyectado no recarga (CMS/hosting lo bloquea), usa el botón '🔄 Actualizar ahora'
# -----------------------------








