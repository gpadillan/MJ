import streamlit as st
import pandas as pd
import os
import plotly.express as px
import unicodedata
from datetime import datetime
from io import BytesIO
from responsive import get_screen_size

# ==== RUTAS ====
UPLOAD_FOLDER = "uploaded_admisiones"
LEADS_GENERADOS_FILE = os.path.join(UPLOAD_FOLDER, "leads_generados.xlsx")
VENTAS_FILE = os.path.join(UPLOAD_FOLDER, "ventas.xlsx")

# Paleta base (fallback)
COLORWAY = px.colors.qualitative.Plotly

# ==== COLORES CONFIGURABLES (EDITA AQUÍ) ====
MES_COLORS_BAR = {
    "Enero": "#1e88e5",
    "Febrero": "#fb8c00",
    "Marzo": "#43a047",
    "Abril": "#e53935",
    "Mayo": "#8e24aa",
    "Junio": "#6d4c41",
    "Julio": "#ec407a",
    "Agosto": "#9e9e9e",
    "Septiembre": "#3fca33",
    "Octubre": "#00acc1",
    "Noviembre": "#5c6bc0",
    "Diciembre": "#f4511e",
}
USE_SAME_COLORS_FOR_CARDS = False
CARDS_LIGHTEN_FACTOR = 0.83

def app():
    width, height = get_screen_size()
    is_mobile = width <= 400

    traducciones_meses = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    MESES_ORDEN = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

    # ---------- helpers ----------
    def normalizar(texto: str) -> str:
        texto = str(texto) if pd.notna(texto) else ""
        texto = texto.lower()
        texto = unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode("utf-8")
        return texto.strip()

    def add_mes_cols(df: pd.DataFrame) -> pd.DataFrame:
        """Crea SIEMPRE las columnas mes_num, anio, mes_nombre y mes_anio."""
        fecha_col = None
        for c in ["creado", "fecha", "fecha_creacion"]:
            if c in df.columns:
                fecha_col = c
                break
        df["creado"] = pd.to_datetime(df.get(fecha_col), errors="coerce")
        df["mes_num"] = df["creado"].dt.month
        df["anio"] = df["creado"].dt.year
        df["mes_nombre"] = df["mes_num"].map(traducciones_meses)
        df["mes_anio"] = df.apply(
            lambda r: f"{traducciones_meses.get(int(r['mes_num']), '')} {int(r['anio'])}"
            if pd.notna(r["mes_num"]) and pd.notna(r["anio"]) else None, axis=1
        )
        return df

    def header_with_total(label: str, total: int):
        st.markdown(f"#### {label}")
        st.markdown(
            f"<div style='margin:-6px 0 10px 0; font-weight:700'>TOTAL: {format(total, ',').replace(',', '.')}</div>",
            unsafe_allow_html=True
        )

    def lighten_hex(hex_color: str, factor: float = 0.85) -> str:
        """Aclara un color hex mezclándolo con blanco. factor 0..1 (más alto = más claro)."""
        try:
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
        except Exception:
            return "#f3f4f6"
        r_l = int(r + (255 - r) * factor)
        g_l = int(g + (255 - g) * factor)
        b_l = int(b + (255 - b) * factor)
        return f"#{r_l:02x}{g_l:02x}{b_l:02x}"

    # Normaliza a "(En Blanco)"
    def _to_blank_label(series_like) -> pd.Series:
        s = pd.Series(series_like, copy=True)
        s = s.astype(str).str.strip()
        s = s.replace(["", "nan", "NaN", "NONE", "None", "NULL"], "(En Blanco)")
        return s.fillna("(En Blanco)")

    CATEGORIAS_EXACTAS = {
        "MÁSTER IA": [
            "máster en inteligencia artificial", "máster integral en inteligencia artificial", "máster ia",
            "master ia", "master en inteligencia artificial"
        ],
        "MÁSTER RRHH": [
            "máster recursos humanos rrhh: dirección de personas, desarrollo de talento y gestión laboral",
            "máster en rrhh: dirección de personas, desarrollo de talento y gestión laboral",
            "máster rrhh", "master rrhh", "master en rrhh, dirección de personas, desarrollo de talento y gestión laboral"
        ],
        "MÁSTER CIBERSEGURIDAD": [
            "máster en dirección de ciberseguridad, hacking ético y seguridad ofensiva",
            "master en direccion de ciberseguridad, hacking etico y seguridad ofensiva",
            "la importancia de la ciberseguridad y privacidad", "máster ciber", "master ciber", "máster ciberseguridad"
        ],
        "CERTIFICACIÓN SAP S/4HANA": [
            "certificado sap s/4hana finance", "certificado oficial sap s/4hana finance",
            "certificado oficial sap s/4hana sourcing and procurement", "certificado oficial sap s/4hana logística",
            "consultoría sap s4hana finanzas", "consultoría sap bw4/hana",
            "consultoría sap s4hana planificación de la producción y fabricación",
            "sap btp: la plataforma para la transformación digital",
            "máster en dirección financiera y consultoría funcional sap s/4hana finance", "sap s/4hana", "sap"
        ],
        "MÁSTER DPO": [
            "máster profesional en auditoría de protección de datos, gestión de riesgos y cyber compliance",
            "master en auditoría de protección de datos, gestión de riesgos y cyber compliance",
            "máster en dirección de compliance & protección de datos",
            "máster en auditoría de protección de datos, gestión de riesgos y cyber compliance​", "dpo"
        ],
        "MÁSTER EERR": [
            "master en gestión eficiente de energías renovables",
            "master profesional en energías renovables, redes inteligentes y movilidad eléctrica",
            "máster en gestión eficiente de las energías renovables",
            "máster en bim y gestión eficiente de la energía (no usar)", "energías renovables", "eerr"
        ],
        "MBA + RRHH": [
            "doble máster oficial en rrhh + mba", "doble máster en rrhh + mba",
            "doble máster rrhh + mba", "doble máster en dirección financiera + dirección rrhh", "mba rrhh"
        ],
        "PROGRAMA CALIFORNIA": ["programa movilidad california", "california state university"]
    }

    def clasificar_programa(nombre: str) -> str:
        nombre_limpio = normalizar(nombre)
        for categoria, nombres in CATEGORIAS_EXACTAS.items():
            if nombre_limpio in [normalizar(n) for n in nombres]:
                return categoria
        return "SIN CLASIFICAR"

    # ===== CARGA LEADS =====
    if not os.path.exists(LEADS_GENERADOS_FILE):
        st.warning("📭 No se ha subido el archivo de Leads Generados aún.")
        return

    df = pd.read_excel(LEADS_GENERADOS_FILE)
    df.columns = df.columns.str.strip().str.lower()

    if 'creado' not in df.columns:
        st.error("❌ En leads: falta la columna 'creado'.")
        return

    # Prep LEADS
    df['creado'] = pd.to_datetime(df['creado'], errors='coerce')
    df = df[df['creado'].notna()]
    df["mes_num"] = df["creado"].dt.month
    df["anio"] = df["creado"].dt.year
    df["mes_nombre"] = df["mes_num"].map(traducciones_meses)
    df["mes_anio"] = df["mes_nombre"] + " " + df["anio"].astype(str)

    if 'programa' not in df.columns or 'propietario' not in df.columns:
        st.error("❌ En leads: faltan las columnas 'programa' y/o 'propietario'.")
        return
    df["programa"] = _to_blank_label(df["programa"])
    df["propietario"] = _to_blank_label(df["propietario"])
    df["programa_categoria"] = df["programa"].apply(clasificar_programa)
    df["programa_final"] = df.apply(
        lambda r: r["programa"] if r["programa_categoria"] == "SIN CLASIFICAR" else r["programa_categoria"], axis=1
    )

    # ===== CARGA / PREP VENTAS =====
    ventas_ok = os.path.exists(VENTAS_FILE)
    df_ventas = pd.DataFrame()
    if ventas_ok:
        try:
            df_ventas = pd.read_excel(VENTAS_FILE)
            df_ventas.columns = df_ventas.columns.str.strip().str.lower()

            if "propietario" in df_ventas.columns:
                df_ventas["propietario"] = _to_blank_label(df_ventas["propietario"])
            else:
                st.warning("⚠️ En ventas.xlsx falta la columna 'propietario'. Algunas vistas se verán limitadas.")

            prog_col = 'programa' if 'programa' in df_ventas.columns else ('nombre' if 'nombre' in df_ventas.columns else None)
            if prog_col:
                df_ventas["programa_bruto"] = df_ventas[prog_col].astype(str)
                df_ventas["programa_categoria"] = df_ventas["programa_bruto"].apply(clasificar_programa)
                df_ventas["programa_final"] = df_ventas.apply(
                    lambda r: r["programa_bruto"] if r.get("programa_categoria", "SIN CLASIFICAR") == "SIN CLASIFICAR" else r.get("programa_categoria"),
                    axis=1
                )
            else:
                df_ventas["programa_final"] = "(Desconocido)"

            df_ventas = add_mes_cols(df_ventas)

        except Exception as e:
            ventas_ok = False
            st.warning(f"⚠️ No se pudo leer ventas.xlsx: {e}")

    # =========================
    # FILTROS ARRIBA (SIN propietario)
    # =========================
    meses_disponibles = (
        df[["mes_anio", "mes_num", "anio"]]
        .dropna().drop_duplicates()
        .sort_values(["anio", "mes_num"])
    )
    opciones_meses = ["Todos"] + meses_disponibles["mes_anio"].tolist()
    col_fm, col_fp = st.columns([1, 1])
    with col_fm:
        mes_seleccionado = st.selectbox("Selecciona un mes:", opciones_meses)
    with col_fp:
        programas = ["Todos"] + sorted(df["programa_final"].unique())
        programa_seleccionado = st.selectbox("Selecciona un programa:", programas)

    # Aplicar filtros base
    df_filtrado = df.copy()
    if mes_seleccionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["mes_anio"] == mes_seleccionado]
    if programa_seleccionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["programa_final"] == programa_seleccionado]

    # ===== ORDEN Y COLORES POR MES =====
    orden_meses = (
        df_filtrado[["mes_anio", "anio", "mes_num"]]
        .drop_duplicates().sort_values(["anio", "mes_num"])["mes_anio"].tolist()
    )
    if not orden_meses:
        orden_meses = meses_disponibles["mes_anio"].tolist()

    color_map_mes_chart = {}
    for mes in orden_meses:
        base = mes.split(" ")[0]
        color_map_mes_chart[mes] = MES_COLORS_BAR.get(base, "#4c78a8")

    if USE_SAME_COLORS_FOR_CARDS:
        color_map_cards = color_map_mes_chart.copy()
    else:
        color_map_cards = {}
        for mes in orden_meses:
            base = mes.split(" ")[0]
            color_map_cards[mes] = lighten_hex(MES_COLORS_BAR.get(base, "#4c78a8"), CARDS_LIGHTEN_FACTOR)

    # ===== GRÁFICO 📆 Total de clientes potenciales por mes =====
    st.subheader("📅 Total Leads por mes")
    leads_por_mes = (
        df_filtrado.groupby(["mes_anio", "mes_num", "anio"]).size().reset_index(name="Cantidad")
        .sort_values(["anio", "mes_num"])
    )
    leads_por_mes["Mes"] = leads_por_mes["mes_anio"]

    fig_leads = px.bar(
        leads_por_mes, x="Cantidad", y="Mes", orientation="h",
        text="Cantidad", color="Mes", color_discrete_map=color_map_mes_chart,
    )
    fig_leads.update_traces(textposition="outside")
    fig_leads.update_layout(xaxis_title="Cantidad", yaxis_title=None, showlegend=False, height=420 if is_mobile else None)
    st.plotly_chart(fig_leads, use_container_width=True)

    # ===========================================================
    #   TABLAS (selector de propietario SOLO para las tablas)
    # ===========================================================
    st.markdown("### Selecciona un Propietario:")

    df_tablas_global = df.copy()
    if mes_seleccionado != "Todos":
        df_tablas_global = df_tablas_global[df_tablas_global["mes_anio"] == mes_seleccionado]
    if programa_seleccionado != "Todos":
        df_tablas_global = df_tablas_global[df_tablas_global["programa_final"] == programa_seleccionado]

    propietarios_tablas = ["Todos"] + sorted(df_tablas_global["propietario"].unique().tolist())
    propietario_tablas = st.selectbox("Propietario", propietarios_tablas, key="prop_tabs")

    df_tablas = df_tablas_global.copy()
    if propietario_tablas != "Todos":
        df_tablas = df_tablas[df_tablas["propietario"] == propietario_tablas]

    colA, colB, colC = st.columns(3)

    # ------- Tabla 1: Programas (LEADS) -------
    with colA:
        t1 = (
            df_tablas["programa_final"].value_counts(dropna=False)
            .rename_axis("Programa").reset_index(name="Cantidad")
        )
        total1 = int(t1["Cantidad"].sum()) if not t1.empty else 0
        header_with_total("📘 Total Leads por Programa", total1)
        if propietario_tablas != "Todos" and total1 > 0:
            t1 = pd.concat(
                [pd.DataFrame([{"Programa": f"TOTAL {propietario_tablas}", "Cantidad": total1}]), t1],
                ignore_index=True
            )
        st.dataframe(t1.style.background_gradient(cmap="Blues"), use_container_width=True)

    # ------- Tabla 2: Origen de los Leads (LEADS) -------
    with colB:
        origen_col_leads = "origen" if "origen" in df_tablas.columns else ("origen lead" if "origen lead" in df_tablas.columns else None)
        if origen_col_leads:
            tmp = df_tablas.copy()
            tmp[origen_col_leads] = _to_blank_label(tmp[origen_col_leads])
            conteo_origen = tmp[origen_col_leads].value_counts().reset_index()
            conteo_origen.columns = ["Origen Lead", "Cantidad"]
        else:
            conteo_origen = pd.DataFrame(columns=["Origen Lead", "Cantidad"])

        total2 = int(conteo_origen["Cantidad"].sum()) if not conteo_origen.empty else 0
        header_with_total("📄 Origen Leads", total2)
        if propietario_tablas != "Todos" and total2 > 0:
            conteo_origen = pd.concat(
                [pd.DataFrame([{"Origen Lead": f"TOTAL — {propietario_tablas}", "Cantidad": total2}]), conteo_origen],
                ignore_index=True
            )
        st.dataframe(conteo_origen.style.background_gradient(cmap="Greens"), use_container_width=True)

    # ------- Tabla 3: 💶 Leads - Venta (DESDE ventas.xlsx) -------
    with colC:
        if ventas_ok and not df_ventas.empty:
            ventas_tablas = df_ventas.copy()
            # filtros iguales a las otras tablas
            if mes_seleccionado != "Todos":
                ventas_tablas = ventas_tablas[ventas_tablas["mes_anio"] == mes_seleccionado]
            if programa_seleccionado != "Todos":
                ventas_tablas = ventas_tablas[ventas_tablas["programa_final"] == programa_seleccionado]
            if propietario_tablas != "Todos" and "propietario" in ventas_tablas.columns:
                ventas_tablas = ventas_tablas[ventas_tablas["propietario"] == propietario_tablas]

            # origen en ventas
            origen_cols_posibles = ["origen", "origen de la venta", "origen venta", "source"]
            origen_col_v = next((c for c in origen_cols_posibles if c in ventas_tablas.columns), None)

            if origen_col_v:
                tmpv = ventas_tablas.copy()
                tmpv[origen_col_v] = _to_blank_label(tmpv[origen_col_v])
                conteo_origen_v = tmpv[origen_col_v].value_counts().reset_index()
                conteo_origen_v.columns = ["Origen", "Cantidad"]
            else:
                conteo_origen_v = pd.DataFrame(columns=["Origen", "Cantidad"])
        else:
            conteo_origen_v = pd.DataFrame(columns=["Origen", "Cantidad"])

        total3 = int(conteo_origen_v["Cantidad"].sum()) if not conteo_origen_v.empty else 0
        header_with_total("💶 Leads - Venta", total3)
        if propietario_tablas != "Todos" and total3 > 0:
            conteo_origen_v = pd.concat(
                [pd.DataFrame([{"Origen": f"TOTAL — {propietario_tablas}", "Cantidad": total3}]), conteo_origen_v],
                ignore_index=True
            )
        st.dataframe(conteo_origen_v.style.background_gradient(cmap="Purples"), use_container_width=True)

    # ===========================================================
    #  ⬇️ EXPORTAR EXCEL DETALLE (SOLO FILAS EN BLANCO)
    #  - Leads por Programa: sin "Origen" (sí "Origen Lead"), filtro Programa="(En Blanco)"
    #  - Origen Leads: sin "Origen" (sí "Origen Lead"), filtro Origen Lead="(En Blanco)"
    #  - Leads-Venta: sin "Origen Lead" (sí "Origen"), filtro Origen="(En Blanco)"
    # ===========================================================
    def _find_col(cols, candidates):
        return next((c for c in candidates if c in cols), None)

    # ---- Detalle LEADS (normalizado a blancos)
    leads_detalle = df_tablas.copy()
    nombre_col_L = _find_col(leads_detalle.columns, ["nombre", "first name", "firstname"])
    apell_col_L  = _find_col(leads_detalle.columns, ["apellidos", "apellido", "last name", "lastname"])
    origen_col_L = _find_col(leads_detalle.columns, ["origen", "origen lead"])

    leads_export_cols = pd.DataFrame({
        "Propietario": leads_detalle.get("propietario", pd.Series(dtype=str)),
        "Nombre": leads_detalle.get(nombre_col_L, pd.Series(dtype=str)),
        "Apellidos": leads_detalle.get(apell_col_L, pd.Series(dtype=str)),
        "Programa": leads_detalle.get("programa_final", pd.Series(dtype=str)),
        "Origen Lead": leads_detalle.get(origen_col_L, pd.Series([""]*len(leads_detalle))) if origen_col_L else pd.Series([""]*len(leads_detalle)),
        # "Origen" NO se mostrará en hojas 1 y 2
    })
    leads_export_cols["Programa"] = _to_blank_label(leads_export_cols["Programa"])
    leads_export_cols["Origen Lead"] = _to_blank_label(leads_export_cols["Origen Lead"])

    # ---- Detalle VENTAS (y normalización de Origen)
    if ventas_ok and not df_ventas.empty:
        ventas_detalle = df_ventas.copy()
        if mes_seleccionado != "Todos":
            ventas_detalle = ventas_detalle[ventas_detalle["mes_anio"] == mes_seleccionado]
        if programa_seleccionado != "Todos":
            ventas_detalle = ventas_detalle[ventas_detalle["programa_final"] == programa_seleccionado]
        if propietario_tablas != "Todos" and "propietario" in ventas_detalle.columns:
            ventas_detalle = ventas_detalle[ventas_detalle["propietario"] == propietario_tablas]
    else:
        ventas_detalle = pd.DataFrame(columns=["propietario","programa_final"])

    nombre_col_V = _find_col(ventas_detalle.columns, ["nombre", "first name", "firstname"])
    apell_col_V  = _find_col(ventas_detalle.columns, ["apellidos", "apellido", "last name", "lastname"])
    origen_col_V = _find_col(ventas_detalle.columns, ["origen", "origen de la venta", "origen venta", "source"])

    ventas_export_cols = pd.DataFrame({
        "Propietario": ventas_detalle.get("propietario", pd.Series(dtype=str)),
        "Nombre": ventas_detalle.get(nombre_col_V, pd.Series(dtype=str)),
        "Apellidos": ventas_detalle.get(apell_col_V, pd.Series(dtype=str)),
        "Programa": ventas_detalle.get("programa_final", pd.Series(dtype=str)),
        # "Origen Lead" NO se mostrará en hoja 3
        "Origen": ventas_detalle.get(origen_col_V, pd.Series([""]*len(ventas_detalle))) if origen_col_V else pd.Series([""]*len(ventas_detalle))
    })
    ventas_export_cols["Origen"] = _to_blank_label(ventas_export_cols["Origen"])

    # ======= FILTROS “SOLO EN BLANCO” + SELECCIÓN DE COLUMNAS =======
    # Hoja 1: Leads por Programa (sin "Origen", sí "Origen Lead"), Programa en blanco
    hoja1_cols = ["Propietario", "Nombre", "Apellidos", "Programa", "Origen Lead"]
    hoja1 = leads_export_cols[hoja1_cols].copy()
    hoja1 = hoja1[hoja1["Programa"] == "(En Blanco)"]

    # Hoja 2: Origen Leads (sin "Origen", sí "Origen Lead"), Origen Lead en blanco
    hoja2_cols = ["Propietario", "Nombre", "Apellidos", "Programa", "Origen Lead"]
    hoja2 = leads_export_cols[hoja2_cols].copy()
    hoja2 = hoja2[hoja2["Origen Lead"] == "(En Blanco)"]

    # Hoja 3: Leads-Venta (sin "Origen Lead", sí "Origen"), Origen en blanco
    hoja3_cols = ["Propietario", "Nombre", "Apellidos", "Programa", "Origen"]
    hoja3 = ventas_export_cols[hoja3_cols].copy()
    hoja3 = hoja3[hoja3["Origen"] == "(En Blanco)"]

    # Construir y mostrar botón de descarga
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        # Hoja 1
        (hoja1 if not hoja1.empty else hoja1.head(0)).to_excel(
            writer, index=False, sheet_name="Programas en blanco"
        )
        # Hoja 2
        (hoja2 if not hoja2.empty else hoja2.head(0)).to_excel(
            writer, index=False, sheet_name="Origen Leads en blanco"
        )
        # Hoja 3
        (hoja3 if not hoja3.empty else hoja3.head(0)).to_excel(
            writer, index=False, sheet_name="Leads-Venta (Origen en blanco)"
        )

    st.download_button(
        label="⬇️ Descargar detalle (Excel) — SOLO EN BLANCO",
        data=buffer.getvalue(),
        file_name="detalle_leads_y_ventas_en_blanco.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Descarga únicamente las filas en '(En Blanco)' con las columnas exactas por hoja."
    )

    # =========================
    # TARJETAS POR PROPIETARIO
    # =========================
    st.subheader("Desglose por Propietario")

    df_mes_prop = (
        df_filtrado.groupby(["anio", "mes_num", "mes_anio", "propietario"])
        .size().reset_index(name="leads")
        .sort_values(["anio", "mes_num", "propietario"])
    )
    if propietario_tablas != "Todos":
        df_mes_prop = df_mes_prop[df_mes_prop["propietario"] == propietario_tablas]

    if df_mes_prop.empty:
        st.info("No hay datos para el filtro seleccionado.")
        return

    totales_leads_prop = df_mes_prop.groupby("propietario")["leads"].sum().sort_values(ascending=False)

    ventas_filtrado_cards = pd.DataFrame()
    if ventas_ok and not df_ventas.empty:
        ventas_filtrado_cards = df_ventas.copy()
        if mes_seleccionado != "Todos":
            ventas_filtrado_cards = ventas_filtrado_cards[ventas_filtrado_cards["mes_anio"] == mes_seleccionado]
        if programa_seleccionado != "Todos":
            ventas_filtrado_cards = ventas_filtrado_cards[ventas_filtrado_cards["programa_final"] == programa_seleccionado]
        if propietario_tablas != "Todos" and "propietario" in ventas_filtrado_cards.columns:
            ventas_filtrado_cards = ventas_filtrado_cards[ventas_filtrado_cards["propietario"] == propietario_tablas]

    leads_prop_mes = (
        df_mes_prop.pivot_table(index="propietario", columns="mes_anio", values="leads",
                                aggfunc="sum", fill_value=0)
        .reindex(index=totales_leads_prop.index)
        .reindex(columns=orden_meses, fill_value=0)
    )

    if (
        ventas_ok
        and not ventas_filtrado_cards.empty
        and {"propietario", "mes_anio"}.issubset(ventas_filtrado_cards.columns)
    ):
        ventas_prop_mes = (
            ventas_filtrado_cards.groupby(["propietario", "mes_anio"]).size()
            .unstack(fill_value=0)
            .reindex(index=totales_leads_prop.index, fill_value=0)
            .reindex(columns=orden_meses, fill_value=0)
        )
    else:
        ventas_prop_mes = leads_prop_mes.copy() * 0

    ratio_prop_mes = (ventas_prop_mes / leads_prop_mes.replace(0, pd.NA) * 100).fillna(0).round(2)

    # ====== ESTILOS CSS ======
    st.markdown(
        """
        <style>
        .cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 14px;
        }
        .card {
            background: #ffffff;
            border: 1px solid #edf2f7;
            border-radius: 12px;
            padding: 14px 14px 10px 14px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .card h4 { margin: 0 0 6px 0; font-size: 16px; color: #1a202c; }
        .row { display:flex; gap:12px; margin: 6px 0 10px 0; }
        .pill { background:#f3f4f6; border-radius:8px; padding:4px 8px; font-size:12px; font-weight:700; color:#111827; }
        .chips { display:flex; flex-wrap:wrap; gap:6px; }
        .chip {
            display:inline-flex; align-items:center; flex-wrap:wrap;
            gap:6px; height:auto; padding:6px 8px;
            border-radius:8px; font-size:13px; font-weight:700; color:#111827;
            box-shadow: inset 0 -1px 0 rgba(0,0,0,0.04);
            border: 1px solid rgba(0,0,0,0.04);
        }
        .chip .count, .chip .count-alt {
            background: rgba(0,0,0,0.06);
            padding: 2px 6px;
            border-radius: 6px;
            font-weight: 800;
        }
        .chip .count-alt { background: rgba(0,0,0,0.10); }
        </style>
        """,
        unsafe_allow_html=True
    )

    # ====== RENDER TARJETAS ======
    tarjetas_html = ['<div class="cards-grid">']
    for propietario, leads_total in totales_leads_prop.items():
        ventas_total = int(ventas_prop_mes.loc[propietario].sum()) if ventas_prop_mes.shape[0] else 0
        ratio_global = (ventas_total / leads_total * 100.0) if leads_total > 0 else None
        ratio_global_txt = f"{ratio_global:.2f}" if ratio_global is not None else "—"

        tarjetas_html.append('<div class="card">')
        tarjetas_html.append(f'<h4>{propietario}</h4>')
        tarjetas_html.append(
            f'<div class="row">'
            f'<span class="pill">🧊 Leads: {int(leads_total)}</span>'
            f'<span class="pill">🧾 Ventas: {ventas_total}</span>'
            f'<span class="pill">🎯 Ratio: {ratio_global_txt}</span>'
            f'</div>'
        )

        tarjetas_html.append('<div class="chips">')
        for mes in orden_meses:
            l = int(leads_prop_mes.loc[propietario, mes]) if mes in leads_prop_mes.columns else 0
            v = int(ventas_prop_mes.loc[propietario, mes]) if mes in ventas_prop_mes.columns else 0
            r = float(ratio_prop_mes.loc[propietario, mes]) if mes in ratio_prop_mes.columns else 0.0
            if (l > 0) or (v > 0):
                bg = color_map_cards.get(mes, "#718096")
                tarjetas_html.append(
                    f'<span class="chip" style="background:{bg}">'
                    f'{mes}'
                    f'<span class="count">L: {l}</span>'
                    f'<span class="count">V: {v}</span>'
                    f'<span class="count-alt">{r:.2f}</span>'
                    f'</span>'
                )
        if (leads_prop_mes.loc[propietario].sum() == 0) and (ventas_prop_mes.loc[propietario].sum() == 0):
            tarjetas_html.append('<span class="chip" style="background:#A0AEC0">Sin datos</span>')

        tarjetas_html.append('</div>')  # chips
        tarjetas_html.append('</div>')  # card

    tarjetas_html.append('</div>')      # grid
    st.markdown("\n".join(tarjetas_html), unsafe_allow_html=True)

# Ejecución directa
if __name__ == "__main__":
    app()
