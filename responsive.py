# responsive.py
from streamlit_js_eval import streamlit_js_eval

def get_screen_size():
    screen_width = streamlit_js_eval(js_expressions="window.innerWidth", key="screen_width")
    if screen_width and screen_width < 600:
        return 350, 300  # Tamaño para móvil
    else:
        return 800, 500  # Tamaño para escritorio
