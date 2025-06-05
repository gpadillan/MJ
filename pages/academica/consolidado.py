import streamlit as st
import pandas as pd

def show_consolidado(data):
    hoja = "CONSOLIDADO ACADÉMICO"
    if hoja not in data:
        st.warning(f"⚠️ No se encontró la hoja '{hoja}'.")
        return

    df = data[hoja]
    st.title("📊 Consolidado Académico EIP")

    # ======== BLOQUE 1: Indicadores Académicos =========
    indicadores = []

    total_alumnos = df.iloc[1, 1]
    indicadores.append(["Alumn@s", total_alumnos, "normal"])

    for i in range(2, 10):
        nombre = str(df.iloc[i, 1]).strip()
        valor = df.iloc[i, 2]

        if pd.notna(nombre) and pd.notna(valor):
            if isinstance(valor, float) and valor <= 1:
                valor = f"{valor:.2%}".replace(".", ",")
            indicadores.append([nombre, valor, "normal"])

    nombre = str(df.iloc[10, 1]).strip()
    valor = df.iloc[10, 2]
    if pd.notna(nombre) and pd.notna(valor):
        if isinstance(valor, float) and valor <= 1:
            valor = f"{valor:.2%}".replace(".", ",")
        indicadores.append([nombre, valor, "normal"])

    nombre = str(df.iloc[11, 1]).strip()
    valor = df.iloc[11, 2]
    if pd.notna(nombre) and pd.notna(valor):
        indicadores.append([nombre, int(valor), "normal"])

    # ======== BLOQUE 2: Certificaciones =========
    total_cert = int(df.iloc[13, 2])
    indicadores.append(["Certificaciones", total_cert, "total_cert"])

    certs = df.iloc[14:27, [1, 2]].dropna()
    for _, row in certs.iterrows():
        indicadores.append([row[0], int(row[1]), "cert_item"])

    # ======== BLOQUE 3: Recobros =========
    recobros = []
    for i in range(1, 5):
        concepto = str(df.iloc[i, 4]).strip()
        valor = df.iloc[i, 5]
        if pd.notna(concepto) and pd.notna(valor):
            if isinstance(valor, (int, float)) and (
                "recobrado" in concepto.lower() or
                "objetivo" in concepto.lower() or
                "€" in concepto.lower()
            ):
                valor = f"{valor:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
            elif isinstance(valor, float) and valor <= 1:
                valor = f"{valor:.2%}".replace(".", ",")
            elif isinstance(valor, float):
                valor = f"{valor:.2f}".replace(".", ",")
            recobros.append([concepto, valor, "normal"])

    # ======== GENERAR HTML =========
    def render_tabla(titulo, filas):
        html = f"""
        <style>
            .tabla-custom {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 2em;
            }}
            .tabla-custom th, .tabla-custom td {{
                padding: 0.5em;
                border: 1px solid #ccc;
                text-align: left;
            }}
            .tabla-custom th {{
                background-color: #f0f0f0;
            }}
            .col-master {{
                background-color: #f2f2f2;
                font-weight: bold;
            }}
            .row-cert-total {{
                background-color: #fff3cd;
                font-weight: bold;
            }}
            .row-cert-indiv {{
                background-color: #e3f2fd;
            }}
        </style>
        <h3>{titulo}</h3>
        <table class="tabla-custom">
            <thead>
                <tr>
                    <th>Indicador</th><th>Valor</th>
                </tr>
            </thead>
            <tbody>
        """
        for indicador, valor, tipo in filas:
            clase = ""
            if tipo == "total_cert":
                clase = 'row-cert-total'
            elif tipo == "cert_item":
                clase = 'row-cert-indiv'
            html += f'<tr class="{clase}"><td>{indicador}</td><td>{valor}</td></tr>'
        html += "</tbody></table>"
        return html

    st.markdown(render_tabla("🎓 Indicadores Académicos y Certificaciones", indicadores), unsafe_allow_html=True)
    st.markdown(render_tabla("💰 Recobros EIP", recobros), unsafe_allow_html=True)
