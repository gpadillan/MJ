# pagesEIM/principal.py

import os
import pandas as pd
import streamlit as st
from datetime import datetime
from streamlit_folium import folium_static
import folium
from utils.geo_utils import normalize_text, PROVINCIAS_COORDS, PAISES_COORDS, geolocalizar_pais
import unicodedata
import re
from io import BytesIO
import base64

# ===================== UTILS =====================

def format_euro(value: float) -> str:
    try:
        v = float(value)
    except Exception:
        v = 0.0
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def render_import_card(title, value, color="#ede7f6"):
    return f"""
        <div style='padding: 12px; background-color: {color}; border-radius: 10px;
                    font-size: 14px; text-align: center; border: 1px solid #e0e0e0;
                    box-shadow: 0 1px 4px rgba(0,0,0,0.06);'>
            <div style='font-weight:600; margin-bottom:4px'>{title}</div>
            <div style='font-size:18px; font-weight:700'>{value}</div>
        </div>
    """

MESES_NOMBRE = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

# Fichero publicado para todos los usuarios (fallback)
GESTION_FILE = os.path.join("uploaded", "archivo_cargado_eim.xlsx")


def load_eim_df_from_session_or_file(gestion_file_path: str) -> pd.DataFrame | None:
    """
    Prioriza el DF en sesión (si el admin subió el archivo). Si no existe,
    intenta leer el XLSX publicado en disco para que lo vea todo el mundo.
    """
    df = st.session_state.get("excel_data_eim")
    if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
        return df
    if os.path.exists(gestion_file_path):
        try:
            return pd.read_excel(gestion_file_path, dtype=str)
        except Exception:
            return None
    return None


# ===================== PÁGINA PRINCIPAL EIM =====================

def principal_page():
    st.title("📊 Panel EIM")

    # 🔄 Recargar / limpiar caché
    if st.button("🔄 Recargar datos (EIM)"):
        for key in ["excel_data_eim", "coords_cache"]:
            if key in st.session_state:
                del st.session_state[key]
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("Caché limpiada.")

    anio_actual = datetime.now().year

    # ===================== GESTIÓN DE COBRO (EIM) =====================
    st.markdown("## 💼 Gestión de Cobro (EIM)")

    df_gestion = load_eim_df_from_session_or_file(GESTION_FILE)

    if df_gestion is not None and not df_gestion.empty and ("Estado" in df_gestion.columns):
        # Filtrado / normalización del campo Estado
        _INVALID_EST = {"", "NAN", "NULL", "NONE", "NO ENCONTRADO", "-", "S/E", "SIN", "NA"}
        _HIDE_ROWS_CONTAINS = ["BECAS ISA – CONSOLIDADO", "PENDIENTE COBRO ISA"]

        def _norm_estado(x):
            if pd.isna(x):
                return "SIN ESTADO"
            s = str(x).replace("\u00A0", " ").strip().upper()
            return "SIN ESTADO" if s in _INVALID_EST else s

        df_g = df_gestion.copy()

        # Ocultar filas por texto
        if _HIDE_ROWS_CONTAINS:
            mask_hide = df_g["Estado"].astype(str).str.upper().str.contains("|".join(_HIDE_ROWS_CONTAINS), na=False)
            df_g = df_g[~mask_hide].copy()

        # Estado normalizado
        df_g["ESTADO_N"] = df_g["Estado"].apply(_norm_estado)

        # 👉 DESCARTAR "SIN ESTADO"
        df_g = df_g[df_g["ESTADO_N"] != "SIN ESTADO"].copy()

        # Detecta columnas válidas: totales históricos + meses del año actual
        columnas_validas = []
        for anio in range(2018, anio_actual):
            col = f"Total {anio}"
            if col in df_g.columns:
                columnas_validas.append(col)
        for mes_num in range(1, 13):
            col_mes = f"{MESES_NOMBRE[mes_num]} {anio_actual}"
            if col_mes in df_g.columns:
                columnas_validas.append(col_mes)

        if not columnas_validas:
            st.info("No se encontraron columnas de totales/meses en el archivo de Gestión de Cobro (EIM).")
        else:
            # Sumar importes por estado
            df_g[columnas_validas] = df_g[columnas_validas].apply(pd.to_numeric, errors="coerce").fillna(0)
            df_estado = (
                df_g.groupby("ESTADO_N")[columnas_validas].sum()
                    .reset_index()
                    .rename(columns={"ESTADO_N": "Estado"})
            )
            df_estado["Total"] = df_estado[columnas_validas].sum(axis=1)

            # ---- Normalizar claves para diccionario (sin acentos, mayúsculas) ----
            def _strip_accents(s: str) -> str:
                return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

            def _norm_key(s: str) -> str:
                s = _strip_accents(str(s)).upper()
                s = re.sub(r'\s+', ' ', s).strip()
                return s

            tot_por_estado = { _norm_key(r["Estado"]): float(r["Total"]) for _, r in df_estado.iterrows() }

            # Valores por estado
            cobrado          = tot_por_estado.get("COBRADO", 0.0)
            domic_confirmada = tot_por_estado.get("DOMICILIACION CONFIRMADA", 0.0)
            domic_emitida    = tot_por_estado.get("DOMICILIACION EMITIDA", 0.0)  # ← incluir en 1ª fila y Total
            pendiente        = tot_por_estado.get("PENDIENTE", 0.0)
            dudoso           = tot_por_estado.get("DUDOSO COBRO", 0.0)
            incobrable       = tot_por_estado.get("INCOBRABLE", 0.0)
            no_cobrado       = tot_por_estado.get("NO COBRADO", 0.0)

            # ✅ Total generado = Cobrado + Confirmada + Emitida
            total_generado = cobrado + domic_confirmada + domic_emitida

            # Colores
            COLOR_MAP = {
                "COBRADO": "#E3F2FD",
                "DOMICILIACIÓN CONFIRMADA": "#FFE0B2",
                "DOMICILIACIÓN EMITIDA": "#FFF9C4",
                "DUDOSO COBRO": "#FFEBEE",
                "INCOBRABLE": "#FCE4EC",
                "NO COBRADO": "#ECEFF1",
                "PENDIENTE": "#E6FCF5",
                "TOTAL GENERADO": "#D3F9D8",
            }

            # ======= FILA 1: Cobrado | Domiciliación Confirmada | Domiciliación Emitida | Total generado =======
            cols_top = st.columns(4)
            cols_top[0].markdown(
                render_import_card("📒 Cobrado", f"€ {format_euro(cobrado)}", COLOR_MAP["COBRADO"]),
                unsafe_allow_html=True
            )
            cols_top[1].markdown(
                render_import_card("📘 Domiciliación Confirmada", f"€ {format_euro(domic_confirmada)}", COLOR_MAP["DOMICILIACIÓN CONFIRMADA"]),
                unsafe_allow_html=True
            )
            cols_top[2].markdown(
                render_import_card("📤 Domiciliación Emitida", f"€ {format_euro(domic_emitida)}", COLOR_MAP["DOMICILIACIÓN EMITIDA"]),
                unsafe_allow_html=True
            )
            cols_top[3].markdown(
                render_import_card("💰 Total generado", f"€ {format_euro(total_generado)}", COLOR_MAP["TOTAL GENERADO"]),
                unsafe_allow_html=True
            )

            # ======= FILA 2: Pendiente | Dudoso Cobro | Incobrable | No Cobrado (4 en línea) =======
            cols_bottom = st.columns(4)
            items_bottom = [
                ("⏳ Pendiente",   pendiente,  "PENDIENTE"),
                ("❗ Dudoso Cobro", dudoso,   "DUDOSO COBRO"),
                ("🚫 Incobrable",  incobrable, "INCOBRABLE"),
                ("🧾 No Cobrado",  no_cobrado, "NO COBRADO"),
            ]
            for (title, amount, key), col in zip(items_bottom, cols_bottom):
                color = COLOR_MAP.get(key, "#F5F5F5")
                col.markdown(
                    render_import_card(title, f"€ {format_euro(amount)}", color),
                    unsafe_allow_html=True
                )

    else:
        st.info("No hay datos de Gestión de Cobro (EIM). Sube el Excel en la sección **EIM** o publica un archivo en `uploaded/archivo_cargado_eim.xlsx`.")

    # ===================== MAPA: 🌍 Global Alumnos (EIM) =====================
    st.markdown("---")
    st.markdown("## 🌍 Global Alumnos")

    df_mapa = load_eim_df_from_session_or_file(GESTION_FILE)
    if df_mapa is None or df_mapa.empty:
        st.warning("⚠️ No hay archivo cargado para el mapa (EIM).")
    else:
        required_cols = ['Cliente', 'Provincia', 'País']
        if not all(col in df_mapa.columns for col in required_cols):
            st.error("❌ El archivo debe tener columnas: Cliente, Provincia, País.")
        else:
            if "coords_cache" not in st.session_state:
                st.session_state["coords_cache"] = {}

            df_u = df_mapa.drop_duplicates(subset=['Cliente', 'Provincia', 'País']).copy()
            df_u['Provincia'] = df_u['Provincia'].apply(normalize_text).str.title().str.strip()
            df_u['País'] = df_u['País'].apply(normalize_text).str.title().str.strip()

            # Provincias válidas de España
            df_esp = df_u[(df_u['País'].str.upper() == 'ESPAÑA') & (df_u['Provincia'].isin(PROVINCIAS_COORDS))]
            # Países (incluye registros sin provincia válida)
            df_ext = df_u[(df_u['Provincia'].isna()) | (~df_u['Provincia'].isin(PROVINCIAS_COORDS)) | (df_u['País'] == "Gibraltar")]

            count_prov = df_esp['Provincia'].value_counts().reset_index()
            count_prov.columns = ['Entidad', 'Alumnos']

            count_pais = df_ext['País'].value_counts().reset_index()
            count_pais.columns = ['Entidad', 'Alumnos']

            total_alumnos = int(count_prov['Alumnos'].sum() + count_pais['Alumnos'].sum())

            # Badget total
            st.markdown(
                f"<div style='padding: 4px 12px; display:inline-block; background-color:#e3f2fd; border-radius:6px; "
                f"font-weight:700; color:#1565c0;'>👥 Total: {total_alumnos}</div>",
                unsafe_allow_html=True
            )

            mapa = folium.Map(location=[25, 0], zoom_start=2, width="100%", height="700px", max_bounds=True)

            # 🔵 Provincias de España
            for _, row in count_prov.iterrows():
                entidad, alumnos = row['Entidad'], int(row['Alumnos'])
                coords = PROVINCIAS_COORDS.get(entidad)
                if coords:
                    folium.Marker(
                        location=coords,
                        popup=f"<b>{entidad}</b><br>Alumnos: {alumnos}",
                        tooltip=f"{entidad} ({alumnos})",
                        icon=folium.Icon(color="blue", icon="user", prefix="fa")
                    ).add_to(mapa)

            # 🔴 Marcador central España
            total_espana = int(count_prov['Alumnos'].sum())
            coords_espana = [40.4268, -3.7138]
            folium.Marker(
                location=coords_espana,
                popup=f"<b>España (provincias)</b><br>Total alumnos: {total_espana}",
                tooltip=f"España (provincias) ({total_espana})",
                icon=folium.Icon(color="red", icon="flag", prefix="fa")
            ).add_to(mapa)

            # 🌍 Banderas por país
            def get_flag_emoji(pais_nombre):
                FLAGS = {
                    "Francia": "🇫🇷", "Portugal": "🇵🇹", "Italia": "🇮🇹",
                    "Alemania": "🇩🇪", "Reino Unido": "🇬🇧", "Marruecos": "🇲🇦",
                    "Argentina": "🇦🇷", "México": "🇲🇽", "Colombia": "🇨🇴",
                    "Chile": "🇨🇱", "Brasil": "🇧🇷", "Perú": "🇵🇪",
                    "Uruguay": "🇺🇾", "Venezuela": "🇻🇪", "Ecuador": "🇪🇨",
                    "Gibraltar": "🇬🇮"
                }
                return FLAGS.get(pais_nombre.title(), "🌍")

            # 🔴 Países extranjeros / sin provincia válida
            for _, row in count_pais.iterrows():
                entidad, alumnos = row['Entidad'], int(row['Alumnos'])
                if entidad.upper() == "ESPAÑA":
                    continue
                coords = PAISES_COORDS.get(entidad) or st.session_state["coords_cache"].get(entidad)
                if not coords:
                    coords = geolocalizar_pais(entidad)
                    if coords:
                        st.session_state["coords_cache"][entidad] = coords
                if coords:
                    bandera = get_flag_emoji(entidad)
                    folium.Marker(
                        location=coords,
                        popup=f"<b>{bandera} {entidad}</b><br>Alumnos: {alumnos}",
                        tooltip=f"{bandera} {entidad} ({alumnos})",
                        icon=folium.Icon(color="red", icon="globe", prefix="fa")
                    ).add_to(mapa)

            folium_static(mapa)

    # ===================== CLIENTES ESPAÑA INCOMPLETOS =====================
    st.markdown("---")
    st.markdown("## 🧾 Clientes únicos en España con Provincia o Localidad vacías")

    df_check = load_eim_df_from_session_or_file(GESTION_FILE)
    if df_check is None or df_check.empty:
        st.warning("⚠️ No hay archivo cargado para revisar clientes incompletos (EIM).")
        return

    required_cols_check = ['Cliente', 'Provincia', 'Localidad', 'Nacionalidad', 'País', 'Comercial']
    missing_cols = [col for col in required_cols_check if col not in df_check.columns]

    if missing_cols:
        st.warning(f"⚠️ Faltan columnas para la tabla: {', '.join(missing_cols)}")
    else:
        df_filtrado = df_check[df_check['País'].astype(str).str.strip().str.upper() == "ESPAÑA"].copy()
        df_incompletos = df_filtrado[
            df_filtrado['Provincia'].isna() | (df_filtrado['Provincia'].astype(str).str.strip() == '') |
            df_filtrado['Localidad'].isna() | (df_filtrado['Localidad'].astype(str).str.strip() == '')
        ][['Cliente', 'Provincia', 'Localidad', 'Nacionalidad', 'País', 'Comercial']]

        df_incompletos = (
            df_incompletos
            .drop_duplicates(subset=["Cliente"])
            .sort_values(by="Cliente")
            .reset_index(drop=True)
        )

        if df_incompletos.empty:
            st.success("✅ No hay registros en España con Provincia o Localidad vacías.")
        else:
            st.dataframe(df_incompletos, use_container_width=True)

            def to_excel_bytes(df_):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_.to_excel(writer, index=False, sheet_name='Incompletos')
                return output.getvalue()

            excel_data = to_excel_bytes(df_incompletos)
            b64 = base64.b64encode(excel_data).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="clientes_incompletos_eim.xlsx">📥 Descargar Excel</a>'
            st.markdown(href, unsafe_allow_html=True)
