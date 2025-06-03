import streamlit as st
import pandas as pd
import unicodedata
import math

def normalizar(texto):
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8").lower()

def formatear_tabla(df_raw):
    datos = []
    cert_valores = []
    cert_index = None
    in_cert_block = False

    for i in range(len(df_raw)):
        nombre = str(df_raw.iloc[i, 0])
        valor = df_raw.iloc[i, 1]

        if nombre.strip().lower() == "nan" or nombre.strip() == "":
            continue

        datos.append([nombre, valor])
        nombre_lower = nombre.lower()

        if "certificaciones:" in nombre_lower:
            cert_index = len(datos) - 1
            in_cert_block = True
            continue

        if in_cert_block and isinstance(valor, (int, float)):
            cert_valores.append(valor)

        if isinstance(valor, (int, float)) and any(p in nombre_lower for p in [
            "cumplimiento", "éxito académico", "satisfacción",
            "riesgo", "absentismo", "cierre expediente", "reseñas"
        ]) and valor <= 1:
            datos[-1][1] = f"{valor:.2%}".replace(".", ",")

    cert_valores = [v for v in cert_valores if pd.notna(v)]

    if cert_index is not None:
        if cert_valores:
            cert_total = int(sum(cert_valores))
            datos[cert_index][1] = cert_total
    elif cert_valores:
        cert_total = int(sum(cert_valores))
        datos.append(["Certificaciones", cert_total])

    return pd.DataFrame(datos, columns=["Indicador", "Valor"])

def encontrar_titulo(df, fila_inicio, col_inicio):
    for fila in range(max(0, fila_inicio - 2), min(fila_inicio + 6, df.shape[0])):
        for col in range(max(0, col_inicio - 2), min(df.shape[1], col_inicio + 3)):
            celda = str(df.iat[fila, col])
            if "máster" in celda.lower():
                return celda.replace(":", "").strip()
    return f"Bloque desde fila {fila_inicio}"

def show_gestion_corporativa(data):
    hoja = "ÁREA GESTIÓN CORPORATIVA"
    if hoja not in data:
        st.warning("⚠️ No se encontró la hoja 'ÁREA GESTIÓN CORPORATIVA'.")
        return

    df = data[hoja]
    st.title("🏢 Indicadores Área Gestión Corporativa")

    col_b = df.iloc[:, 1].fillna("").astype(str)
    col_e = df.iloc[:, 4].fillna("").astype(str)

    norm_b = col_b.map(normalizar).str.strip()
    norm_e = col_e.map(normalizar).str.strip()

    bloques_b = norm_b[norm_b.str.contains("master profesional en")].index.tolist()
    bloques_e = norm_e[norm_e.str.contains("master profesional en")].index.tolist()

    bloques_b.append(len(df))
    bloques_e.append(len(df))

    titulos_b = [encontrar_titulo(df, i, 1) for i in bloques_b[:-1]]
    titulos_e = [encontrar_titulo(df, i, 4) for i in bloques_e[:-1]]

    all_bloques = [(col_b, 1, 2, bloques_b, titulos_b), (col_e, 4, 5, bloques_e, titulos_e)]
    opciones = ["Todos"] + list(dict.fromkeys(titulos_b + titulos_e))  # evita duplicados

    st.markdown("### 🔍 Selecciona un programa para visualizar:")
    seleccion = st.radio("", opciones, horizontal=True)

    if seleccion == "Todos":
        bloques_finales = []

        for columna, col_idx1, col_idx2, indices, titulos in all_bloques:
            for i in range(len(indices) - 1):
                inicio, fin = indices[i], indices[i + 1]
                bloque = df.iloc[inicio:fin, [col_idx1, col_idx2]].reset_index(drop=True)
                titulo = titulos[i]
                bloques_finales.append((titulo, bloque))

        mitad = math.ceil(len(bloques_finales) / 2)
        col1, col2 = st.columns(2)

        for titulo, bloque in bloques_finales[:mitad]:
            with col1:
                st.markdown(f"#### 📘 {titulo}")
                st.dataframe(formatear_tabla(bloque), use_container_width=True, hide_index=True)

        for titulo, bloque in bloques_finales[mitad:]:
            with col2:
                st.markdown(f"#### 📘 {titulo}")
                st.dataframe(formatear_tabla(bloque), use_container_width=True, hide_index=True)

    else:
        for columna, col_idx1, col_idx2, indices, titulos in all_bloques:
            if seleccion in titulos:
                idx = titulos.index(seleccion)
                inicio, fin = indices[idx], indices[idx + 1]
                bloque = df.iloc[inicio:fin, [col_idx1, col_idx2]].reset_index(drop=True)
                st.markdown(f"#### 📘 {seleccion}")
                st.dataframe(formatear_tabla(bloque), use_container_width=True, hide_index=True)
                break
