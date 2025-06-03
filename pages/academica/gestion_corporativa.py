import streamlit as st
import pandas as pd
import unicodedata
import math

# Utilidades
def normalizar(texto):
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8").lower()

def es_porcentaje(valor, nombre):
    return isinstance(valor, (int, float)) and any(p in nombre for p in [
        "cumplimiento", "éxito académico", "satisfacción",
        "riesgo", "absentismo", "cierre expediente", "reseñas"
    ]) and 0 <= valor <= 1

# Procesamiento de tabla
def formatear_tabla(df_raw):
    datos, cert_valores, cert_index = [], [], None
    in_cert_block = False

    for _, fila in df_raw.iterrows():
        nombre = str(fila.iloc[0]).strip()
        valor = fila.iloc[1]

        if not nombre or nombre.lower() == "nan":
            continue

        datos.append([nombre, valor])
        nombre_norm = nombre.lower()

        if "certificaciones:" in nombre_norm:
            cert_index = len(datos) - 1
            in_cert_block = True
            continue

        if in_cert_block and isinstance(valor, (int, float)):
            cert_valores.append(valor)

        if es_porcentaje(valor, nombre_norm):
            datos[-1][1] = f"{valor:.2%}".replace(".", ",")

    cert_valores = [v for v in cert_valores if pd.notna(v)]

    if cert_valores:
        cert_total = int(sum(cert_valores))
        if cert_index is not None:
            datos[cert_index][1] = cert_total
        else:
            datos.append(["Certificaciones", cert_total])

    return pd.DataFrame(datos, columns=["Indicador", "Valor"])

# Extraer bloques y títulos reales
def extraer_bloques(df, col_idx1, col_idx2):
    col_titulo = df.iloc[:, col_idx1].fillna("").astype(str)
    col_valor = df.iloc[:, col_idx2]
    norm = col_titulo.map(normalizar)

    indices = norm[norm.str.contains("master profesional en")].index.tolist()
    indices.append(len(df))

    bloques = []
    for i in range(len(indices) - 1):
        inicio = indices[i] + 1  # Inicia después del título
        fin = indices[i + 1]
        titulo = col_titulo[indices[i]].replace(":", "").strip()
        bloque = df.iloc[inicio:fin, [col_idx1, col_idx2]].reset_index(drop=True)
        bloques.append((titulo, bloque))

    return bloques

# Mostrar en Streamlit
def show_gestion_corporativa(data):
    hoja = "ÁREA GESTIÓN CORPORATIVA"
    if hoja not in data:
        st.warning("⚠️ No se encontró la hoja 'ÁREA GESTIÓN CORPORATIVA'.")
        return

    df = data[hoja]
    st.title("🏢 Indicadores Área Gestión Corporativa")

    # Extraer bloques de columnas B-C y E-F
    bloques_b = extraer_bloques(df, 1, 2)
    bloques_e = extraer_bloques(df, 4, 5)

    opciones = ["Todos"] + [b[0] for b in bloques_b + bloques_e]
    st.markdown("### 🔍 Selecciona un programa para visualizar:")
    seleccion = st.radio("", opciones, horizontal=True)

    def render_bloques(bloques):
        mitad = math.ceil(len(bloques) / 2)
        col1, col2 = st.columns(2)

        for titulo, bloque in bloques[:mitad]:
            with col1:
                st.markdown(f"#### 📘 {titulo}")
                st.dataframe(formatear_tabla(bloque), use_container_width=True, hide_index=True)

        for titulo, bloque in bloques[mitad:]:
            with col2:
                st.markdown(f"#### 📘 {titulo}")
                st.dataframe(formatear_tabla(bloque), use_container_width=True, hide_index=True)

    if seleccion == "Todos":
        render_bloques(bloques_b + bloques_e)
    else:
        for titulo, bloque in bloques_b + bloques_e:
            if seleccion == titulo:
                st.markdown(f"#### 📘 {titulo}")
                st.dataframe(formatear_tabla(bloque), use_container_width=True, hide_index=True)
                break
