import streamlit as st
import pandas as pd
import unicodedata
import math

def normalizar(texto):
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8").lower()

def es_porcentaje(nombre, valor):
    nombre = normalizar(nombre)
    claves = ["cumplimiento", "exito academico", "satisfaccion", "riesgo", 
              "absentismo", "cierre expediente", "resenas"]
    return any(clave in nombre for clave in claves) and isinstance(valor, (int, float)) and valor <= 1

def formatear_tabla(df_raw):
    datos = []
    cert_valores = []
    cert_index = None
    in_cert_block = False

    for i in range(len(df_raw)):
        nombre, valor = str(df_raw.iloc[i, 0]).strip(), df_raw.iloc[i, 1]

        if not nombre or nombre.lower() == "nan":
            continue

        nombre_lower = normalizar(nombre)
        datos.append([nombre, valor])

        if "certificaciones:" in nombre_lower:
            cert_index = len(datos) - 1
            in_cert_block = True
            continue

        if in_cert_block and isinstance(valor, (int, float)):
            cert_valores.append(valor)

        if es_porcentaje(nombre, valor):
            datos[-1][1] = f"{valor:.2%}".replace(".", ",")

    cert_valores = [v for v in cert_valores if pd.notna(v)]

    if cert_valores:
        cert_total = int(sum(cert_valores))
        if cert_index is not None:
            datos[cert_index][1] = cert_total
        else:
            datos.append(["Certificaciones", cert_total])

    return pd.DataFrame(datos, columns=["Indicador", "Valor"])

def extraer_bloques(df, col_idx):
    col = df.iloc[:, col_idx].fillna("").astype(str)
    norm_col = col.map(normalizar)
    bloques = norm_col[norm_col.str.contains("master profesional en")].index.tolist()
    bloques.append(len(df))

    titulos = []
    for idx in bloques[:-1]:
        titulo = df.iloc[idx, col_idx].strip()
        titulos.append(titulo)

    return (df.iloc[:, col_idx], col_idx, col_idx + 1, bloques, titulos)

def mostrar_bloques(df, all_bloques, seleccion):
    for columna, col1, col2, indices, titulos in all_bloques:
        if seleccion in titulos:
            i = titulos.index(seleccion)
            bloque = df.iloc[indices[i]:indices[i+1], [col1, col2]].reset_index(drop=True)
            st.markdown(f"#### 📘 {seleccion}")
            st.dataframe(formatear_tabla(bloque), use_container_width=True, hide_index=True)
            return

def mostrar_todos(df, all_bloques):
    bloques_finales = []

    for columna, col1, col2, indices, titulos in all_bloques:
        for i in range(len(indices) - 1):
            bloque = df.iloc[indices[i]:indices[i+1], [col1, col2]].reset_index(drop=True)
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

def show_gestion_corporativa(data):
    hoja = "ÁREA GESTIÓN CORPORATIVA"
    if hoja not in data:
        st.warning("⚠️ No se encontró la hoja 'ÁREA GESTIÓN CORPORATIVA'.")
        return

    df = data[hoja]
    st.title("🏢 Indicadores Área Gestión Corporativa")

    bloque_b = extraer_bloques(df, 1)
    bloque_e = extraer_bloques(df, 4)
    all_bloques = [bloque_b, bloque_e]

    opciones = ["Todos"] + bloque_b[4] + bloque_e[4]
    st.markdown("### 🔍 Selecciona un programa para visualizar:")
    seleccion = st.radio("", opciones, horizontal=True)

    if seleccion == "Todos":
        mostrar_todos(df, all_bloques)
    else:
        mostrar_bloques(df, all_bloques, seleccion)
