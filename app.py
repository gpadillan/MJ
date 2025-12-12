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
#        🎄 GUIRNALDA CURVADA con BOMBILLAS pegadas a la curva (Opción A)
#        — visible 1 dic .. 7 ene; cambia los emojis según rango
# ===============================================================
def add_garland_follow_curve():
    # fecha local en Madrid si está disponible
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
        return  # fuera de temporada: no añadimos nada

    if in_dec1_to_dec26(today):
        specials = ["🎅", "🎄"]
    else:
        # 27 dic -> 7 ene: los emoticonos solicitados
        specials = ["🤴🏼", "🤴🏽", "🤴🏿", "🐫"]

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
        overflow: visible;
    }}

    .garland-svg {{
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 60px;
        overflow: visible;
        z-index: 1;
    }}

    .garland-items {{
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 110px;
        pointer-events: none;
        z-index: 2;
    }}

    .garland-item {{
        position: absolute;
        transform: translate(-50%, -10%);
        pointer-events: none;
        z-index: 3;
    }}

    .garland-item .bulb {{
        width: var(--bulb-size);
        height: calc(var(--bulb-size) * 1.9);
        border-radius: 50% 50% 40% 40%;
        position: relative;
        opacity: .55;
        transition: opacity 0.3s ease, filter 0.3s ease;
        z-index: 4;
        display: inline-block;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06), inset 0 -6px 12px rgba(0,0,0,0.02);
    }}
    .garland-item .bulb.on {{
        opacity: 1;
        filter: drop-shadow(0 6px 18px rgba(255,220,140,0.12));
    }}

    .garland-item .bulb::before {{
        content: "";
        position: absolute;
        top: -6px;
        left: 50%;
        transform: translateX(-50%);
        width: calc(var(--bulb-size) * 0.9);
        height: 6px;
        background: linear-gradient(180deg, #6b6b6b, #3b3b3b);
        border-radius: 3px;
        z-index: 6;
    }}

    .c1 {{ background: linear-gradient(180deg,#FFE88A,#FFD84D); box-shadow:0 4px 14px rgba(255,215,77,0.22); }}
    .c2 {{ background: linear-gradient(180deg,#90CFFF,#4DA6FF); box-shadow:0 4px 14px rgba(77,166,255,0.16); }}
    .c3 {{ background: linear-gradient(180deg,#FFB2B2,#FF6F6F); box-shadow:0 4px 14px rgba(255,111,111,0.12); }}
    .c4 {{ background: linear-gradient(180deg,#BFEFB0,#90DE7B); box-shadow:0 4px 14px rgba(144,222,123,0.10); }}
    .c5 {{ background: linear-gradient(180deg,#E2B6FF,#C16BFF); box-shadow:0 4px 14px rgba(193,107,255,0.12); }}

    .special {{
        font-size: 25px;
        line-height: 1;
        transform: translate(-50%, -6%);
        z-index: 5;
    }}

    @media (max-width: 900px) {{
        .garland-wrap {{ display: none !important; }}
    }}
    </style>

    <div class="garland-wrap">
        <svg id="garlandSVG" class="garland-svg" preserveAspectRatio="none" viewBox="0 0 1600 60" width="100%" height="60">
            <path id="garlandPath" d="M0 30 Q 80 10, 160 30 T 320 30 T 480 30 T 640 30 T 800 30 T 960 30 T 1120 30 T 1280 30 T 1440 30 T 1600 30"
                stroke="rgba(70,70,70,0.5)" stroke-width="4" stroke-linecap="round" fill="transparent"/>
        </svg>

        <div id="garlandItems" class="garland-items"></div>
    </div>

    <script>
    (function(){{
        function buildGarlandAlongPath() {{
            const itemsContainer = document.getElementById("garlandItems");
            const svg = document.getElementById("garlandSVG");
            const path = document.getElementById("garlandPath");
            const parentDoc = window.parent.document;
            const sidebar = parentDoc.querySelector('[data-testid="stSidebar"]');

            const bulbSize = 12;
            const gap = 9;
            const unit = bulbSize + gap;

            let leftPx = 260;
            if (sidebar) {{
                const rect = sidebar.getBoundingClientRect();
                const cs = window.parent.getComputedStyle(sidebar);
                const borderRight = parseFloat(cs.borderRightWidth) || 0;
                const innerEdge = rect.right - borderRight;
                leftPx = Math.round(innerEdge - (bulbSize / 2) - 320);
            }}

            const svgRect = svg.getBoundingClientRect();
            const viewBoxWidth = 1600;
            const scale = svgRect.width / viewBoxWidth;
            const pathLen = path.getTotalLength();

            const startRatio = Math.max(0, Math.min(1, (leftPx - svgRect.left) / svgRect.width));
            const startLen = startRatio * pathLen;

            const totalWidth = window.parent.innerWidth;
            const availablePx = Math.max(0, totalWidth - leftPx - 40);

            const approxCount = Math.max(0, Math.floor(availablePx / unit));
            const totalUnits = approxCount;

            if (totalUnits <= 0) {{
                itemsContainer.innerHTML = "";
                return;
            }}

            const availableLenOnPath = (availablePx / svgRect.width) * pathLen;
            const stepLen = totalUnits > 1 ? availableLenOnPath / (totalUnits - 1) : availableLenOnPath;

            itemsContainer.innerHTML = "";

            const colors = ["c1","c2","c3","c4","c5"];
            const specials = {specials_js};
            let bulbCount = 0;
            let specIndex = 0;

            let placed = 0;
            let i = 0;
            while (placed < totalUnits) {{
                for (let b_i = 0; b_i < 10 && placed < totalUnits; b_i++) {{
                    const curLen = startLen + i * stepLen;
                    const pt = path.getPointAtLength(curLen);
                    const screenX = svgRect.left + pt.x * scale;
                    const screenY = svgRect.top + pt.y * scale;
                    const contRect = itemsContainer.getBoundingClientRect();
                    const relX = screenX - contRect.left;
                    const relY = screenY - contRect.top;

                    const el = document.createElement("div");
                    el.className = "garland-item";
                    el.style.left = relX + "px";
                    el.style.top = (relY + 2) + "px";

                    const bulb = document.createElement("span");
                    const cls = colors[bulbCount % colors.length];
                    bulb.className = "bulb " + cls;
                    bulb.dataset.delay = Math.floor(Math.random() * 1600);
                    el.appendChild(bulb);
                    itemsContainer.appendChild(el);

                    bulbCount++;
                    i++;
                    placed++;
                }}

                if (placed < totalUnits) {{
                    const curLen = startLen + i * stepLen;
                    const pt = path.getPointAtLength(curLen);
                    const screenX = svgRect.left + pt.x * scale;
                    const screenY = svgRect.top + pt.y * scale;
                    const contRect = itemsContainer.getBoundingClientRect();
                    const relX = screenX - contRect.left;
                    const relY = screenY - contRect.top;

                    const el = document.createElement("div");
                    el.className = "garland-item special";
                    el.style.left = relX + "px";
                    el.style.top = (relY + 12) + "px";
                    el.textContent = specials[specIndex % specials.length];
                    itemsContainer.appendChild(el);

                    specIndex++;
                    i++;
                    placed++;
                }}
            }}

            function animateBulbs() {{
                const bulbs = Array.from(itemsContainer.querySelectorAll(".bulb"));
                bulbs.forEach((b) => {{
                    const baseDelay = parseInt(b.dataset.delay || "0", 10);
                    setTimeout(function pulseOnce(){{
                        b.classList.add("on");
                        setTimeout(()=> b.classList.remove("on"), 400 + Math.random() * 800);
                        const next = 900 + Math.random() * 3000;
                        setTimeout(pulseOnce, next);
                    }}, baseDelay + Math.random() * 500);
                }});
            }}
            setTimeout(animateBulbs, 220);
        }}

        setTimeout(buildGarlandAlongPath, 250);
        let t;
        window.addEventListener("resize", function(){{ clearTimeout(t); t = setTimeout(buildGarlandAlongPath, 140); }});
    }})();
    </script>
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

    module_path, func_name = routes.get(page, (None, None))

    try:
        importlib.invalidate_caches()
        mod = importlib.import_module(module_path)
    except Exception as e:
        st.title(f"{page} · {unidad}")
        st.exception(e)
        return

    fn = getattr(mod, func_name, None)
    if fn is None:
        st.title(f"{page} · {unidad}")
        st.write("La página no define la función requerida.")
        return

    st.caption(f"Ámbito activo: **{unidad}**")
    fn()

# ===============================================================
#                            MAIN
# ===============================================================
def main():

    add_custom_css()

    # --- BLOQUEO PERMANENTE POR REFORMAS ---
    # A partir del 15 de diciembre a las 12:00 (hora Madrid) la app queda BLOQUEADA.
    # La app no volverá a abrirse automáticamente después de esa fecha/hora.
    # Para restablecer el acceso hay que editar o eliminar este bloque en el código.
    if TZ_MADRID is not None:
        now = datetime.now(TZ_MADRID)
    else:
        now = datetime.utcnow()

    inicio_bloqueo = now.replace(month=12, day=15, hour=12, minute=0, second=0, microsecond=0)

    if now >= inicio_bloqueo:
        st.title("Cierre por reformas de Streamlit")
        st.error(
            "La aplicación está temporalmente cerrada por reformas de Streamlit.\n\n"
            "Disculpa las molestias."
        )
        st.stop()

    if not st.session_state["logged_in"]:
        login_page()
        return

    prev = st.session_state["_unidad_prev"]

    show_sidebar()

    # 🎄 Activamos la guirnalda curva con bulbs pegadas a la línea
    add_garland_follow_curve()

    if st.session_state["unidad"] != prev:
        st.session_state["_unidad_prev"] = st.session_state["unidad"]
        st.rerun()

    route_page()

if __name__ == "__main__":
    main()
