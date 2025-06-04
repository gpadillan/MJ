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

    for i in range(len(df_raw)):
        nombre = str(df_raw.iloc[i, 0]).strip()
        valor = df_raw.iloc[i, 1]

        if not nombre or nombre.lower() == "nan":
            continue

        nombre_lower = normalizar(nombre)

        if "certificaciones" in nombre_lower:
            in_cert_block = True
            continue

        if in_cert_block:
            if isinstance(valor, (int, float)) and not pd.isna(valor):
                certificaciones.append((nombre, int(valor)))
            continue

        if isinstance(valor, (int, float)) and valor <= 1 and any(p in nombre_lower for p in [
            "cumplimiento", "exito academico", "satisfaccion", "riesgo",
            "absentismo", "cierre expediente", "resenas"
        ]):
            valor = f"{valor:.2%}".replace(".", ",")

        indicadores.append((nombre, valor))

    # Insertar total certificaciones justo debajo de "Reclamaciones"
    total_cert = sum([v for _, v in certificaciones if isinstance(v, int)])
    pos_reclamaciones = next((i for i, (n, _) in enumerate(indicadores) if normalizar(n) == "reclamaciones"), -1)
    if pos_reclamaciones != -1:
        indicadores.insert(pos_reclamaciones + 1, ("Certificaciones", total_cert))

    # Añadir certificaciones individuales después de total
    for cert in certificaciones:
        indicadores.append(cert)

    return pd.DataFrame(indicadores, columns=["Indicador", "Valor"])

def mostrar_bloque(titulo, bloque):
    df_ind = formatear_tabla(bloque)
    st.markdown(f"### 🎓 {titulo}")

    rows_html = ""
    cert_mode = False
    for indicador, valor in df_ind.values:
        clase = ""
        if normalizar(indicador) == "certificaciones":
            clase = 'row-cert-total'
            cert_mode = True
        elif cert_mode:
            clase = 'row-cert-indiv'
        row = f'<tr class="{clase}"><td class="col-master">{titulo}</td><td>{indicador}</td><td>{valor}</td></tr>'
        rows_html += row

    tabla_html = f"""
    <style>
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
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 0.5em;
            border: 1px solid #ccc;
            text-align: left;
        }}
    </style>
    <table>
        <thead>
            <tr>
                <th>Máster/Certificación</th>
                <th>Indicador</th>
                <th>Valor</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    """
    st.markdown(tabla_html, unsafe_allow_html=True)

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

    st.markdown("### 🔍 Selecciona un programa para visualizar:")
    opciones = ["Todos"] + [titulo for titulo, _ in bloques_finales]
    seleccion = st.radio("", opciones, horizontal=True)

    if seleccion == "Todos":
        col1, col2 = st.columns(2)
        mitad = (len(bloques_finales) + 1) // 2
        for titulo, bloque in bloques_finales[:mitad]:
            with col1:
                mostrar_bloque(titulo, bloque)
        for titulo, bloque in bloques_finales[mitad:]:
            with col2:
                mostrar_bloque(titulo, bloque)
    else:
        for titulo, bloque in bloques_finales:
            if titulo == seleccion:
                mostrar_bloque(titulo, bloque)
                break
