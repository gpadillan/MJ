# pagesEIM/deuda_main.py
import importlib
import streamlit as st
from datetime import datetime

# Mapeo visible -> módulo en pagesEIM.deuda y función render()
SUBPAGES_EIM = {
    "Gestión de datos": ("pagesEIM.deuda.gestion_datos", "render"),
    "Global":           ("pagesEIM.deuda.global_",       "render"),   # el archivo se llama global_.py
    "Pendiente":        ("pagesEIM.deuda.pendiente",     "render"),
}

def deuda_page():
    st.title("💼 Sección: Gestión de Cobro (EIM)")
    st.caption(f"🕒 Última actualización: {datetime.now():%Y-%m-%d %H:%M}")

    # Selector de subpágina
    visible = list(SUBPAGES_EIM.keys())
    sub_sel = st.selectbox("Selecciona una subcategoría:", visible)

    module_path, fn_name = SUBPAGES_EIM.get(sub_sel, (None, None))
    if not module_path:
        st.error("Configuración de subpáginas no válida.")
        return

    # Import dinámico y ejecución
    try:
        mod = importlib.import_module(module_path)
        fn = getattr(mod, fn_name, None)
        if not callable(fn):
            st.error(f"El módulo `{module_path}` no define la función `{fn_name}()`.")
            return
        # Mostrar cuál módulo se ejecuta (útil para depurar)
        st.caption(f"🔗 Cargando: `{module_path}.{fn_name}()`")
        fn()
    except ModuleNotFoundError as e:
        st.error(f"No se encontró el módulo para **‘{sub_sel}’**.\n\n"
                 f"Intenté importar: `{module_path}`\n\nDetalle: {e}")
    except Exception as e:
        st.error(f"Error ejecutando **‘{sub_sel}’**: {e}")
