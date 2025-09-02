# principal.py  (pagesEIM)

import os
import pandas as pd
import streamlit as st
from datetime import datetime
from streamlit_folium import folium_static
import folium
from utils.geo_utils import normalize_text, PROVINCIAS_COORDS, PAISES_COORDS, geolocalizar_pais

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

# === Helper para obtener un DataFrame desde session_state sin usar "or" ===
def pick_dataframe(obj):
    """Devuelve un DataFrame si obj lo es; si es un dict, devuelve el primer DataFrame dentro."""
    if obj is None:
        return None
    if isinstance(obj, pd.DataFrame):
        return obj
    if isinstance(obj, dict):
        # si guardaste varias hojas: elegimos la primera que sea DF
        for v in obj.values():
            if isinstance(v, pd.DataFrame):
                return v
    return None

def first_df_from_session(keys):
    """Devuelve el primer DataFrame encontrado en st.session_state para cualquiera de las keys dadas."""
    for k in keys:
        if k in st.session_state:
            df = pick_dataframe(st.session_state.get(k))
            if df is not None:
                return df
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
    GESTION_FILE = os.path.join("uploaded", "archivo_cargado.xlsx")

    # ===================== 💼 GESTIÓN DE COBRO (EIM) =====================
    st.markdown("## 💼 Gestión de Cobro (EIM)")

    # 1) Preferir lo subido en EIM
    df_gestion = first_df_from_session(["excel_data_eim"])

    # 2) Fallback al archivo local
    if df_gestion is None and os.path.exists(GESTION_FILE):
        try:
            df_gestion = pd.read_excel(GESTION_FILE)
        except Exception:
            df_gestion = None

    if df_gestion is not None and not df_gestion.empty and ("Estado" in df_gestion.columns):
        _INVALID_EST = {"", "NAN", "NULL", "NONE", "NO ENCONTRADO", "-"}
        _HIDE_ROWS_CONTAINS = ["BECAS ISA – CONSOLIDADO", "PENDIENTE COBRO ISA"]

        def _norm_estado(x):
            if pd.isna(x): return "SIN ESTADO"
            s = str(x).replace("\u00A0"," ").strip().upper()
            return "SIN ESTADO" if s in _INVALID_EST else s

        df_g = df_gestion.copy()
        if _HIDE_ROWS_CONTAINS:
            mask_hide = df_g["Estado"].astype(str).str.upper().str.contains("|".join(_HIDE_ROWS_CONTAINS), na=False)
            df_g = df_g[~mask_hide].copy()

        df_g["ESTADO_N"] = df_g["Estado"].apply(_norm_estado)

        # Columnas válidas: totales históricos + meses del año actual
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
            df_g[columnas_validas] = df_g[columnas_validas].apply(pd.to_numeric, errors="coerce").fillna(0)
            df_estado = (
                df_g.groupby("ESTADO_N")[columnas_validas].sum()
                    .reset_index()
                    .rename(columns={"ESTADO_N":"Estado"})
            )
            df_estado["Total"] = df_estado[columnas_validas].sum(axis=1)

            ESTADOS_ORDER = [
                "COBRADO",
                "DOMICILIACIÓN CONFIRMADA",
                "DOMICILIACIÓN EMITIDA",
                "DUDOSO COBRO",
                "INCOBRABLE",
                "NO COBRADO",
                "PENDIENTE",
            ]
            COLOR_MAP = {
                "COBRADO": "#E3F2FD",
                "DOMICILIACIÓN CONFIRMADA": "#FFE0B2",
                "DOMICILIACIÓN EMITIDA": "#E8F5E9",
                "DUDOSO COBRO": "#FFEBEE",
                "INCOBRABLE": "#EDE7F6",
                "NO COBRADO": "#F3E5F5",
                "PENDIENTE": "#FCE4EC",
            }

            known = df_estado[df_estado["Estado"].isin(ESTADOS_ORDER)].copy()
            known["__ord"] = known["Estado"].apply(lambda x: ESTADOS_ORDER.index(x))
            others = df_estado[~df_estado["Estado"].isin(ESTADOS_ORDER)].copy()
            others["__ord"] = list(range(len(known), len(known) + len(others)))
            df_estado_sorted = pd.concat([known, others], ignore_index=True).sort_values("__ord").drop(columns="__ord")

            st.markdown("### Total por Estado")
            for i in range(0, len(df_estado_sorted), 4):
                cols = st.columns(4)
                subset = df_estado_sorted.iloc[i:i+4]
                for (idx, row), container in zip(subset.iterrows(), cols):
                    estado = str(row["Estado"]).title()
                    importe = f"{format_euro(row['Total'])} €"
                    color = COLOR_MAP.get(str(row["Estado"]).upper(), "#F5F5F5")
                    container.markdown(render_import_card(estado, importe, color), unsafe_allow_html=True)

            total_general = f"{format_euro(df_estado_sorted['Total'].sum())} €"
            st.markdown("")
            st.markdown(render_import_card("TOTAL", total_general, "#D1C4E9"), unsafe_allow_html=True)

    else:
        st.info("No hay datos de Gestión de Cobro (EIM). Sube el Excel en la sección **EIM** o coloca el archivo en `uploaded/archivo_cargado.xlsx`.")

    # ===================== 🌍 Global Alumnos (EIM) =====================
    st.markdown("---")
    st.markdown("## 🌍 Global Alumnos")

    # ⛔️ IMPORTANTE: nada de "df1 or df2" con DataFrames
    df_mapa = first_df_from_session(["excel_data_eim"])
    if df_mapa is None:
        df_mapa = first_df_from_session(["excel_data"])

    if df_mapa is None:
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

            df_esp = df_u[(df_u['País'].str.upper() == 'ESPAÑA') & (df_u['Provincia'].isin(PROVINCIAS_COORDS))]
            df_ext = df_u[(df_u['Provincia'].isna()) | (~df_u['Provincia'].isin(PROVINCIAS_COORDS)) | (df_u['País'] == "Gibraltar")]

            count_prov = df_esp['Provincia'].value_counts().reset_index()
            count_prov.columns = ['Entidad', 'Alumnos']

            count_pais = df_ext['País'].value_counts().reset_index()
            count_pais.columns = ['Entidad', 'Alumnos']

            total_alumnos = int(count_prov['Alumnos'].sum() + count_pais['Alumnos'].sum())

            st.markdown(
                f"<div style='padding: 4px 12px; display:inline-block; background-color:#e3f2fd; border-radius:6px; "
                f"font-weight:700; color:#1565c0;'>👥 Total: {total_alumnos}</div>",
                unsafe_allow_html=True
            )

            mapa = folium.Map(location=[25, 0], zoom_start=2, width="100%", height="700px", max_bounds=True)

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

            total_espana = int(count_prov['Alumnos'].sum())
            coords_espana = [40.4268, -3.7138]
            folium.Marker(
                location=coords_espana,
                popup=f"<b>España (provincias)</b><br>Total alumnos: {total_espana}",
                tooltip=f"España (provincias) ({total_espana})",
                icon=folium.Icon(color="red", icon="flag", prefix="fa")
            ).add_to(mapa)

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

    # ===================== 🧾 Clientes España incompletos =====================
    st.markdown("---")
    st.markdown("## 🧾 Clientes únicos en España con Provincia o Localidad vacías")

    df_check = first_df_from_session(["excel_data_eim"])
    if df_check is None:
        df_check = first_df_from_session(["excel_data"])

    if df_check is None:
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

            from io import BytesIO
            import base64

            def to_excel_bytes(df_):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_.to_excel(writer, index=False, sheet_name='Incompletos')
                return output.getvalue()

            excel_data = to_excel_bytes(df_incompletos)
            b64 = base64.b64encode(excel_data).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="clientes_incompletos_eim.xlsx">📥 Descargar Excel</a>'
            st.markdown(href, unsafe_allow_html=True)
