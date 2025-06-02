# responsive.py

from streamlit_js_eval import streamlit_js_eval
import time

def get_screen_size():
    """
    Devuelve (width, height) del gráfico en función del tamaño de pantalla.
    Usa streamlit_js_eval y fuerza actualización cada 5 segundos.
    """
    # Clave dinámica para que se actualice con cada render
    key = f"screen_width_{int(time.time() // 5)}"

    screen_width = streamlit_js_eval(js_expressions="window.innerWidth", key=key)

    if screen_width is None:
        # Si aún no se detecta (primer render), asumimos escritorio
        return 800, 500
    elif screen_width < 600:
        # Pantalla pequeña: móvil
        return 350, 400
    else:
        # Escritorio o tablet
        return 900, 500
