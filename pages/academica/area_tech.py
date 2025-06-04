import streamlit as st
import pandas as pd
import unicodedata

def normalizar(texto):
    if not isinstance(texto, str):
        return ""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8").lower().strip()

def formatear_tabla(df_raw):
    indicadores = []
    certificaciones = []
    in_cert_block = False
    solo_certificaciones = True

    for i in range(len(df_raw)):
        nombre = str(df_raw.iloc[i, 0]).strip()
        valor = df_raw.iloc[i, 1]

        if not nombre or nombre.lower() == "nan":
            continue

        nombre_lower = normalizar(nombre)

        if "certificaciones" in nombre_lower:
            in_cert_block = True
            continue

        if any(p in nombre_lower for p in [
            "cumplimiento", "exito", "satisfaccion", "riesgo",
            "absentismo", "expediente", "resenas", "alumn", "reclamaciones"
        ]):
            solo_certificaciones = False

        if in_cert_block:
            if isinstance(valor, (int, float)) and not pd.isna(valor):
                certificaciones.append([nombre, int(valor)])
            continue

        if isinstance(valor, (int, float)) and valor <= 1 and any(p in nombre_lower for p in [
            "cumplimiento", "exito academico", "satisfaccion",
            "riesgo", "absentismo", "cierre expediente", "resenas"
        ]):
            valor = f"{valor:.2%}".replace(".", ",")

        indicadores.append([nombre, valor])

    df_ind = pd.DataFrame(indicadores, columns=["Indicador", "Valor"])
    df_cert = pd.DataFrame(certificaciones, columns=["Indicador", "Valor"])

    if solo_certificaciones and df_ind.empty and not df_cert.empty:
        return pd.DataFrame(), df_cert

    return df_ind, df_cert

def mostrar_bloque_con_titulo(titulo, bloque):
    df_ind, df_cert = formatear_tabla(bloque)

    if df_ind.empty and df_cert.empty:
        return

    bloques = [df_ind]

    if not df_cert.empty:
        suma_cert = df_cert["Valor"].sum()
        resumen = pd.DataFrame([["Certificaciones", suma_cert]], columns=["Indicador", "Valor"])
        bloques.append(resumen)
        bloques.append(df_cert)

    df_total = pd.concat(bloques, ignore_index=True)

    st.markdown(f"#### 🎓 {titulo}")
    st.markdown("**📊 Indicadores y Certificaciones:**")

    html = """
    <style>
        .styled-table {
            width: 100%;
            border-collapse: collapse;
            font-family: sans-serif;
        }
        .styled-table th {
            background-color: #f2f2f2;
            text-align: left;
            padding: 10px;
        }
        .styled-table td {
            padding: 10px;
        }
        .col-master {
            background-color: #f2f2f2;
        }
        .row-cert-total {
            background-color: #fff3cd;
            font-weight: bold;
        }
        .row-cert-indiv {
            background-color: #e1f5fe;
        }
    </style>
    <table class="styled-table">
        <thead>
            <tr>
                <th class="col-master">Máster / Certificación</th>
                <th>Indicador</th>
                <th>Valor</th>
            </tr>
        </thead>
        <tbody>
    """

    cert_mode = False
    for i, row in df_total.iterrows():
        indicador = str(row["Indicador"])
        valor = row["Valor"]

        if indicador.lower() == "certificaciones":
            clase_fila = "row-cert-total"
            cert_mode = True
        elif cert_mode:
            clase_fila = "row-cert-indiv"
        else:
            clase_fila = ""

        html += f"""
            <tr class="{clase_fila}">
                <td class="col-master">{titulo}</td>
                <td>{indicador}</td>
                <td>{valor}</td>
            </tr>
        """

    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)

def show_area_tech(data):
    hoja = "ÁREA TECH"
    if hoja not in data:
        st.warning("⚠️ No se encontró la hoja 'ÁREA TECH'.")
        return

    df = data[hoja]
    st.title("🤖 Indicadores Área TECH")

    columnas_masters = list(range(1, df.shape[1], 3))
    bloques_finales = []

    for col_idx in columnas_masters:
        col_main = df.iloc[:, col_idx].fillna("").astype(str)
        col_next = df.iloc[:, col_idx + 1].fillna("")

        bloque_indices = col_main[col_main.str.contains("máster|master|certificación|certificacion", case=False, na=False)].index.tolist()

        for inicio in bloque_indices:
            fin = inicio
            while fin < len(col_main) and not (
                all(x == "" for x in [col_main[fin], str(col_next[fin])])
            ):
                fin += 1

            bloque = df.iloc[inicio:fin, [col_idx, col_idx + 1]].reset_index(drop=True)

            titulo = None
            for fila in range(max(0, inicio - 2), min(inicio + 6, df.shape[0])):
                for col in range(max(0, col_idx - 2), min(df.shape[1], col_idx + 3)):
                    celda = str(df.iat[fila, col])
                    if any(palabra in celda.lower() for palabra in ["máster", "master", "certificación", "certificacion"]):
                        titulo = celda.replace(":", "").strip()
                        break
                if titulo:
                    break

            if not titulo:
                titulo = f"Bloque sin título (fila {inicio}, col {col_idx})"

            bloques_finales.append((titulo, bloque))

    bloques_finales = [
        (titulo, bloque)
        for titulo, bloque in bloques_finales
        if normalizar(titulo) != "certificaciones"
    ]

    opciones = ["Todos"] + [titulo for titulo, _ in bloques_finales]

    st.markdown("### 🔍 Selecciona un programa para visualizar:")
    seleccion = st.radio("", opciones, horizontal=True)

    if seleccion == "Todos":
        col1, col2 = st.columns(2)
        mitad = (len(bloques_finales) + 1) // 2
        for titulo, bloque in bloques_finales[:mitad]:
            with col1:
                mostrar_bloque_con_titulo(titulo, bloque)
        for titulo, bloque in bloques_finales[mitad:]:
            with col2:
                mostrar_bloque_con_titulo(titulo, bloque)
    else:
        for titulo, bloque in bloques_finales:
            if titulo == seleccion:
                mostrar_bloque_con_titulo(titulo, bloque)
                break
