# ===============================================================
# app.py — Sistema de Gestión + Guirnalda CURVADA (Opción A: curva suave)
# ===============================================================

import importlib
import json
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
from auth import login_page
from sidebar import show_sidebar

# zona horaria Madrid (fallback si no hay zoneinfo)
try:
    from zoneinfo import ZoneInfo
    TZ_MADRID = ZoneInfo("Europe/Madrid")
except Exception:
    TZ_MADRID = None

# ===============================================================
#                 SESIÓN / ESTADO
# ===============================================================
DEFAULTS = {
    "logged_in": False,
    "username": "",
    "role": "viewer",
    "current_page": "Inicio",
    "excel_uploaded": False,
    "excel_filename": "",
    "excel_data": None,
    "upload_time": None,
    "unidad": "EIP",
}

for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

if "_unidad_prev" not in st.session_state:
    st.session_state["_unidad_prev"] = st.session_state["unidad"]

# ===============================================================
#                     CONFIGURACIÓN PÁGINA
# ===============================================================
st.set_page_config(
    page_title="Sistema de Gestión",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===============================================================
#                   CSS GENERAL OPCIONAL
# ===============================================================
def add_custom_css():
    st.markdown("""
        <style>
        [data-testid="stSidebarNav"] { display: none !important; }
        </style>
    """, unsafe_allow_html=True)

# ===============================================================
#        🎄 GUIRNALDA CURVADA con BOMBILLAS pegadas a la curva
# ===============================================================
def add_garland_follow_curve():
    if TZ_MADRID is not None:
        today = datetime.now(TZ_MADRID).date()
    else:
        today = datetime.utcnow().date()

    def in_dec1_to_dec26(d):
        return d.month == 12 and 1 <= d.day <= 26

    def in_dec27_to_jan7(d):
        return (d.month == 12 and d.day >= 27) or (d.month == 1 and 1 <= d.day <= 7)

    show_guirnalda = in_dec1_to_dec26(today) or in_dec27_to_jan7(today)
    if not show_guirnalda:
        return

    specials = ["🎅", "🎄"] if in_dec1_to_dec26(today) else ["🤴🏼", "🤴🏽", "🤴🏿", "🐫"]
    specials_js = json.dumps(specials)

    html = f"""
    <style>
    :root {{
        --bulb-size: 12px;
        --gap-size: 9px;
        --top-pos: -5px;
    }}
    .garland-wrap {{
        position: fixed;
        top: var(--top-pos);
        left: 0;
        right: 0;
        height: 110px;
        pointer-events: none;
        z-index: 999999;
    }}
    </style>

    <div class="garland-wrap">
        <svg id="garlandSVG" preserveAspectRatio="none" viewBox="0 0 1600 60" width="100%" height="60">
            <path id="garlandPath"
                d="M0 30 Q 80 10, 160 30 T 320 30 T 480 30 T 640 30 T 800 30 T 960 30 T 1120 30 T 1280 30 T 1440 30 T 1600 30"
                stroke="rgba(70,70,70,0.5)" stroke-width="4" fill="transparent"/>
        </svg>
    </div>
    """
    components.html(html, height=110, scrolling=False)

# ===============================================================
#                     SISTEMA DE RUTAS
# ===============================================================
ROUTES_EIP = {
    "Inicio": ("pages.inicio", "inicio_page"),
    "Admisiones": ("pages.admisiones.main_admisiones", "app"),
    "Academica": ("pages.academica.academica_main", "academica_page"),
    "Desarrollo": ("pages.desarrollo_main", "desarrollo_page"),
    "Gestión de Cobro": ("pages.deuda_main", "deuda_page"),
    "Principal": ("pages.principal", "principal_page"),
}

ROUTES_EIM = {
    "Inicio": ("pagesEIM.inicio", "inicio_page"),
    "Admisiones": ("pagesEIM.admisiones.main_admisiones", "app"),
    "Gestión de Cobro": ("pagesEIM.deuda_main", "deuda_page"),
    "Principal": ("pagesEIM.principal", "principal_page"),
}

ROUTES_B2C = {
    "Principal": ("pagesB2C.principal", "principal_page"),
}

def _get_routes(unidad):
    return {
        "EIP": ROUTES_EIP,
        "EIM": ROUTES_EIM,
        "Mainjobs B2C": ROUTES_B2C
    }.get(unidad, ROUTES_EIP)

def route_page():
    unidad = st.session_state.get("unidad", "EIP")
    page = st.session_state.get("current_page", "Inicio")
    routes = _get_routes(unidad)

    if page not in routes:
        st.session_state["current_page"] = list(routes.keys())[0]
        page = st.session_state["current_page"]

    module_path, func_name = routes[page]
    importlib.invalidate_caches()
    mod = importlib.import_module(module_path)
    fn = getattr(mod, func_name)
    st.caption(f"Ámbito activo: **{unidad}**")
    fn()

# ===============================================================
#                            MAIN
# ===============================================================
def main():

    add_custom_css()

    if not st.session_state["logged_in"]:
        login_page()
        return

    prev = st.session_state["_unidad_prev"]

    show_sidebar()
    add_garland_follow_curve()

    if st.session_state["unidad"] != prev:
        st.session_state["_unidad_prev"] = st.session_state["unidad"]
        st.rerun()

    route_page()

if __name__ == "__main__":
    main()
