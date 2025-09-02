# app.py
import streamlit as st
import importlib
from auth import login_page
from sidebar import show_sidebar

# ===================== Inicialización de sesión =====================
DEFAULTS = {
    'logged_in': False,
    'username': "",
    'role': "viewer",
    'current_page': "Inicio",
    'excel_uploaded': False,
    'excel_filename': "",
    'excel_data': None,
    'upload_time': None,
    'unidad': "EIP",  # 👈 Selector EIP/EIM controlado desde sidebar
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ===================== Config de página =====================
st.set_page_config(
    page_title="Sistema de Gestión",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed" if not st.session_state['logged_in'] else "expanded"
)

# ===================== Estilos =====================
def add_custom_css():
    st.markdown("""
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
    """, unsafe_allow_html=True)

    if not st.session_state['logged_in']:
        st.markdown("""
        <style>
        [data-testid="stSidebar"],
        section[data-testid="stSidebarUserContent"] { display: none !important; }
        </style>
        """, unsafe_allow_html=True)

# ===================== Router =====================
# ---- Rutas para EIP (tu estructura actual en /pages) ----
ROUTES_EIP = {
    "Inicio":              ("pages.inicio",                    "inicio_page"),
    "Admisiones":          ("pages.admisiones.main_admisiones","app"),
    "Academica":           ("pages.academica.academica_main",  "academica_page"),
    "Desarrollo":          ("pages.desarrollo_main",           "desarrollo_page"),
    "Gestión de Cobro":    ("pages.deuda_main",                "deuda_page"),
    "Principal":           ("pages.principal",                 "principal_page"),
}

# ---- Rutas para EIM (espejo en /pagesEIM con las MISMAS funciones) ----
# Asegúrate de crear:
#   pagesEIM/__init__.py
#   pagesEIM/academica/__init__.py
#   pagesEIM/admisiones/__init__.py
#   pagesEIM/deuda/__init__.py
# y los módulos con las funciones indicadas abajo.
ROUTES_EIM = {
    "Inicio":              ("pagesEIM.inicio",                     "inicio_page"),
    "Admisiones":          ("pagesEIM.admisiones.main_admisiones", "app"),
    "Academica":           ("pagesEIM.academica.academica_main",   "academica_page"),
    "Desarrollo":          ("pagesEIM.desarrollo_main",            "desarrollo_page"),
    "Gestión de Cobro":    ("pagesEIM.deuda_main",                 "deuda_page"),
    "Principal":           ("pagesEIM.principal",                  "principal_page"),
}

def route_page():
    unidad = st.session_state.get("unidad", "EIP")          # "EIP" / "EIM"
    page   = st.session_state.get("current_page", "Inicio") # etiqueta del sidebar
    routes = ROUTES_EIP if unidad == "EIP" else ROUTES_EIM

    module_path, func_name = routes.get(page, (None, None))
    if not module_path:
        st.title(f"{page} · {unidad}")
        st.info("Ruta no definida para esta página.")
        return

    # Carga dinámica del módulo
    try:
        mod = importlib.import_module(module_path)
    except ModuleNotFoundError:
        st.title(f"{page} · {unidad}")
        st.info("Esta sección para el ámbito seleccionado aún no existe.")
        return

    # Obtiene la función a ejecutar
    fn = getattr(mod, func_name, None)
    if fn is None:
        st.title(f"{page} · {unidad}")
        st.info(f"La página no define la función `{func_name}()`.")
        return

    # Etiqueta de ámbito activo visible en cada página
    st.caption(f"Ámbito activo: **{unidad}**")
    fn()

# ===================== Main =====================
def main():
    add_custom_css()

    if not st.session_state['logged_in']:
        login_page()
        return

    # Sidebar (selector EIP/EIM + navegación)
    show_sidebar()

    # Router
    route_page()

# ===================== Entry point =====================
if __name__ == "__main__":
    main()
