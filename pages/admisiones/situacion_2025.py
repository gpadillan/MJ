import os 
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from responsive import get_screen_size

UPLOAD_FOLDER = "uploaded_admisiones"
EXCEL_FILE = os.path.join(UPLOAD_FOLDER, "matricula_programas_25.xlsx")


# ----------------- Helpers -----------------
def _parse_excel_serial_to_datetime(val):
    """
    Convierte un serial numérico de Excel a datetime (origen 1899-12-30).
    Si no es numérico, devuelve NaT.
    """
    try:
        if isinstance(val, str):
            v = val.strip().replace(",", ".")
            if v == "":
                return pd.NaT
            v = float(v)
        else:
            v = float(val)
        return pd.to_datetime(v, unit="D", origin="1899-12-30", errors="coerce")
    except Exception:
        return pd.NaT


def _to_year(series_like: pd.Series) -> pd.Series:
    """
    Devuelve el año robustamente:
    - Si ya es datetime -> extrae año.
    - Si es número (o str numérico) -> interpreta como serial Excel.
    - Si es texto -> parseo con dayfirst=True.
    """
    s = series_like

    if pd.api.types.is_datetime64_any_dtype(s):
        return pd.to_datetime(s, errors="coerce").dt.year

    dt_try = pd.to_datetime(s, errors="coerce", dayfirst=True)
    mask_nat = dt_try.isna()
    if mask_nat.any():
        dt_serial = s[mask_nat].apply(_parse_excel_serial_to_datetime)
        dt_try.loc[mask_nat] = dt_serial

    return dt_try.dt.year


def _fill_blank(s: pd.Series, blank_label="(En Blanco)"):
    out = s.astype(str).str.strip()
    out = out.replace(["", "nan", "NaN", "NONE", "None"], blank_label)
    return out.fillna(blank_label)


def _is_blank_series(s: pd.Series):
    """Detecta si el valor está en 'blanco' (sin tocar a '(En Blanco)')"""
    s2 = s.astype(str).str.strip()
    return s2.isin(["", "nan", "NaN", "NONE", "None"])


@st.cache_data(show_spinner=False)
def _read_excel_cached(path: str, mtime: float, sheet_name="Contactos") -> pd.DataFrame:
    """
    Lectura estable:
    - engine='openpyxl'
    - dtype=str para evitar inferencias diferentes entre entornos
    Cacheada por mtime del archivo.
    """
    return pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl", dtype=str)


# ----------------- APP -----------------
def app():
    width, height = get_screen_size()
    is_mobile = width <= 400

    traducciones_meses = {
        "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
        "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
        "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
    }
    now = datetime.now()
    mes_actual = traducciones_meses[now.strftime("%B")] + " " + now.strftime("%Y")

    st.markdown(f"<h1>Matrículas por Programa y Propietario - {mes_actual}</h1>", unsafe_allow_html=True)

    # Carga
    try:
        if not os.path.exists(EXCEL_FILE):
            raise FileNotFoundError(f"No existe el archivo: {EXCEL_FILE}")
        mtime = os.path.getmtime(EXCEL_FILE)
        df = _read_excel_cached(EXCEL_FILE, mtime, sheet_name="Contactos")
    except Exception as e:
        st.error(f"No se pudo cargar el archivo: {e}")
        return

    if "Programa" not in df.columns or "propietario" not in df.columns:
        st.error("Faltan columnas requeridas: 'Programa' o 'propietario'")
        return

    # Normalización
    df["Programa"] = _fill_blank(df["Programa"])
    df["propietario"] = _fill_blank(df["propietario"])

    # Clasificación de programas
    programa_mapping = {
        "Certificado oficial SAP S/4HANA Finance": "CERTIFICACIÓN SAP S/4HANA",
        "Consultoría SAP S4HANA Ventas": "CERTIFICACIÓN SAP S/4HANA",
        "Master en Auditoría de Protección de Datos, Gestión de Riesgos y Cyber Compliance": "MÁSTER DPO",
        "Máster Profesional en Auditoría de Protección de Datos, Gestión de Riesgos y Cyber Compliance": "MÁSTER DPO",
        "Máster en Dirección de Compliance & Protección de Datos": "MÁSTER DPO",
        "Master en Dirección de Ciberseguridad, Hacking Ético y Seguridad Ofensiva": "MÁSTER CIBERSEGURIDAD",
        "Máster en Dirección de Ciberseguridad, Hacking Ético y Seguridad Ofensiva": "MÁSTER CIBERSEGURIDAD",
        "Master en Gestión Eficiente de Energías Renovables": "MÁSTER EERR",
        "Máster en Gestión Eficiente de las Energías Renovables": "MÁSTER EERR",
        "Programa Movilidad California": "PROGRAMA CALIFORNIA",
        "Máster en RRHH: Dirección de Personas, Desarrollo de Talento y Gestión Laboral": "MÁSTER RRHH",
        "Master en RRHH, dirección de personas, desarrollo de talento y gestión laboral": "MÁSTER RRHH",
        "Máster en Inteligencia Artificial": "MÁSTER IA"
    }
    df["programa_categoria"] = df["Programa"].map(programa_mapping).fillna(df["Programa"])

    # Columna 'último contacto'
    col_ultimo = (
        "último contacto"
        if "último contacto" in df.columns
        else ("Último contacto" if "Último contacto" in df.columns else None)
    )
    if not col_ultimo:
        st.error("No se encontró la columna 'último contacto' / 'Último contacto'.")
        return

    # Año robusto
    df["_anio"] = _to_year(df[col_ultimo])

    # =========================
    # CONTROLES con visibilidad por rol
    # =========================
    def _is_current_user_admin() -> bool:
        # 1) Query param ?admin=1|true|yes
        try:
            qp = st.experimental_get_query_params()
            flag = str(qp.get("admin", ["0"])[0]).strip().lower()
            if flag in ("1", "true", "yes"):
                return True
        except Exception:
            pass
        # 2) Session state
        if st.session_state.get("is_admin", False):
            return True
        # 3) Secrets
        try:
            admins = set(st.secrets.get("APP_ADMINS", []))
            current_user = str(st.secrets.get("APP_CURRENT_USER", "")).strip()
            if current_user and current_user in admins:
                return True
        except Exception:
            pass
        return False

    is_admin = _is_current_user_admin()

    st.subheader("")
    if is_admin:
        left, right = st.columns(2)
        with left:
            modo_todos_anios = st.checkbox(
                "Contar TODOS los años (ignorar el filtro de año)",
                value=False,
                help="Si marcas esto, el total y el gráfico incluyen registros de todos los años."
            )
        with right:
            incluir_sin_fecha = st.checkbox(
                "Incluir filas sin 'último contacto'",
                value=True,
                help="Incluye registros con 'último contacto' en blanco o inválido."
            )
        incluir_programa_blanco = st.checkbox(
            "Incluir Programas en blanco",
            value=True,
            help="Si tu Excel cuenta los '(En Blanco)', márcalo."
        )
    else:
        # No admin: solo muestra 'Todos los años'; el resto siempre activo
        modo_todos_anios = st.checkbox(
            "Contar TODOS los años (ignorar el filtro de año)",
            value=False,
            help="Si marcas esto, el total y el gráfico incluyen registros de todos los años."
        )
        incluir_sin_fecha = True
        incluir_programa_blanco = True

    # Selector de año (solo si NO se marcan todos los años)
    if not modo_todos_anios:
        anios_disponibles = sorted(df["_anio"].dropna().unique().tolist(), reverse=True)
        if not anios_disponibles and not incluir_sin_fecha:
            st.info("No hay años disponibles en la columna de último contacto.")
            return

        anio_sel = None
        if anios_disponibles:
            anio_sel = st.selectbox("Año (último contacto)", [str(int(a)) for a in anios_disponibles], index=0)
            anio_sel_int = int(anio_sel)
        else:
            # No hay años (todo NaN), trabajaremos solo con sin fecha si se permite
            anio_sel_int = None
    else:
        anio_sel = "Todos"
        anio_sel_int = None

    # Construcción del DataFrame base según controles
    base = df.copy()

    # Filtrado por 'Programa' en blanco o no
    if not incluir_programa_blanco:
        base = base[~_is_blank_series(base["Programa"])].copy()

    # Filtrado por año / sin fecha
    if modo_todos_anios:
        # No filtramos por año; opcionalmente incluimos o excluimos NaN de _anio
        if not incluir_sin_fecha:
            base = base[base["_anio"].notna()].copy()
    else:
        # Solo año seleccionado
        mask_year = pd.Series(False, index=base.index)
        if anio_sel_int is not None:
            mask_year |= (base["_anio"] == anio_sel_int)
        if incluir_sin_fecha:
            mask_year |= base["_anio"].isna()
        base = base[mask_year].copy()

    # Filtro por programa (como ya tenías)
    st.subheader("Selecciona un programa")
    programas_unicos = sorted(base["programa_categoria"].unique())
    programa_seleccionado = st.selectbox("Programa", ["Todos"] + programas_unicos)
    df_filtrado = base if programa_seleccionado == "Todos" else base[base["programa_categoria"] == programa_seleccionado]

    # UI
    col1, col2 = st.columns(2)

    with col1:
        # === KPI TOTAL (respeta los controles) ===
        titulo_anio = anio_sel if anio_sel else "—"
        st.metric(f"Total matrículas — {titulo_anio}", value=int(base.shape[0]))

        # === Gráfico por programa (respeta “Todos los años” y “sin fecha”) ===
        if not modo_todos_anios:
            graf_title = f"Total matrículas por programa — {titulo_anio}"
        else:
            graf_title = "Total matrículas por programa — Todos los años"

        conteo_programa = df_filtrado["programa_categoria"].value_counts().reset_index()
        conteo_programa.columns = ["programa", "cantidad"]

        if conteo_programa.empty:
            st.info("No hay datos para los filtros seleccionados.")
        else:
            colores = px.colors.qualitative.Plotly
            color_map = {row["programa"]: colores[i % len(colores)] for i, row in conteo_programa.iterrows()}
            fig1 = px.bar(
                conteo_programa, x="programa", y="cantidad",
                color="programa", text="cantidad",
                color_discrete_map=color_map,
                title=graf_title
            )
            fig1.update_layout(
                xaxis_title=None, yaxis_title="Cantidad",
                showlegend=not is_mobile, xaxis=dict(showticklabels=False)
            )
            st.plotly_chart(fig1, use_container_width=True)

            if is_mobile:
                st.markdown("---")
                st.markdown("<h4 style='font-size: 1rem;'>Detalle de programas</h4>", unsafe_allow_html=True)
                for _, row in conteo_programa.iterrows():
                    color = color_map[row["programa"]]
                    st.markdown(
                        f"<div style='font-size: 12px; margin-bottom: 4px;'>"
                        f"<span style='display: inline-block; width: 10px; height: 10px; background-color: {color}; margin-right: 6px; border-radius: 2px;'></span>"
                        f"{row['programa']}</div>",
                        unsafe_allow_html=True
                    )

    with col2:
        st.subheader("Propietarios")
        propietarios = ["Todos"] + sorted(df_filtrado["propietario"].unique())
        propietario_seleccionado = st.selectbox("Selecciona un propietario", propietarios)

        df_final = df_filtrado if propietario_seleccionado == "Todos" else df_filtrado[df_filtrado["propietario"] == propietario_seleccionado]

        current_year = datetime.now().year
        # Si estás en “Todos los años”, el KPI de propietario indica TOTAL con el mismo ámbito:
        if modo_todos_anios:
            label_kpi = "Matrículas (todos los años)"
        else:
            label_kpi = "Matrícula en curso" if (anio_sel_int == current_year) else f"Matrícula {anio_sel}"

        st.metric(label=label_kpi, value=df_final.shape[0])

        if propietario_seleccionado == "Todos":
            conteo_prop = df_final["propietario"].value_counts().reset_index()
            conteo_prop.columns = ["propietario", "cantidad"]
            if not conteo_prop.empty:
                fig2 = px.funnel(conteo_prop, y="propietario", x="cantidad", text="cantidad", color_discrete_sequence=["#1f77b4"])
                fig2.update_layout(xaxis_title="Cantidad", yaxis_title=None, showlegend=False)
                fig2.update_traces(texttemplate="%{x}", textfont_size=16, textposition="inside")
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No hay propietarios para los filtros aplicados.")
        else:
            tabla_programas = (
                df_final.groupby("programa_categoria").size().reset_index(name="Cantidad")
                .sort_values("Cantidad", ascending=False)
            )
            if not tabla_programas.empty:
                st.dataframe(tabla_programas, use_container_width=True)
            else:
                st.info("Este propietario no tiene registros para el filtro actual.")

    # --- Promedio de PVP ---
    st.markdown("---")
    if "PVP" in df_final.columns and not df_final.empty:
        df_final = df_final.copy()
        df_final["PVP"] = pd.to_numeric(df_final["PVP"], errors="coerce").fillna(0)
        promedio_pvp = df_final["PVP"].sum() / df_final.shape[0] if df_final.shape[0] else 0
        st.metric(label="Promedio de PVP", value=f"{promedio_pvp:,.0f} €")
    else:
        st.metric(label="Promedio de PVP", value="0 €")

    # ===== Análisis =====
    st.subheader("📊 Análisis")
    col3, col4 = st.columns([1, 1])

    with col3:
        st.subheader("Forma de Pago")
        if "Forma de Pago" in df_final.columns and not df_final.empty:
            tmp = df_final.copy()
            forma_pago_str = tmp["Forma de Pago"].astype(str).str.strip()
            tmp["Forma de Pago (vist)"] = forma_pago_str.replace(["", "nan", "NaN", "NONE", "None"], "(En Blanco)")
            conteo_pago = tmp["Forma de Pago (vist)"].value_counts().reset_index()
            conteo_pago.columns = ["forma_pago", "cantidad"]

            if not conteo_pago.empty:
                formas_pago = conteo_pago["forma_pago"].tolist()
                color_palette = px.colors.qualitative.Bold
                color_map_fp = {fp: color_palette[i % len(color_palette)] for i, fp in enumerate(formas_pago)}
                fig3 = px.pie(conteo_pago, names="forma_pago", values="cantidad", hole=0.4, color="forma_pago", color_discrete_map=color_map_fp)
                fig3.update_layout(showlegend=True, legend_title="Forma de pago")
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("No hay datos de 'Forma de Pago' para los filtros seleccionados.")
        else:
            st.info("La columna 'Forma de Pago' no está disponible en el archivo.")

    with col4:
        st.subheader("Suma de PVP por Forma de Pago")
        if "Forma de Pago" in df_final.columns and "PVP" in df_final.columns and not df_final.empty:
            tmp = df_final.copy()
            tmp["Forma de Pago"] = tmp["Forma de Pago"].astype(str).str.strip().replace(
                ["", "nan", "NaN", "NONE", "None"], "(En Blanco)"
            )
            tmp["PVP"] = pd.to_numeric(tmp["PVP"], errors="coerce").fillna(0)
            suma_pvp = tmp.groupby("Forma de Pago")["PVP"].sum().reset_index().sort_values("PVP", ascending=True)

            fig4 = px.funnel(suma_pvp, y="Forma de Pago", x="PVP", color="Forma de Pago")
            fig4.update_layout(width=650, xaxis_title="Suma de PVP (€)", yaxis=dict(showticklabels=False), showlegend=False)
            fig4.update_traces(texttemplate="%{x:,.0f} €", textfont_size=16, textposition="inside")
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("No hay datos suficientes para mostrar el embudo de PVP por forma de pago.")

    # ======= TABLA FALTANTES =======
    st.markdown("---")
    st.subheader("Registros con PVP, Forma de Pago o Programa en blanco")

    if "PVP" in df_final.columns and "Forma de Pago" in df_final.columns and not df_final.empty:
        tmp = df_final.copy()

        # Flags de blanco SIN convertir aún a "(En Blanco)"
        fp_blank_flag  = _is_blank_series(tmp["Forma de Pago"])
        prog_blank_flag = _is_blank_series(tmp["Programa"]) | (
            tmp["Programa"].astype(str).str.strip().str.lower() == "(en blanco)"
        )

        # PVP numérico y flags (en blanco o cero)
        tmp["PVP_NUM"] = pd.to_numeric(tmp["PVP"], errors="coerce")
        pvp_blank_text_flag = _is_blank_series(tmp["PVP"])
        pvp_zero_flag = tmp["PVP_NUM"].fillna(0) == 0
        pvp_blank_flag = pvp_blank_text_flag | pvp_zero_flag

        # Filtrar registros donde falte cualquiera de los tres campos
        faltantes = tmp[fp_blank_flag | pvp_blank_flag | prog_blank_flag].copy()

        if not faltantes.empty:
            # Normalización visual
            faltantes["Forma de Pago"] = faltantes["Forma de Pago"].astype(str).str.strip().replace(
                ["", "nan", "NaN", "NONE", "None"], "(En Blanco)"
            )
            faltantes["Programa"] = faltantes["Programa"].astype(str).str.strip().replace(
                ["", "nan", "NaN", "NONE", "None"], "(En Blanco)"
            )

            # Formateo PVP visible: NaN o <= 0 -> "(En Blanco)"
            def _pvp_display(row):
                val_num = pd.to_numeric(row.get("PVP_NUM"), errors="coerce")
                if pd.isna(val_num) or val_num <= 0:
                    return "(En Blanco)"
                return f"{val_num:,.0f} €".replace(",", ".")
            faltantes["PVP"] = faltantes.apply(_pvp_display, axis=1)

            # Columna informativa de qué campo(s) faltan
            def _faltan(row):
                missing = []
                if str(row["Programa"]).strip().lower() == "(en blanco)":
                    missing.append("Programa")
                if str(row["Forma de Pago"]).strip().lower() == "(en blanco)":
                    missing.append("Forma de Pago")
                val_num = pd.to_numeric(row.get("PVP_NUM"), errors="coerce")
                if pd.isna(val_num) or val_num <= 0:
                    missing.append("PVP")
                return ", ".join(missing) if missing else ""
            faltantes["Campos en blanco"] = faltantes.apply(_faltan, axis=1)

            # 🚫 Sin 'programa_categoria'
            st.dataframe(
                faltantes[["propietario", "Programa", "Forma de Pago", "PVP", "Campos en blanco"]]
                .reset_index(drop=True),
                use_container_width=True
            )
        else:
            st.info("No hay registros con PVP, Forma de Pago o Programa en blanco para este filtro.")
    else:
        st.info("No hay datos suficientes para mostrar el detalle de faltantes.")
