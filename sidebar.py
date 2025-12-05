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


def _nav_button(label: str, page_key: str, primary: bool = False):
    """
    Crea un botón de navegación que cambia st.session_state['current_page'].
    - primary=True => usa el estilo 'primary' de Streamlit (lo sobreescribimos con CSS en EIM)
    """
    btn_type = "primary" if primary else "secondary"
    if st.button(label, use_container_width=True, key=f"nav_{page_key}", type=btn_type):
        st.session_state["current_page"] = page_key
        st.rerun()


def show_sidebar():
    with st.sidebar:
        # Añadimos un borde derecho fino y semitransparente al sidebar.
        # Este borde será la referencia visual/DOM que usará la guirnalda
        # para alinearse exactamente con el final de la zona gris.
        st.markdown(
            """
            <style>
            /* Borde fino y discreto en el borde derecho del sidebar */
            [data-testid="stSidebar"] {
                border-right: 1px solid rgba(0,0,0,0.12) !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

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

        # 🎨 Estilos SOLO para navegación EIM (burdeos + texto blanco)
        if unidad_sel == "EIM":
            st.markdown(
                """
                <style>
                /* Botones 'primary' del sidebar (solo los nav de EIM los marcamos como primary) */
                [data-testid="stSidebar"] .stButton > button[kind="primary"]{
                    background-color: #7B1E3A !important;  /* burdeos */
                    border-color: #7B1E3A !important;
                    color: #ffffff !important;
                }
                [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover{
                    background-color: #6a1932 !important;
                    border-color: #6a1932 !important;
                    color: #ffffff !important;
                }
                [data-testid="stSidebar"] .stButton > button[kind="primary"]:active{
                    background-color: #5c162c !important;
                    border-color: #5c162c !important;
                    color: #ffffff !important;
                }
                [data-testid="stSidebar"] .stButton > button[kind="primary"]:focus{
                    outline: none !important;
                    box-shadow: 0 0 0 0.2rem rgba(123, 30, 58, 0.25) !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

        # 🎨 Estilos SOLO para navegación EIP (más amarillo + letras azules)
        if unidad_sel == "EIP":
            st.markdown(
                """
                <style>
                /* Botones 'secondary' del sidebar (los nav de EIP los marcamos como secondary) */
                [data-testid="stSidebar"] .stButton > button[kind="secondary"]{
                    background-color: #FFD84D !important;   /* amarillo más vivo */
                    border-color: #FFC94A !important;
                    color: #0b5394 !important;               /* azul */
                    font-weight: 700 !important;
                }
                [data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover{
                    background-color: #FFCD1A !important;   /* hover más intenso */
                    border-color: #FFCA28 !important;
                    color: #0b5394 !important;
                }
                [data-testid="stSidebar"] .stButton > button[kind="secondary"]:active{
                    background-color: #FFC107 !important;   /* active */
                    border-color: #FFB300 !important;
                    color: #0b5394 !important;
                }
                [data-testid="stSidebar"] .stButton > button[kind="secondary"]:focus{
                    outline: none !important;
                    box-shadow: 0 0 0 0.2rem rgba(255, 209, 77, 0.5) !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

        # Navegación por ámbito
        if unidad_sel == "Mainjobs B2C":
            st.markdown("### 📂 Navegación B2C")
            _nav_button("Área Principal (B2C)", "Principal", primary=False)

        elif unidad_sel == "EIM":
            st.markdown("### 📂 Navegación EIM")
            # En EIM ocultamos Académica y Empleo (Desarrollo) y pintamos nav como 'primary'
            _nav_button("Área Principal", "Principal", primary=True)
            _nav_button("Área de Admisiones", "Admisiones", primary=True)
            _nav_button("Área Gestión de Cobro", "Gestión de Cobro", primary=True)

        else:  # EIP
            st.markdown("### 📂 Navegación EIP")
            _nav_button("Área Principal", "Principal", primary=False)
            _nav_button("Área de Admisiones", "Admisiones", primary=False)
            _nav_button("Área Académica", "Academica", primary=False)
            _nav_button("Área de Empleo", "Desarrollo", primary=False)
            _nav_button("Área Gestión de Cobro", "Gestión de Cobro", primary=False)

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
