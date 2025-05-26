import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Tarjeta con matrícula e importe
def render_info_card(title: str, value1, value2, color: str = "#e3f2fd"):
    return f"""
        <div style='padding: 8px; background-color: {color}; border-radius: 8px;
                    font-size: 13px; text-align: center; border: 1px solid #ccc;
                    box-shadow: 1px 1px 5px rgba(0,0,0,0.1);'>
            <strong>{title}</strong><br>
            👥 Matrículas: <strong>{value1}</strong><br>
            💶 Importe: <strong>{value2} €</strong>
        </div>
    """

# Tarjeta solo con importe
def render_import_card(title: str, value, color: str = "#ede7f6"):
    return f"""
        <div style='padding: 8px; background-color: {color}; border-radius: 8px;
                    font-size: 13px; text-align: center; border: 1px solid #ccc;
                    box-shadow: 1px 1px 5px rgba(0,0,0,0.1);'>
            <strong>{title}</strong><br>
            💶 <strong>{value} €</strong>
        </div>
    """

def principal_page():
    st.title("📊 Panel Principal")
    st.markdown("## 📥 Admisiones")

    UPLOAD_FOLDER = "uploaded_admisiones"
    GESTION_FOLDER = "uploaded"
    ACADEMICO_FILE = os.path.join("uploaded_academica", "Indicadores Académicos EIP.xlsx")
    VENTAS_FILE = os.path.join(UPLOAD_FOLDER, "ventas.xlsx")
    PREVENTAS_FILE = os.path.join(UPLOAD_FOLDER, "preventas.xlsx")
    GESTION_FILE = os.path.join(GESTION_FOLDER, "archivo_cargado.xlsx")

    traduccion_meses = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    mes_actual = datetime.now().month
    anio_actual = datetime.now().year

    total_matriculas = 0
    total_preventas = 0
    total_preventas_importe = 0
    columnas_validas = []
    matriculas_por_mes = {}
    importes_por_mes = {}
    estados = {}

    # Ventas
    if os.path.exists(VENTAS_FILE):
        df_ventas = pd.read_excel(VENTAS_FILE)
        if "fecha de cierre" in df_ventas.columns:
            df_ventas['fecha de cierre'] = pd.to_datetime(df_ventas['fecha de cierre'], dayfirst=True, errors='coerce')
            df_ventas = df_ventas.dropna(subset=['fecha de cierre'])
            df_ventas = df_ventas[df_ventas['fecha de cierre'].dt.year == anio_actual]
            total_matriculas = len(df_ventas)
            df_ventas['mes'] = df_ventas['fecha de cierre'].dt.month
            for m in range(1, mes_actual + 1):
                df_mes = df_ventas[df_ventas['mes'] == m]
                matriculas_por_mes[m] = len(df_mes)
                importes_por_mes[m] = df_mes.get('importe', pd.Series(0)).sum()

    # Preventas
    if os.path.exists(PREVENTAS_FILE):
        df_preventas = pd.read_excel(PREVENTAS_FILE)
        total_preventas = len(df_preventas)
        columnas_importe = [col for col in df_preventas.columns if "importe" in col.lower()]
        if columnas_importe:
            total_preventas_importe = df_preventas[columnas_importe].sum(numeric_only=True).sum()

    # Gestión de cobro
    if os.path.exists(GESTION_FILE):
        df_gestion = pd.read_excel(GESTION_FILE)
        if "Estado" in df_gestion.columns:
            for anio in range(2018, anio_actual):
                col = f"Total {anio}"
                if col in df_gestion.columns:
                    columnas_validas.append(col)
            for mes_num in range(1, mes_actual + 1):
                nombre_mes = f"{traduccion_meses[mes_num]} {anio_actual}"
                if nombre_mes in df_gestion.columns:
                    columnas_validas.append(nombre_mes)
            if columnas_validas:
                df_gestion[columnas_validas] = df_gestion[columnas_validas].apply(pd.to_numeric, errors='coerce').fillna(0)
                df_estado_totales = df_gestion.groupby("Estado")[columnas_validas].sum()
                df_estado_totales["Total"] = df_estado_totales.sum(axis=1)
                estados = df_estado_totales["Total"].to_dict()

    # Tarjetas por mes
    st.markdown(f"### 📅 Matrículas por Mes ({anio_actual})")
    meses = [
        (traduccion_meses[m], matriculas_por_mes.get(m, 0), f"{importes_por_mes.get(m, 0):,.2f}".replace(",", "."))
        for m in range(1, mes_actual + 1)
    ]
    for i in range(0, len(meses), 4):
        cols = st.columns(4)
        for j, (mes, matriculas, importe) in enumerate(meses[i:i+4]):
            cols[j].markdown(render_info_card(mes, matriculas, importe), unsafe_allow_html=True)

    # Totales generales
    st.markdown("### Total General")
    col1, col2 = st.columns(2)
    col1.markdown(render_info_card("Matrículas Totales", total_matriculas, f"{sum(importes_por_mes.values()):,.2f}".replace(",", "."), "#c8e6c9"), unsafe_allow_html=True)
    col2.markdown(render_info_card("Preventas", total_preventas, f"{total_preventas_importe:,.2f}".replace(",", "."), "#ffe0b2"), unsafe_allow_html=True)

    # Gestión de Cobro
    if estados:
        st.markdown("---")
        st.markdown("## 💼 Gestión de Cobro")
        st.markdown("### Totales por Estado")
        estado_items = sorted(estados.items(), key=lambda x: x[1], reverse=True)
        for i in range(0, len(estado_items), 4):
            cols = st.columns(4)
            for j, (estado, total) in enumerate(estado_items[i:i+4]):
                cols[j].markdown(render_import_card(f"Estado: {estado}", f"{total:,.2f}".replace(",", ".")), unsafe_allow_html=True)

    # Indicadores Académicos
    if os.path.exists(ACADEMICO_FILE):
        try:
            df = pd.read_excel(ACADEMICO_FILE, sheet_name="CONSOLIDADO ACADÉMICO")
            st.markdown("---")
            st.markdown("## 🎓 Indicadores Académicos")

            indicadores = [("Alumnos/as", df.iloc[1, 1])]
            for i in range(2, 10):
                nombre = str(df.iloc[i, 1])
                valor = df.iloc[i, 2]
                if pd.notna(nombre) and pd.notna(valor):
                    if "cumplimiento" in nombre.lower() and isinstance(valor, (int, float)) and valor <= 1:
                        valor = f"{valor:.0%}".replace(".", ",")
                    elif isinstance(valor, float) and valor <= 1:
                        valor = f"{valor:.2%}".replace(".", ",")
                    indicadores.append((nombre, valor))

            nombre = str(df.iloc[10, 1])
            valor = df.iloc[10, 2]
            if pd.notna(valor):
                valor = f"{valor:.2%}".replace(".", ",") if isinstance(valor, float) else valor
                indicadores.append((nombre, valor))

            nombre = str(df.iloc[11, 1])
            valor = df.iloc[11, 2]
            if pd.notna(valor):
                indicadores.append((nombre, int(valor)))

            for i in range(0, len(indicadores), 4):
                cols = st.columns(4)
                for j, (titulo, valor) in enumerate(indicadores[i:i+4]):
                    cols[j].markdown(render_import_card(titulo, valor, "#f0f4c3"), unsafe_allow_html=True)

            st.markdown("### 🏅 Certificaciones")
            total_cert = int(df.iloc[13, 2])
            st.markdown(render_import_card("Total Certificaciones", f"{total_cert}", "#dcedc8"), unsafe_allow_html=True)

        except Exception as e:
            st.warning(f"❌ Error al cargar el archivo académico: {e}")
    else:
        st.info("📭 No se encontró el archivo académico.")
