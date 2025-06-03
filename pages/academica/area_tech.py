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
                certificaciones.append([nombre, int(valor)])
            continue

        if isinstance(valor, (int, float)) and any(p in nombre_lower for p in [
            "cumplimiento", "exito academico", "satisfaccion",
            "riesgo", "absentismo", "cierre expediente", "resenas"
        ]) and valor <= 1:
            valor = f"{valor:.2%}".replace(".", ",")

        indicadores.append([nombre, valor])

    df_ind = pd.DataFrame(indicadores, columns=["Indicador", "Valor"])
    df_cert = pd.DataFrame(certificaciones, columns=["Certificación", "Cantidad"])
    df_cert = df_cert[df_cert["Cantidad"] > 0]

    return df_ind, df_cert

def mostrar_bloque(titulo, bloque):
    st.markdown(f"#### 🎓 {titulo}")
    df_ind, df_cert = formatear_tabla(bloque)

    st.markdown("**📊 Indicadores:**")
    st.dataframe(df_ind, use_container_width=True, hide_index=True)

    if not df_cert.empty:
        total_cert = df_cert["Cantidad"].sum()
        st.markdown(f"**📜 Certificaciones: {total_cert}**")
        st.dataframe(df_cert, use_container_width=True, hide_index=True)

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

        # Detectar inicio del bloque (buscar palabra clave)
        inicio_idx = col_main[col_main.str.contains("Máster|Certificación", case=False)].index
        if len(inicio_idx) == 0:
            continue
        inicio = inicio_idx[0]

        # Determinar el final del bloque (primera fila vacía)
        fin = inicio
        while fin < len(col_main) and not (
            all(x == "" for x in [col_main[fin], str(col_next[fin])])
        ):
            fin += 1

        bloque = df.iloc[inicio:fin, [col_idx, col_idx + 1]].reset_index(drop=True)

        # Buscar título explorando más celdas: filas -2 a +5 y columnas col_idx±2
        titulo = None
        for fila in range(max(0, inicio - 2), min(inicio + 6, df.shape[0])):
            for col in range(max(0, col_idx - 2), min(df.shape[1], col_idx + 3)):
                celda = str(df.iat[fila, col])
                if "máster" in celda.lower() or "certificación" in celda.lower():
                    titulo = celda.replace(":", "").strip()
                    break
            if titulo:
                break

        if not titulo:
            titulo = f"Bloque sin título (fila {inicio}, col {col_idx})"

        bloques_finales.append((titulo, bloque))

    opciones = ["Todos"] + [titulo for titulo, _ in bloques_finales]

    st.markdown("### 🔍 Selecciona un programa para visualizar:")
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
