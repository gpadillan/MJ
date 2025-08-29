# sidebar.py
import streamlit as st

def show_sidebar():
    with st.sidebar:
        # --- Cabecera ---
        username = st.session_state.get("username", "admin")
        st.markdown(f"### 👋 Bienvenido, {username}")

        # --- Selector de ámbito (EIP / EIM) ---
        # Se guarda en st.session_state["unidad"] para que las páginas lo lean.
        unidad_actual = st.session_state.get("unidad", "EIP")
        st.session_state["unidad"] = st.radio(
            "Ámbito",
            options=["EIP", "EIM"],
            index=0 if unidad_actual == "EIP" else 1,
            horizontal=True,
            key="radio_ambito",
        )
        st.caption(f"Ámbito activo: **{st.session_state['unidad']}**")

        st.markdown("---")

        # --- Navegación (misma para ambos ámbitos, solo cambia el contenido en las páginas) ---
        st.markdown("### 📂 Navegación")
        nav_items = {
            "Área Principal": "Principal",
            "Área de Admisiones": "Admisiones",
            "Área Académica": "Academica",
            "Área de Empleo": "Desarrollo",
            "Área Gestión de Cobro": "Gestión de Cobro",
        }

        for label, page_key in nav_items.items():
            if st.button(label, use_container_width=True, key=f"nav_{page_key}"):
                st.session_state["current_page"] = page_key
                st.rerun()

        st.markdown("---")

        # --- (Opcional) Recargar / limpiar caché global ---
        if st.button("🔄 Recargar / limpiar caché", use_container_width=True, key="reload_cache"):
            for k in [
                "academica_excel_data",
                "excel_data",
                "df_ventas",
                "df_preventas",
                "df_gestion",
                "df_empleo_informe",
            ]:
                if k in st.session_state:
                    del st.session_state[k]
            st.cache_data.clear()
            st.cache_resource.clear()
            st.success("Caché limpiada. Volviendo a cargar…")
            st.rerun()

        # --- Cerrar sesión ---
        if st.button("🚪 Cerrar Sesión", use_container_width=True, key="logout_btn"):
            st.session_state["logged_in"] = False
            st.session_state["username"] = ""
            st.session_state["excel_data"] = None
            st.session_state["excel_filename"] = ""
            st.session_state["upload_time"] = None
            st.session_state["current_page"] = "Inicio"
            st.rerun()
