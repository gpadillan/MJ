import streamlit as st
import pandas as pd
import os
import plotly.express as px
import unicodedata
from datetime import datetime
from responsive import get_screen_size

# ==== RUTAS ====
UPLOAD_FOLDER = "uploaded_admisiones"
LEADS_GENERADOS_FILE = os.path.join(UPLOAD_FOLDER, "leads_generados.xlsx")
VENTAS_FILE = os.path.join(UPLOAD_FOLDER, "ventas.xlsx")

# Paleta base para meses (se reutiliza en todos los componentes)
COLORWAY = px.colors.qualitative.Plotly

def app():
    width, height = get_screen_size()
    is_mobile = width <= 400

    traducciones_meses = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    # ===== CARGA LEADS =====
    if not os.path.exists(LEADS_GENERADOS_FILE):
        st.warning("📭 No se ha subido el archivo de Leads Generados aún.")
        return

    df = pd.read_excel(LEADS_GENERADOS_FILE)
    df.columns = df.columns.str.strip().str.lower()

    if 'creado' not in df.columns:
        st.error("❌ En leads: falta la columna 'creado'.")
        return

    # ===== CARGA VENTAS =====
    ventas_ok = os.path.exists(VENTAS_FILE)
    df_ventas = pd.DataFrame()
    if ventas_ok:
        try:
            df_ventas = pd.read_excel(VENTAS_FILE)
            df_ventas.columns = df_ventas.columns.str.strip().str.lower()
        except Exception as e:
            ventas_ok = False
            st.warning(f"⚠️ No se pudo leer ventas.xlsx: {e}")

    # ===== NORMALIZADORES =====
    def normalizar(texto: str) -> str:
        texto = str(texto) if pd.notna(texto) else ""
        texto = texto.lower()
        texto = unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode("utf-8")
        return texto.strip()

    CATEGORIAS_EXACTAS = {
        "MÁSTER IA": [
            "máster en inteligencia artificial", "máster integral en inteligencia artificial", "máster ia",
            "master ia", "master en inteligencia artificial"
        ],
        "MÁSTER RRHH": [
            "máster recursos humanos rrhh: dirección de personas, desarrollo del talento y gestión laboral",
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

    # ===== PREP LEADS =====
    df['creado'] = pd.to_datetime(df['creado'], errors='coerce')
    df = df[df['creado'].notna()]
    df["mes_num"] = df["creado"].dt.month
    df["anio"] = df["creado"].dt.year
    df["mes_nombre"] = df["mes_num"].map(traducciones_meses)
    df["mes_anio"] = df["mes_nombre"] + " " + df["anio"].astype(str)

    if 'programa' not in df.columns or 'propietario' not in df.columns:
        st.error("❌ En leads: faltan las columnas 'programa' y/o 'propietario'.")
        return
    df["programa"] = df["programa"].astype(str).str.strip().replace(["", "nan", "None"], "(En Blanco)")
    df["propietario"] = df["propietario"].astype(str).str.strip().replace(["", "nan", "None"], "(En Blanco)")
    df["programa_categoria"] = df["programa"].apply(clasificar_programa)
    df["programa_final"] = df.apply(lambda r: r["programa"] if r["programa_categoria"] == "SIN CLASIFICAR" else r["programa_categoria"], axis=1)

    # ===== PREP VENTAS =====
    if ventas_ok:
        if 'creado' in df_ventas.columns:
            df_ventas['creado'] = pd.to_datetime(df_ventas['creado'], errors='coerce')
        else:
            df_ventas['creado'] = pd.NaT

        if 'propietario' not in df_ventas.columns:
            ventas_ok = False
            st.warning("⚠️ En ventas.xlsx falta la columna 'propietario'. El ratio por mes no se podrá calcular.")
        else:
            df_ventas["propietario"] = df_ventas["propietario"].astype(str).str.strip().replace(["", "nan", "None"], "(En Blanco)")
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

            df_ventas["mes_num"] = df_ventas["creado"].dt.month
            df_ventas["anio"] = df_ventas["creado"].dt.year
            df_ventas["mes_nombre"] = df_ventas["mes_num"].map(traducciones_meses)
            df_ventas["mes_anio"] = df_ventas.apply(
                lambda r: f"{traducciones_meses.get(int(r['mes_num']), '')} {int(r['anio'])}" if pd.notna(r['mes_num']) and pd.notna(r['anio']) else None, axis=1
            )

    st.subheader("Filtros")

    # ===== FILTRO POR MES (sobre LEADS) =====
    meses_disponibles = df[["mes_anio", "mes_num", "anio"]].dropna().drop_duplicates().sort_values(["anio", "mes_num"])
    opciones_meses = ["Todos"] + meses_disponibles["mes_anio"].tolist()
    mes_seleccionado = st.selectbox("Selecciona un Mes:", opciones_meses)

    df_filtrado = df.copy()
    if mes_seleccionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["mes_anio"] == mes_seleccionado]

    # ===== FILTROS SECUNDARIOS ENCADENADOS =====
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        programas = ["Todos"] + sorted(df_filtrado["programa_final"].unique())
        programa_seleccionado = st.selectbox("Selecciona un Programa:", programas)
    if programa_seleccionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["programa_final"] == programa_seleccionado]

    with col_f2:
        propietarios = ["Todos"] + sorted(df_filtrado["propietario"].unique())
        propietario_seleccionado = st.selectbox("Selecciona un Propietario:", propietarios)
    if propietario_seleccionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["propietario"] == propietario_seleccionado]

    # ===== COLOR POR MES =====
    orden_meses = (
        df_filtrado[["mes_anio", "anio", "mes_num"]]
        .drop_duplicates().sort_values(["anio", "mes_num"])["mes_anio"].tolist()
    )
    if not orden_meses:
        orden_meses = meses_disponibles["mes_anio"].tolist()
    color_map_mes = {mes: COLORWAY[i % len(COLORWAY)] for i, mes in enumerate(orden_meses)}

    # ===== GRÁFICO 📆 Total de Leads por Mes =====
    leads_por_mes = (
        df_filtrado.groupby(["mes_anio", "mes_num", "anio"]).size().reset_index(name="Cantidad")
        .sort_values(["anio", "mes_num"])
    )
    leads_por_mes["Mes"] = leads_por_mes["mes_anio"]
    leads_por_mes["Etiqueta"] = leads_por_mes.apply(lambda r: f"{r['Mes']} - {r['Cantidad']}", axis=1)

    if is_mobile:
        fig_leads = px.bar(leads_por_mes, x="Cantidad", y="Mes", orientation="h", text="Cantidad",
                           height=420, color="Mes", color_discrete_map=color_map_mes)
        fig_leads.update_traces(textposition="outside")
    else:
        fig_leads = px.pie(leads_por_mes, names="Etiqueta", values="Cantidad",
                           hole=0.4, color="Mes", color_discrete_map=color_map_mes)

    # === LAYOUT: gráfico de meses + resumen por programa (con TOTAL) ===
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📆 Total de Leads por Mes")
        st.plotly_chart(fig_leads, use_container_width=True)

    with col2:
        conteo_programas = (
            df_filtrado["programa_final"].value_counts(dropna=False)
            .rename_axis("Programa").reset_index(name="Cantidad")
        )
        total_programas = int(conteo_programas["Cantidad"].sum())
        total_fmt = f"{total_programas:,}".replace(",", ".")
        st.subheader(f"📘 Total de Leads por Programa – TOTAL: {total_fmt}")
        st.dataframe(conteo_programas.style.background_gradient(cmap="Blues"), use_container_width=True)

    # =========================
    # TARJETAS POR PROPIETARIO (con VENTAS y RATIO por mes)
    # =========================
    st.subheader(" Ventas por Propietario")

    # LEADS por propietario y mes (para chips)
    df_mes_prop = (
        df_filtrado.groupby(["anio", "mes_num", "mes_anio", "propietario"])
        .size().reset_index(name="leads")
        .sort_values(["anio", "mes_num", "propietario"])
    )
    if df_mes_prop.empty:
        st.info("No hay datos para el filtro seleccionado.")
        return

    # Totales de leads por propietario (orden)
    totales_leads_prop = df_mes_prop.groupby("propietario")["leads"].sum().sort_values(ascending=False)

    # VENTAS filtradas con los mismos criterios (para chips y ratio por mes)
    ventas_filtrado_cards = pd.DataFrame()
    if ventas_ok:
        ventas_filtrado_cards = df_ventas.copy()
        if mes_seleccionado != "Todos" and "mes_anio" in ventas_filtrado_cards.columns:
            ventas_filtrado_cards = ventas_filtrado_cards[ventas_filtrado_cards["mes_anio"] == mes_seleccionado]
        if programa_seleccionado != "Todos" and "programa_final" in ventas_filtrado_cards.columns:
            ventas_filtrado_cards = ventas_filtrado_cards[ventas_filtrado_cards["programa_final"] == programa_seleccionado]
        if propietario_seleccionado != "Todos":
            ventas_filtrado_cards = ventas_filtrado_cards[ventas_filtrado_cards["propietario"] == propietario_seleccionado]

    # Matriz LEADS por propietario x mes
    leads_prop_mes = (
        df_mes_prop.pivot_table(index="propietario", columns="mes_anio", values="leads",
                                aggfunc="sum", fill_value=0)
        .reindex(index=totales_leads_prop.index)
        .reindex(columns=orden_meses, fill_value=0)
    )

    # Matriz VENTAS por propietario x mes
    if ventas_ok and not ventas_filtrado_cards.empty and "propietario" in ventas_filtrado_cards.columns:
        ventas_prop_mes = (
            ventas_filtrado_cards.groupby(["propietario", "mes_anio"]).size()
            .unstack(fill_value=0)
            .reindex(index=totales_leads_prop.index, fill_value=0)
            .reindex(columns=orden_meses, fill_value=0)
        )
    else:
        ventas_prop_mes = leads_prop_mes.copy() * 0  # todo a cero si no hay ventas

    # Matriz RATIO por propietario x mes (en %)
    ratio_prop_mes = (ventas_prop_mes / leads_prop_mes.replace(0, pd.NA) * 100).fillna(0).round(1)

    # ====== ESTILOS CSS ======
    st.markdown(
        """
        <style>
        .cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
            gap: 14px;
        }
        .card {
            background: #f7fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 14px 14px 10px 14px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        }
        .card h4 { margin: 0 0 6px 0; font-size: 16px; color: #1a202c; }
        .row { display:flex; gap:12px; margin: 6px 0 10px 0; }
        .pill { background:#edf2f7; border-radius:8px; padding:4px 8px; font-size:12px; font-weight:700; color:#2d3748; }
        .chips { display:flex; flex-wrap:wrap; gap:6px; }
        .chip {
            display:inline-flex; align-items:center; flex-wrap:wrap;
            gap:6px; height:auto; padding:6px 8px;
            border-radius:8px; font-size:13px; font-weight:700; color:white;
            box-shadow: inset 0 -1px 0 rgba(0,0,0,0.12);
        }
        .chip .count, .chip .count-alt {
            background: rgba(0,0,0,0.28);
            padding: 2px 6px;
            border-radius: 6px;
            font-weight: 800;
        }
        .chip .count-alt { background: rgba(255,255,255,0.18); }
        </style>
        """, unsafe_allow_html=True
    )

    # ====== RENDER TARJETAS ======
    tarjetas_html = ['<div class="cards-grid">']
    for propietario, leads_total in totales_leads_prop.items():
        ventas_total = int(ventas_prop_mes.loc[propietario].sum()) if ventas_prop_mes.shape[0] else 0
        ratio_global = (ventas_total / leads_total * 100.0) if leads_total > 0 else None
        ratio_global_txt = f"{ratio_global:.1f}%" if ratio_global is not None else "—"

        tarjetas_html.append('<div class="card">')
        tarjetas_html.append(f'<h4>{propietario}</h4>')
        tarjetas_html.append(
            f'<div class="row">'
            f'<span class="pill">🧊 Leads: {int(leads_total)}</span>'
            f'<span class="pill">🧾 Ventas: {ventas_total}</span>'
            f'<span class="pill">🎯 Ratio: {ratio_global_txt}</span>'
            f'</div>'
        )

        # Chips por mes: mostramos si hay leads >0 o ventas >0
        tarjetas_html.append('<div class="chips">')
        for mes in orden_meses:
            l = int(leads_prop_mes.loc[propietario, mes]) if mes in leads_prop_mes.columns else 0
            v = int(ventas_prop_mes.loc[propietario, mes]) if mes in ventas_prop_mes.columns else 0
            r = float(ratio_prop_mes.loc[propietario, mes]) if mes in ratio_prop_mes.columns else 0.0
            if (l > 0) or (v > 0):
                bg = color_map_mes.get(mes, "#718096")
                tarjetas_html.append(
                    f'<span class="chip" style="background:{bg}">'
                    f'{mes}'
                    f'<span class="count">L: {l}</span>'
                    f'<span class="count">V: {v}</span>'
                    f'<span class="count-alt">Ratio: {r:.1f}%</span>'
                    f'</span>'
                )
        # Si no hubo nada de nada
        if (leads_prop_mes.loc[propietario].sum() == 0) and (ventas_prop_mes.loc[propietario].sum() == 0):
            tarjetas_html.append('<span class="chip" style="background:#A0AEC0">Sin datos</span>')

        tarjetas_html.append('</div>')  # chips
        tarjetas_html.append('</div>')  # card

    tarjetas_html.append('</div>')      # grid
    st.markdown("\n".join(tarjetas_html), unsafe_allow_html=True)

    # --- ORIGEN DEL LEAD (opcional) ---
    st.subheader("📥 Origen del Lead")
    if 'origen lead' in df_filtrado.columns:
        conteo_origen = df_filtrado['origen lead'].astype(str).value_counts().reset_index()
        conteo_origen.columns = ["Origen Lead", "Cantidad"]
        st.dataframe(conteo_origen.style.background_gradient(cmap="Reds"), use_container_width=True)
    else:
        st.info("ℹ️ No se encontró la columna 'origen lead'.")
