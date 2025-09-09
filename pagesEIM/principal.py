# pagesEIM/principal.py

import os
import re
import unicodedata
from datetime import datetime

import pandas as pd
import streamlit as st
import folium
from streamlit_folium import folium_static

from utils.geo_utils import (
    normalize_text, PROVINCIAS_COORDS, PAISES_COORDS, geolocalizar_pais
)

# =========================================================
# Utils
# =========================================================
def format_euro(value: float) -> str:
    try:
        v = float(value)
    except Exception:
        v = 0.0
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def render_bar_card(title: str, value: float, bg: str, emoji: str = "") -> str:
    """MISMO look & feel que en EIP (medida y estilo idénticos)."""
    return f"""
    <div style="
      background:{bg};
      border:1px solid #dfe3eb;
      border-radius:14px;
      padding:14px 16px;
      box-shadow:0 2px 6px rgba(0,0,0,.06);
    ">
      <div style="font-weight:700;font-size:15px;margin-bottom:8px;color:#1f2d3d">
        {emoji} {title}
      </div>
      <div style="font-size:26px;font-weight:800;color:#1f2d3d">
        € {format_euro(value)}
      </div>
    </div>
    """

# =========================================================
# Carga EIM: sesión -> disco (dos rutas compatibles)
# =========================================================
EIM_UPLOAD_FALLBACKS = [
    os.path.join("uploaded_eim", "archivo_cargado.xlsx"),   # donde guarda la sección EIM
    os.path.join("uploaded", "archivo_cargado_eim.xlsx"),   # compatibilidad
]

def load_eim_df_from_session_or_file() -> pd.DataFrame | None:
    """Prioriza session_state; si no, busca excel en disco (dos rutas)."""
    df = st.session_state.get("excel_data_eim")
    if isinstance(df, pd.DataFrame) and not df.empty:
        return df
    for path in EIM_UPLOAD_FALLBACKS:
        if os.path.exists(path):
            try:
                return pd.read_excel(path, dtype=str)
            except Exception:
                pass
    return None

# =========================================================
# Normalizadores
# =========================================================
def _strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

def _norm_estado(s: str) -> str:
    s = _strip_accents(str(s)).upper()
    s = re.sub(r'\s+', ' ', s).strip()
    return s

MESES_NOMBRE = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

# =========================================================
# Página principal EIM
# =========================================================
def principal_page():
    st.title("📊 Panel EIM")

    # Botón recargar / limpiar
    if st.button("🔄 Recargar datos (EIM)"):
        for k in ["excel_data_eim", "upload_time_eim", "coords_cache"]:
            if k in st.session_state:
                del st.session_state[k]
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("Caché limpiada.")

    anio_actual = datetime.now().year

    # ===================== GESTIÓN DE COBRO (EIM) =====================
    st.markdown("---")
    st.markdown("## 💼 Gestión de Cobro (EIM)")

    df_gestion = load_eim_df_from_session_or_file()

    if df_gestion is None or df_gestion.empty:
        rutas_txt = " o ".join([f"`{p}`" for p in EIM_UPLOAD_FALLBACKS])
        st.info(
            f"No hay datos de Gestión de Cobro disponibles. "
            f"Sube el Excel en la sección **EIM** o publica un archivo en {rutas_txt}."
        )
    else:
        # Normaliza encabezados y localiza 'Estado'
        df_gestion.columns = [c.strip() for c in df_gestion.columns]
        col_estado = next((c for c in df_gestion.columns if c.strip().lower() == "estado"), None)

        if not col_estado:
            st.error("❌ El archivo no contiene la columna 'Estado'.")
        else:
            # Detecta columnas válidas (2018..año-1 + meses año actual)
            columnas_validas = []
            for anio in range(2018, anio_actual):
                col = f"Total {anio}"
                if col in df_gestion.columns:
                    columnas_validas.append(col)
            for mes_num in range(1, 13):
                col_mes = f"{MESES_NOMBRE[mes_num]} {anio_actual}"
                if col_mes in df_gestion.columns:
                    columnas_validas.append(col_mes)

            if not columnas_validas:
                st.info("No se encontraron columnas de totales/meses en el archivo de Gestión de Cobro.")
            else:
                df_gestion[columnas_validas] = df_gestion[columnas_validas].apply(pd.to_numeric, errors="coerce").fillna(0)
                df_resumen = (
                    df_gestion.groupby(col_estado)[columnas_validas]
                              .sum()
                              .reset_index()
                              .rename(columns={col_estado: "Estado"})
                )
                df_resumen["Total"] = df_resumen[columnas_validas].sum(axis=1)

                # === Totales por estado (robusto con acentos) ===
                tot_por_estado = {_norm_estado(r["Estado"]): float(r["Total"]) for _, r in df_resumen.iterrows()}

                cobrado          = tot_por_estado.get("COBRADO", 0.0)
                domic_confirmada = tot_por_estado.get("DOMICILIACION CONFIRMADA", 0.0)
                domic_emitida    = tot_por_estado.get("DOMICILIACION EMITIDA", 0.0)
                pendiente        = tot_por_estado.get("PENDIENTE", 0.0)
                dudoso           = tot_por_estado.get("DUDOSO COBRO", 0.0)
                incobrable       = tot_por_estado.get("INCROBRABLE", tot_por_estado.get("INCOBRABLE", 0.0))
                no_cobrado       = tot_por_estado.get("NO COBRADO", 0.0)

                # ✅ Total Generado = Cobrado + Confirmada + Emitida
                total_generado = cobrado + domic_confirmada + domic_emitida

                # Paleta (misma que en tu EIP)
                COLORS = {
                    "COBRADO": "#E3F2FD",
                    "CONFIRMADA": "#FFE0B2",
                    "EMITIDA": "#FFF9C4",
                    "TOTAL": "#D3F9D8",
                    "PENDIENTE": "#E6FCF5",
                    "DUDOSO": "#FFEBEE",
                    "INCOBRABLE": "#FCE4EC",
                    "NOCOBRADO": "#ECEFF1",
                }

                # ===== Fila 1: Cobrado | Confirmada | Emitida | Total Generado =====
                c1, c2, c3, c4 = st.columns(4)
                c1.markdown(render_bar_card("Cobrado", cobrado, COLORS["COBRADO"], "💵"), unsafe_allow_html=True)
                c2.markdown(render_bar_card("Domiciliación Confirmada", domic_confirmada, COLORS["CONFIRMADA"], "💷"), unsafe_allow_html=True)
                c3.markdown(render_bar_card("Domiciliación Emitida", domic_emitida, COLORS["EMITIDA"], "📤"), unsafe_allow_html=True)
                c4.markdown(render_bar_card("Total Generado", total_generado, COLORS["TOTAL"], "💰"), unsafe_allow_html=True)

                # ===== Fila 2: Pendiente | Dudoso | Incobrable | No Cobrado =====
                b1, b2, b3, b4 = st.columns(4)
                b1.markdown(render_bar_card("Pendiente", pendiente, COLORS["PENDIENTE"], "⏳"), unsafe_allow_html=True)
                b2.markdown(render_bar_card("Dudoso Cobro", dudoso, COLORS["DUDOSO"], "❗"), unsafe_allow_html=True)
                b3.markdown(render_bar_card("Incobrable", incobrable, COLORS["INCOBRABLE"], "⛔"), unsafe_allow_html=True)
                b4.markdown(render_bar_card("No Cobrado", no_cobrado, COLORS["NOCOBRADO"], "🧾"), unsafe_allow_html=True)

    # ===================== 🌍 MAPA (opcional) =====================
    st.markdown("---")
    st.markdown("## 🌍 Global Alumnos")

    df_mapa = load_eim_df_from_session_or_file()
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

            df_esp = df_u[(df_u['País'].str.upper() == 'ESPAÑA') & (df_u['Provincia'].isin(PROVINCIAS_COORDS))]
            df_ext = df_u[(df_u['Provincia'].isna()) | (~df_u['Provincia'].isin(PROVINCIAS_COORDS)) | (df_u['País'] == "Gibraltar")]

            count_prov = df_esp['Provincia'].value_counts().reset_index()
            count_prov.columns = ['Entidad', 'Alumnos']

            count_pais = df_ext['País'].value_counts().reset_index()
            count_pais.columns = ['Entidad', 'Alumnos']

            total_alumnos = int(count_prov['Alumnos'].sum() + count_pais['Alumnos'].sum())
            st.markdown(
                f"<div style='padding:4px 12px;display:inline-block;background:#e3f2fd;border-radius:6px;"
                f"font-weight:700;color:#1565c0;'>👥 Total: {total_alumnos}</div>",
                unsafe_allow_html=True
            )

            mapa = folium.Map(location=[25, 0], zoom_start=2, width="100%", height="700px", max_bounds=True)

            # Provincias 🇪🇸
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
            folium.Marker(
                location=[40.4268, -3.7138],
                popup=f"<b>España (provincias)</b><br>Total alumnos: {total_espana}",
                tooltip=f"España (provincias) ({total_espana})",
                icon=folium.Icon(color="red", icon="flag", prefix="fa")
            ).add_to(mapa)

            def get_flag_emoji(pais_nombre):
                FLAGS = {
                    "Francia":"🇫🇷","Portugal":"🇵🇹","Italia":"🇮🇹","Alemania":"🇩🇪","Reino Unido":"🇬🇧",
                    "Marruecos":"🇲🇦","Argentina":"🇦🇷","México":"🇲🇽","Colombia":"🇨🇴","Chile":"🇨🇱",
                    "Brasil":"🇧🇷","Perú":"🇵🇪","Uruguay":"🇺🇾","Venezuela":"🇻🇪","Ecuador":"🇪🇨",
                    "Gibraltar":"🇬🇮"
                }
                return FLAGS.get(pais_nombre.title(), "🌍")

            # Países 🌍
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

    df_check = load_eim_df_from_session_or_file()
    if df_check is None or df_check.empty:
        st.warning("⚠️ No hay archivo cargado para revisar clientes incompletos (EIM).")
        return

    required_cols_check = ['Cliente', 'Provincia', 'Localidad', 'Nacionalidad', 'País', 'Comercial']
    missing_cols = [c for c in required_cols_check if c not in df_check.columns]

    if missing_cols:
        st.warning(f"⚠️ Faltan columnas en el archivo: {', '.join(missing_cols)}")
    else:
        df_filtrado = df_check[df_check['País'].astype(str).str.strip().str.upper() == "ESPAÑA"].copy()
        df_incompletos = df_filtrado[
            df_filtrado['Provincia'].isna() | (df_filtrado['Provincia'].astype(str).str.strip() == '') |
            df_filtrado['Localidad'].isna() | (df_filtrado['Localidad'].astype(str).str.strip() == '')
        ][['Cliente', 'Provincia', 'Localidad', 'Nacionalidad', 'País', 'Comercial']]

        df_incompletos = (
            df_incompletos.drop_duplicates(subset=["Cliente"])
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
