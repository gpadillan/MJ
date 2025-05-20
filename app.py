import streamlit as st
from auth import login_page
from sidebar import show_sidebar
from pages.admisiones import main_admisiones
from pages.academica.academica_main import academica_page
from pages.desarrollo_main import desarrollo_page
from pages import deuda_main
from pages.inicio import inicio_page

# Inicialización de sesión
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""
if 'role' not in st.session_state:
    st.session_state['role'] = "viewer"
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = "Inicio"
if 'excel_uploaded' not in st.session_state:
    st.session_state['excel_uploaded'] = False
if 'excel_filename' not in st.session_state:
    st.session_state['excel_filename'] = ""
if 'excel_data' not in st.session_state:
    st.session_state['excel_data'] = None
if 'upload_time' not in st.session_state:
    st.session_state['upload_time'] = None

# Configuración general de la página
st.set_page_config(
    page_title="Sistema de Gestión",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed" if not st.session_state['logged_in'] else "expanded"
)

# Estilos personalizados
def add_custom_css():
    st.markdown("""
    <style>
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    .main-header {
        text-align: center;
        padding: 1.5rem;
        background-color: #f0f2f6;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .card {
        padding: 1.5rem;
        border-radius: 10px;
        background-color: #f8f9fa;
        box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.05);
        margin-bottom: 1rem;
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    </style>
    """, unsafe_allow_html=True)

    if not st.session_state['logged_in']:
        st.markdown("""
        <style>
        [data-testid="stSidebar"] {
            display: none !important;
        }
        section[data-testid="stSidebarUserContent"] {
            display: none !important;
        }
        </style>
        """, unsafe_allow_html=True)

# Función principal
def main():
    add_custom_css()

    if not st.session_state['logged_in']:
        login_page()
    else:
        show_sidebar()  # Maneja el menú lateral

        current = st.session_state['current_page']

        if current == "Inicio":
            inicio_page()
        elif current == "Admisiones":
            main_admisiones.app()
        elif current == "Academica":
            academica_page()  # ✅ Ahora funcionará correctamente
        elif current == "Desarrollo":
            desarrollo_page()
        elif current == "Gestión de Cobro":
            deuda_main.deuda_page()

# Punto de entrada
if __name__ == "__main__":
    main()
