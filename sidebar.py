import streamlit as st

# Función para mostrar la barra lateral con navegación
def show_sidebar():
    with st.sidebar:
        st.markdown(f"### Bienvenido, {st.session_state['username']}")
        st.markdown("---")

        # Opciones de navegación
        st.markdown("### Navegación")

        if st.sidebar.button("Área de Admisiones"):
            st.session_state['current_page'] = "Admisiones"
            st.rerun()

        if st.sidebar.button("Área Académica"):
            st.session_state['current_page'] = "Academica"
            st.rerun()

        if st.sidebar.button("Área Desarrollo Profesional"):
            st.session_state['current_page'] = "Desarrollo"
            st.rerun()

        if st.sidebar.button("Gestión de Cobro"):  # ✅ Nombre actualizado aquí
            st.session_state['current_page'] = "Gestión de Cobro"
            st.rerun()

        st.markdown("---")

        # Botón de cerrar sesión
        if st.sidebar.button("Cerrar Sesión"):
            st.session_state['logged_in'] = False
            st.session_state['username'] = ""
            st.session_state['excel_data'] = None
            st.session_state['excel_filename'] = ""
            st.session_state['upload_time'] = None
            st.session_state['current_page'] = "Inicio"
            st.rerun()
