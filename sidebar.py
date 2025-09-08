# sidebar.py
import os
import streamlit as st

@st.cache_resource
def _logo_path(unidad: str) -> str:
    """
    Devuelve la ruta del logo según la unidad.
    """
    base = "assets"
    candidates = {
        "EIP": os.path.join(base, "logo_eip.png"),
        "EIM": os.path.join(base, "logo_eim.png"),
        "Mainjobs B2C": os.path.join(base, "grupo-mainjobs.png"),
    }
    fallback = os.path.join(base, "grupo-mainjobs.png")
    path = candidates.get(unidad, fallback)
    return path if os.path.exists(path) else fallback

def show_sidebar():
    with st.sidebar:
        # Cabecera
        username = st.session_state.get("username", "admin")
        st.markdown(f"### 👋 Bienvenido, {username}")

        # Selector de ámbito
        unidad_actual = st.session_state.get("unidad", "EIP")
        options = ["EIP", "EIM", "Mainjobs B2C"]
        idx = options.index(unidad_actual) if unidad_actual in options else 0
        unidad_sel = st.radio(
            "Ámbito",
            options=options,
            index=idx,
            horizontal=True,
            key="radio_ambito",
        )
        st.session_state["unidad"] = unidad_sel

        # Logo según ámbito
        st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
        st.image(_logo_path(unidad_sel), width=170)
        st.caption(f"Ámbito activo: **{unidad_sel}**")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")

        # Navegación por ámbito
        if unidad_sel == "Mainjobs B2C":
            st.markdown("### 📂 Navegación B2C")
            # En B2C solo mostramos el panel principal B2C (suma EIP+EIM)
            if st.button("Área Principal (B2C)", use_container_width=True, key="nav_b2c_principal"):
                st.session_state["current_page"] = "Principal"
                st.rerun()
        else:
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

        # Recargar / limpiar caché
        if st.button("🔄 Recargar / limpiar caché", use_container_width=True, key="reload_cache"):
            for k in [
                "academica_excel_data",
                "excel_data",
                "excel_data_eim",
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

        # Cerrar sesión
        if st.button("🚪 Cerrar Sesión", use_container_width=True, key="logout_btn"):
            st.session_state["logged_in"] = False
            st.session_state["username"] = ""
            st.session_state["excel_data"] = None
            st.session_state["excel_data_eim"] = None
            st.session_state["excel_filename"] = ""
            st.session_state["upload_time"] = None
            st.session_state["current_page"] = "Inicio"
            st.rerun()

