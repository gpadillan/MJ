# app.py
import importlib
import streamlit as st
from auth import login_page
from sidebar import show_sidebar

# ===================== Inicialización de sesión =====================
DEFAULTS = {
    "logged_in": False,
    "username": "",
    "role": "viewer",
    "current_page": "Inicio",
    "excel_uploaded": False,
    "excel_filename": "",
    "excel_data": None,
    "upload_time": None,
    "unidad": "EIP",  # EIP / EIM / Mainjobs B2C
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Mantener memoria del ámbito anterior para detectar cambios
if "_unidad_prev" not in st.session_state:
    st.session_state["_unidad_prev"] = st.session_state["unidad"]

# ===================== Config de página =====================
st.set_page_config(
    page_title="Sistema de Gestión",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed" if not st.session_state["logged_in"] else "expanded",
)

# ===================== Estilos =====================
def add_custom_css():
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] { display: none !important; }
        .main-header {
            text-align: center; padding: 1.5rem; background-color: #f0f2f6;
            border-radius: 10px; margin-bottom: 2rem;
        }
        .card {
            padding: 1.5rem; border-radius: 10px; background-color: #f8f9fa;
            box-shadow: 0 0.25rem 0.75rem rgba(0,0,0,0.05); margin-bottom: 1rem;
        }
        .sidebar .sidebar-content { background-color: #f8f9fa; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state["logged_in"]:
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"],
            section[data-testid="stSidebarUserContent"] { display: none !important; }
            </style>
            """,
            unsafe_allow_html=True,
        )

# ===================== Router =====================
# ---- Rutas para EIP (/pages) ----
ROUTES_EIP = {
    "Inicio": ("pages.inicio", "inicio_page"),
    "Admisiones": ("pages.admisiones.main_admisiones", "app"),
    "Academica": ("pages.academica.academica_main", "academica_page"),
    "Desarrollo": ("pages.desarrollo_main", "desarrollo_page"),
    "Gestión de Cobro": ("pages.deuda_main", "deuda_page"),
    "Principal": ("pages.principal", "principal_page"),
}

# ---- Rutas para EIM (/pagesEIM) ----
ROUTES_EIM = {
    "Inicio": ("pagesEIM.inicio", "inicio_page"),
    "Admisiones": ("pagesEIM.admisiones.main_admisiones", "app"),
    "Gestión de Cobro": ("pagesEIM.deuda_main", "deuda_page"),
    "Principal": ("pagesEIM.principal", "principal_page"),
}

# ---- Rutas para Mainjobs B2C (/pagesB2C) ----
ROUTES_B2C = {
    "Principal": ("pagesB2C.principal", "principal_page"),
}

def _get_routes_for_unidad(unidad: str):
    if unidad == "EIP":
        return ROUTES_EIP
    if unidad == "EIM":
        return ROUTES_EIM
    if unidad == "Mainjobs B2C":
        return ROUTES_B2C
    return ROUTES_EIP

def route_page():
    unidad = st.session_state.get("unidad", "EIP")
    page = st.session_state.get("current_page", "Inicio")
    routes = _get_routes_for_unidad(unidad)

    if page not in routes:
        st.session_state["current_page"] = list(routes.keys())[0]
        page = st.session_state["current_page"]

    module_path, func_name = routes.get(page, (None, None))
    if not module_path:
        st.title(f"{page} · {unidad}")
        st.info("Ruta no definida para esta página.")
        return

    try:
        mod = importlib.import_module(module_path)
    except ModuleNotFoundError:
        st.title(f"{page} · {unidad}")
        st.info("Esta sección para el ámbito seleccionado aún no existe.")
        return

    fn = getattr(mod, func_name, None)
    if fn is None:
        st.title(f"{page} · {unidad}")
        st.info(f"La página no define la función `{func_name}()`.")
        return

    st.caption(f"Ámbito activo: **{unidad}**")
    fn()

# ===================== Main =====================
def main():
    add_custom_css()

    if not st.session_state["logged_in"]:
        login_page()
        return

    # Guardamos el ámbito antes de que el sidebar lo pueda cambiar
    prev = st.session_state.get("_unidad_prev", st.session_state["unidad"])

    # Sidebar (selector EIP/EIM/Mainjobs B2C + navegación)
    show_sidebar()

    # Si el usuario cambió el ámbito en el sidebar, hacer rerun inmediato
    if st.session_state["unidad"] != prev:
        st.session_state["_unidad_prev"] = st.session_state["unidad"]

        # (opcional) si entras a B2C fuerza "Principal" para evitar páginas inexistentes
        if st.session_state["unidad"] == "Mainjobs B2C":
            st.session_state["current_page"] = "Principal"

        # Si vuelves a EIP/EIM y estabas en "Principal", ajusta a una válida
        if st.session_state["unidad"] in ("EIP", "EIM") and (
            st.session_state.get("current_page") not in _get_routes_for_unidad(st.session_state["unidad"])
        ):
            st.session_state["current_page"] = "Inicio"

        st.rerun()

    # Router
    route_page()

# ===================== Entry point =====================
if __name__ == "__main__":
    main()