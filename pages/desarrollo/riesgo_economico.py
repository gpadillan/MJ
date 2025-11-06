import streamlit as st
import pandas as pd
import plotly.express as px
import re
import unicodedata

# ===== Helpers de normalización =====
NBSP = "\u00A0"

def _norm_text(x: object, upper: bool = True, deaccent: bool = True) -> str:
    if pd.isna(x):
        s = ""
    else:
        s = str(x).replace(NBSP, " ")
    s = " ".join(s.strip().split())
    if deaccent:
        s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    if upper:
        s = s.upper()
    return s

def normalizar_booleano(valor):
    if pd.isna(valor):
        return False
    return str(valor).strip().lower() in ["true", "1", "1.0", "sí", "si", "verdadero", "x"]

def limpiar_riesgo(valor) -> float:
    if isinstance(valor, (int, float)):
        return float(valor)
    if pd.isna(valor):
        return 0.0
    v = re.sub(r"[^\d,\.]", "", str(valor))
    v = v.replace(".", "").replace(",", ".")
    try:
        return float(v)
    except Exception:
        return 0.0

def convertir_fecha_excel(valor):
    try:
        if pd.isna(valor):
            return pd.NaT
        if isinstance(valor, (int, float)):
            return pd.to_datetime("1899-12-30") + pd.to_timedelta(int(valor), unit="D")
        return pd.to_datetime(valor, errors="coerce", dayfirst=True)
    except:
        return pd.NaT

def render(df: pd.DataFrame):
    st.title("💰 Riesgo Económico")

    # 🔄 Botón para recargar / limpiar caché
    if st.button("🔄 Recargar / limpiar caché"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("Caché limpiada. Datos recargados.")

    # -------- Normalización de encabezados (soporta acentos/alias) --------
    df.columns = (
        df.columns.astype(str)
        .str.replace(NBSP, " ")
        .str.strip()
        .str.upper()
    )
    # Aliases más frecuentes
    ren = {
        "PRÁCTCAS/GE": "PRÁCTICAS/GE",   # acento + falta de i
        "PRACTICAS/GE": "PRÁCTICAS/GE",  # sin acento
        "PRACTCAS/GE": "PRÁCTICAS/GE",   # tecleo "PRACTCAS"
        "CONSECUCION GE": "CONSECUCIÓN GE",
        "DEVOLUCION GE": "DEVOLUCIÓN GE",
        "INAPLICACION GE": "INAPLICACIÓN GE",
    }
    df = df.rename(columns={k: v for k, v in ren.items() if k in df.columns})

    columnas_requeridas = [
        "NOMBRE", "APELLIDOS", "PRÁCTICAS/GE", "CONSULTOR EIP",
        "CONSECUCIÓN GE", "DEVOLUCIÓN GE", "INAPLICACIÓN GE",
        "FIN CONV", "RIESGO ECONÓMICO", "EJECUCIÓN GARANTÍA", "AREA", "FECHA CIERRE"
    ]
    faltan = [c for c in columnas_requeridas if c not in df.columns]
    if faltan:
        st.error("❌ Faltan columnas: " + ", ".join(faltan))
        return

    # -------- Limpieza básica de texto --------
    for c in ["AREA", "CONSULTOR EIP", "PRÁCTICAS/GE"]:
        df[c] = df[c].map(lambda x: _norm_text(x, upper=True, deaccent=True))

    # -------- Fechas --------
    df["FIN CONV"] = pd.to_datetime(df["FIN CONV"], errors="coerce", dayfirst=True)
    df["EJECUCIÓN GARANTÍA"] = pd.to_datetime(df["EJECUCIÓN GARANTÍA"], errors="coerce", dayfirst=True)
    df["FECHA CIERRE"] = df["FECHA CIERRE"].apply(convertir_fecha_excel)

    hoy = pd.Timestamp.now().normalize()
    df["FECHA_RIESGO"] = df["FIN CONV"] + pd.DateOffset(months=3)

    # -------- Filtrado de alumnos en riesgo --------
    # (estados vacíos o falsos) + es GE + FIN CONV definido + fecha de riesgo vencida
    def _is_false_or_blank(s):
        if pd.isna(s):
            return True
        t = str(s).strip().lower()
        return t in ("", "nan", "false", "0", "no")

    mask_activos = (
        df["CONSECUCIÓN GE"].map(_is_false_or_blank) &
        df["DEVOLUCIÓN GE"].map(_is_false_or_blank) &
        df["INAPLICACIÓN GE"].map(_is_false_or_blank)
    )

    ge_col = df["PRÁCTICAS/GE"].fillna("")
    mask_ge = ge_col.eq("GE")

    df_filtrado = df[
        mask_activos &
        mask_ge &
        df["FIN CONV"].notna() &
        (df["FECHA_RIESGO"] <= hoy)
    ].copy()

    total_alumnos = len(df_filtrado)

    df_filtrado["RIESGO ECONÓMICO"] = df_filtrado["RIESGO ECONÓMICO"].map(limpiar_riesgo)
    suma_riesgo = df_filtrado["RIESGO ECONÓMICO"].sum()
    suma_riesgo_str = f"{suma_riesgo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"

    total_ejecucion_pasada = df_filtrado[
        df_filtrado["EJECUCIÓN GARANTÍA"].notna() & (df_filtrado["EJECUCIÓN GARANTÍA"] < hoy)
    ].shape[0]

    # 🔴 DEVOLUCIÓN GE
    df["DEVOLUCIÓN GE"] = df["DEVOLUCIÓN GE"].apply(normalizar_booleano)
    df_devolucion = df[df["DEVOLUCIÓN GE"] == True].copy()
    df_devolucion["RIESGO ECONÓMICO"] = df_devolucion["RIESGO ECONÓMICO"].map(limpiar_riesgo)

    total_devoluciones = df_devolucion.shape[0]
    total_riesgo_devolucion = df_devolucion["RIESGO ECONÓMICO"].sum()
    riesgo_devolucion_str = f"{total_riesgo_devolucion:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"

    # -------- KPIs --------
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📌 ALUMNO RIESGO TRIM", total_alumnos)
    col2.metric("💰 RIESGO ECONÓMICO", suma_riesgo_str)
    col3.metric("⏳ VENCIDA GE", total_ejecucion_pasada)
    col4.markdown(
        f"""
        <div style='text-align:center; padding-top: 12px'>
            <div style='font-size:1.1em;'>🔴 DEVOLUCIÓN GE</div>
            <div style='font-size:1.9em'>{total_devoluciones} <span style='font-size:0.75em; color:gray;'>({riesgo_devolucion_str})</span></div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    # -------- Distribución por consultor --------
    if "CONSULTOR EIP" in df_filtrado.columns:
        conteo_consultores = (
            df_filtrado["CONSULTOR EIP"]
            .replace({"NO ENCONTRADO": pd.NA})
            .dropna()
            .value_counts()
            .reset_index()
        )
        conteo_consultores.columns = ["CONSULTOR", "ALUMNOS EN RIESGO"]

        st.subheader("🔄 Distribución de Alumnado en RIESGO por Consultor")
        if not conteo_consultores.empty:
            fig = px.pie(
                conteo_consultores,
                names="CONSULTOR",
                values="ALUMNOS EN RIESGO",
                hole=0.5
            )
            fig.update_traces(textinfo="label+value")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay alumnos en riesgo para representar por consultor.")

        # -------- Detalle alumnos en riesgo --------
        st.markdown("### 📋 Detalle de alumnos en riesgo")
        columnas_tabla = ["NOMBRE", "APELLIDOS", "CONSULTOR EIP", "AREA", "RIESGO ECONÓMICO", "FECHA CIERRE"]
        df_resultado_vista = df_filtrado[columnas_tabla].copy()
        df_resultado_vista["RIESGO ECONÓMICO"] = df_resultado_vista["RIESGO ECONÓMICO"].apply(
            lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
        )
        st.dataframe(df_resultado_vista, use_container_width=True)

        # -------- Detalle devoluciones --------
        st.markdown("### 🔴 Detalle de alumnos con DEVOLUCIÓN GE")
        columnas_devolucion = ["NOMBRE", "APELLIDOS", "CONSULTOR EIP", "AREA", "RIESGO ECONÓMICO", "FECHA CIERRE"]
        df_devolucion_vista = df_devolucion[columnas_devolucion].copy()
        df_devolucion_vista["RIESGO ECONÓMICO"] = df_devolucion_vista["RIESGO ECONÓMICO"].apply(
            lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
        )
        st.dataframe(df_devolucion_vista, use_container_width=True)

    else:
        st.warning("⚠️ La columna 'CONSULTOR EIP' no está disponible en los datos.")
