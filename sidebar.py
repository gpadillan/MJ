# sidebar.py
import os
import streamlit as st

# --- Opcional: cachear carga de imágenes ---
@st.cache_resource
def _logo_path(unidad: str) -> str:
    """
    Devuelve la ruta del logo según la unidad (EIP/EIM).
    Si no existe, cae al logo general de assets/grupo-mainjobs.png.
    """
    base = "assets"
    candidates = {
        "EIP": os.path.join(base, "logo_eip.png"),
        "EIM": os.path.join(base, "logo_eim.png"),
    }
    fallback = os.path.join(base, "grupo-mainjobs.png")
    path = candidates.get(unidad.upper(), fallback)
    return path if os.path.exists(path) else fallback

def show_sidebar():
    with st.sidebar:
        # --- Cabecera ---
        username = st.session_state.get("username", "admin")
        st.markdown(f"### 👋 Bienvenido, {username}")

        # --- Selector de ámbito (EIP / EIM) ---
        unidad_actual = st.session_state.get("unidad", "EIP")
        st.session_state["unidad"] = st.radio(
            "Ámbito",
            options=["EIP", "EIM"],
            index=0 if unidad_actual == "EIP" else 1,
            horizontal=True,
            key="radio_ambito",
        )

        # --- Logo según ámbito ---
        logo = _logo_path(st.session_state["unidad"])
        # centrado y tamaño agradable
        st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
        st.image(logo, width=160)
        st.caption(f"Ámbito activo: **{st.session_state['unidad']}**")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")

        # --- Navegación ---
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

        # --- Recargar / limpiar caché global ---
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
