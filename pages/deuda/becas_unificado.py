import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
from datetime import datetime
import io

def render():
    if 'excel_data' not in st.session_state or st.session_state['excel_data'] is None:
        st.warning("⚠️ No hay archivo cargado. Ve a la sección Gestión de Datos.")
        return

    df = st.session_state['excel_data']
    df_beca = df[df['Forma Pago'].str.strip().str.upper() == "BECAS ISA"]

    if df_beca.empty:
        st.info("No hay registros con 'BECAS ISA' en la columna 'Forma Pago'.")
        return

    export_dict = {}
    html_buffer = io.StringIO()
    html_buffer.write("<html><head><meta charset='utf-8'><title>Informe Becas ISA</title></head><body>")

    st.subheader("🎓 Becas ISA – Suma por Año")
    html_buffer.write("<h2>🎓 Becas ISA – Suma por Año</h2>")

    columnas_totales = [f'Total {anio}' for anio in range(2018, 2030)]
    disponibles = [col for col in columnas_totales if col in df_beca.columns]
    seleccion = st.multiselect("Selecciona los años a visualizar:", disponibles, default=disponibles, key="filtro_becas_isa_anios")

    if seleccion:
        df_beca[seleccion] = df_beca[seleccion].apply(pd.to_numeric, errors="coerce")
        suma = df_beca[seleccion].sum().reset_index()
        suma.columns = ['Año', 'Suma Total']
        suma['Año'] = suma['Año'].str.replace("Total ", "")
        total = suma['Suma Total'].sum()
        df_total = suma.copy()
        df_total.loc[len(df_total)] = ['TOTAL GENERAL', total]

        st.markdown(f"### 📄 Suma total por año – 🧮 Total acumulado: `{total:,.2f} €`")
        st.dataframe(df_total, use_container_width=True)

        html_buffer.write(f"<p><strong>Total acumulado: {total:,.2f} €</strong></p>")
        html_buffer.write(df_total.to_html(index=False))

        fig = px.bar(suma, x="Año", y="Suma Total", text_auto=".2s", color="Suma Total", color_continuous_scale="viridis")
        fig.update_traces(marker_line_color='black', marker_line_width=0.6)
        fig.update_layout(template="plotly")
        st.plotly_chart(fig, use_container_width=True)

        html_buffer.write(pio.to_html(fig, include_plotlyjs='cdn', full_html=False))
        export_dict["Total_Anios"] = df_total

    st.subheader("📅 Becas ISA – Mes - Año Actual")
    html_buffer.write("<h2>📅 Becas ISA – Mes - Año Actual</h2>")
    año_actual = datetime.today().year
    meses = [f"{mes} {año_actual}" for mes in [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]]
    disponibles_mes = [m for m in meses if m in df_beca.columns]

    if disponibles_mes:
        seleccion_mes = st.multiselect(f"Selecciona los meses de {año_actual}", disponibles_mes, default=disponibles_mes, key="filtro_becas_isa_mes")
        if seleccion_mes:
            df_beca[seleccion_mes] = df_beca[seleccion_mes].apply(pd.to_numeric, errors="coerce").fillna(0)
            suma_mes = df_beca[seleccion_mes].sum().reset_index()
            suma_mes.columns = ['Mes', 'Suma Total']
            total_mes = suma_mes['Suma Total'].sum()
            df_total_mes = suma_mes.copy()
            df_total_mes.loc[len(df_total_mes)] = ['TOTAL GENERAL', total_mes]

            st.markdown(f"### 📄 Suma mensual de Becas ISA – 🧮 Total acumulado: `{total_mes:,.2f} €`")
            st.dataframe(df_total_mes, use_container_width=True)

            html_buffer.write(f"<p><strong>Total acumulado mensual: {total_mes:,.2f} €</strong></p>")
            html_buffer.write(df_total_mes.to_html(index=False))

            fig_mes = px.pie(suma_mes, names="Mes", values="Suma Total", title=f"Distribución mensual – Becas ISA {año_actual}")
            fig_mes.update_traces(textinfo='percent+label')
            fig_mes.update_layout(template="plotly")
            st.plotly_chart(fig_mes, use_container_width=True)

            html_buffer.write(pio.to_html(fig_mes, include_plotlyjs='cdn', full_html=False))
            export_dict["Mes_Actual"] = df_total_mes

    st.subheader("🔮 Becas ISA – Futuro (Años posteriores a hoy)")
    html_buffer.write("<h2>🔮 Becas ISA – Futuro (Años posteriores a hoy)</h2>")
    columnas_futuras = [col for col in df_beca.columns if col.startswith('Total ') and col.split()[1].isdigit() and int(col.split()[1]) > año_actual]
    seleccion_futuro = st.multiselect("Selecciona los años futuros:", columnas_futuras, default=columnas_futuras, key="filtro_becas_isa_futuro")

    if seleccion_futuro:
        df_beca[seleccion_futuro] = df_beca[seleccion_futuro].apply(pd.to_numeric, errors="coerce")
        suma_futuro = df_beca[seleccion_futuro].sum().reset_index()
        suma_futuro.columns = ['Año', 'Suma Total']
        suma_futuro['Año'] = suma_futuro['Año'].str.replace("Total ", "")
        total_futuro = suma_futuro['Suma Total'].sum()
        df_total_futuro = suma_futuro.copy()
        df_total_futuro.loc[len(df_total_futuro)] = ['TOTAL GENERAL', total_futuro]

        st.markdown(f"### 📄 Suma total por año – 🧮 Total acumulado: `{total_futuro:,.2f} €`")
        st.dataframe(df_total_futuro, use_container_width=True)

        html_buffer.write(f"<p><strong>Total futuro acumulado: {total_futuro:,.2f} €</strong></p>")
        html_buffer.write(df_total_futuro.to_html(index=False))

        fig_futuro = px.line(suma_futuro, x="Año", y="Suma Total", markers=True, title="Becas ISA Futuro")
        fig_futuro.update_layout(template="plotly")
        st.plotly_chart(fig_futuro, use_container_width=True)

        html_buffer.write(pio.to_html(fig_futuro, include_plotlyjs='cdn', full_html=False))
        export_dict["Futuro"] = df_total_futuro

    st.session_state["descarga_becas_isa"] = export_dict

    # EXCEL
    if export_dict:
        buffer_excel = io.BytesIO()
        with pd.ExcelWriter(buffer_excel, engine="xlsxwriter") as writer:
            for name, df_exp in export_dict.items():
                df_exp.to_excel(writer, index=False, sheet_name=name[:31])
        buffer_excel.seek(0)
        st.download_button(
            label="📥 Descargar Excel Consolidado Becas ISA",
            data=buffer_excel.getvalue(),
            file_name="becas_isa_consolidado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # HTML
    st.download_button(
        label="🌐 Descargar informe HTML Becas ISA",
        data=html_buffer.getvalue().encode("utf-8"),
        file_name="becas_isa_informe.html",
        mime="text/html"
    )

     # Guardar el HTML para el informe consolidado
    st.session_state["html_becas_isa"] = html_buffer.getvalue()

    # Guardar archivo HTML en carpeta para consolidado
    import os
    os.makedirs("uploaded", exist_ok=True)
    with open("uploaded/reporte_becas_isa.html", "w", encoding="utf-8") as f:
        f.write(html_buffer.getvalue())
