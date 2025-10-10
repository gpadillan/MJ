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


def _nav_button(label: str, page_key: str):
    """
    Crea un botón de navegación que cambia st.session_state['current_page'].
    (El estilo lo aplica el contenedor CSS, no el 'type' del botón).
    """
    if st.button(label, use_container_width=True, key=f"nav_{page_key}"):
        st.session_state["current_page"] = page_key
        st.rerun()


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

        # 🎨 Estilos: NAV EIM (burdeos + blanco) y NAV EIP (amarillo + azul)
        st.markdown(
            """
            <style>
            /* ----- Contenedor de NAV EIM ----- */
            .nav-eim .stButton > button{
                background-color: #7B1E3A !important;   /* burdeos */
                border-color: #7B1E3A !important;
                color: #ffffff !important;               /* blanco */
                font-weight: 700 !important;
            }
            .nav-eim .stButton > button:hover{
                background-color: #6a1932 !important;
                border-color: #6a1932 !important;
                color: #ffffff !important;
            }
            .nav-eim .stButton > button:active{
                background-color: #5c162c !important;
                border-color: #5c162c !important;
                color: #ffffff !important;
            }
            .nav-eim .stButton > button:focus{
                outline: none !important;
                box-shadow: 0 0 0 0.2rem rgba(123, 30, 58, 0.25) !important;
            }

            /* ----- Contenedor de NAV EIP ----- */
            .nav-eip .stButton > button{
                background-color: #FFF6CC !important;    /* amarillo claro */
                border-color: #FFE58F !important;
                color: #0b5394 !important;                /* azul */
                font-weight: 700 !important;
            }
            .nav-eip .stButton > button:hover{
                background-color: #FFEFA3 !important;
                border-color: #FFE083 !important;
                color: #0b5394 !important;
            }
            .nav-eip .stButton > button:active{
                background-color: #FFE076 !important;
                border-color: #FFD34F !important;
                color: #0b5394 !important;
            }
            .nav-eip .stButton > button:focus{
                outline: none !important;
                box-shadow: 0 0 0 0.2rem rgba(255, 229, 143, 0.5) !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # Navegación por ámbito (envuelta en contenedores para aplicar los estilos)
        if unidad_sel == "Mainjobs B2C":
            st.markdown("### 📂 Navegación B2C")
            with st.container():
                _nav_button("Área Principal (B2C)", "Principal")

        elif unidad_sel == "EIM":
            st.markdown("### 📂 Navegación EIM")
            st.markdown('<div class="nav-eim">', unsafe_allow_html=True)
            _nav_button("Área Principal", "Principal")
            _nav_button("Área de Admisiones", "Admisiones")
            _nav_button("Área Gestión de Cobro", "Gestión de Cobro")
            st.markdown("</div>", unsafe_allow_html=True)

        else:  # EIP
            st.markdown("### 📂 Navegación EIP")
            st.markdown('<div class="nav-eip">', unsafe_allow_html=True)
            _nav_button("Área Principal", "Principal")
            _nav_button("Área de Admisiones", "Admisiones")
            _nav_button("Área Académica", "Academica")
            _nav_button("Área de Empleo", "Desarrollo")
            _nav_button("Área Gestión de Cobro", "Gestión de Cobro")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")

        # Recargar / limpiar caché (no afectado por los estilos de navegación)
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

        # Cerrar sesión (no afectado por los estilos de navegación)
        if st.button("🚪 Cerrar Sesión", use_container_width=True, key="logout_btn"):
            st.session_state["logged_in"] = False
            st.session_state["username"] = ""
            st.session_state["excel_data"] = None
            st.session_state["excel_data_eim"] = None
            st.session_state["excel_filename"] = ""
            st.session_state["upload_time"] = None
            st.session_state["current_page"] = "Inicio"
            st.rerun()
