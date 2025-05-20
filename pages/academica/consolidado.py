import streamlit as st
import pandas as pd

def show_consolidado(data):
    hoja = "CONSOLIDADO ACADÉMICO"
    if hoja not in data:
        st.warning(f"⚠️ No se encontró la hoja '{hoja}'.")
        return

    df = data[hoja]
    st.title("📊 Consolidado Académico EIP")

    # ========== BLOQUE 1 + BLOQUE 3 en columnas ==========
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 🎓 Indicadores Académicos")

        data_consolidado = []

        # Total alumnos
        total_alumnos = df.iloc[1, 1]
        data_consolidado.append(["Alumnos/as", int(total_alumnos)])

        # Indicadores generales (filas 2 a 9)
        for i in range(2, 10):
            nombre = str(df.iloc[i, 1])
            valor = df.iloc[i, 2]

            if pd.notna(nombre) and pd.notna(valor):
                # Mostrar como porcentaje si incluye "cumplimiento" y valor numérico <= 1
                if ("cumplimiento" in nombre.lower()) and isinstance(valor, (int, float)) and valor <= 1:
                    valor = f"{valor:.0%}".replace(".", ",")
                elif isinstance(valor, float) and valor <= 1:
                    valor = f"{valor:.2%}".replace(".", ",")
                data_consolidado.append([nombre, valor])

        # Recomendación docente
        nombre = str(df.iloc[10, 1])
        valor = df.iloc[10, 2]
        if pd.notna(valor):
            if isinstance(valor, float) and valor <= 1:
                valor = f"{valor:.2%}".replace(".", ",")
            data_consolidado.append([nombre, valor])

        # Reclamaciones
        nombre = str(df.iloc[11, 1])
        valor = df.iloc[11, 2]
        if pd.notna(valor):
            data_consolidado.append([nombre, int(valor)])

        df_consolidado = pd.DataFrame(data_consolidado, columns=["Indicador", "Valor"])
        st.dataframe(df_consolidado, use_container_width=True, hide_index=True)

    with col2:
        st.markdown("### 💰 Recobros EIP")
        data_recobros = []

        for i in range(1, 5):
            concepto = str(df.iloc[i, 4])
            valor = df.iloc[i, 5]

            if pd.notna(concepto) and pd.notna(valor):
                concepto_lower = concepto.lower()
                if isinstance(valor, (int, float)) and (
                    "recobrado" in concepto_lower or
                    "objetivo" in concepto_lower or
                    "€" in concepto_lower
                ):
                    valor = f"{valor:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
                elif isinstance(valor, (int, float)) and valor == int(valor):
                    valor = int(valor)
                data_recobros.append([concepto, valor])

        df_recobros = pd.DataFrame(data_recobros, columns=["Concepto", "Valor"])
        st.dataframe(df_recobros, use_container_width=True, hide_index=True)

    # ========== BLOQUE 2: Certificaciones ==========
    st.markdown("### 🏅 Certificaciones")

    total_cert = int(df.iloc[13, 2])
    st.markdown(f"**Total certificaciones:** {total_cert}")

    certs_df = df.iloc[14:27, [1, 2]].dropna()
    certs_df.columns = ["Certificación", "Cantidad"]
    st.dataframe(certs_df, use_container_width=True, hide_index=True)
