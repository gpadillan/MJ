import streamlit as st

def show_sidebar():
    with st.sidebar:
        st.markdown(f"### 👋 Bienvenido, {st.session_state['username']}")
        st.markdown("---")

        # Navegación principal
        st.markdown("### 📂 Navegación")

        nav_items = {
            "Área Principal": "Principal",         # ✅ Agregada
            "Área de Admisiones": "Admisiones",
            "Área Académica": "Academica",
            "Área de Empleo": "Desarrollo",        # 🔁 Modificado aquí
            "Área Gestión de Cobro": "Gestión de Cobro"
        }

        for label, page_key in nav_items.items():
            if st.button(label):
                st.session_state['current_page'] = page_key
                st.rerun()

        st.markdown("---")

        if st.button("🚪 Cerrar Sesión"):
            st.session_state['logged_in'] = False
            st.session_state['username'] = ""
            st.session_state['excel_data'] = None
            st.session_state['excel_filename'] = ""
            st.session_state['upload_time'] = None
            st.session_state['current_page'] = "Inicio"
            st.rerun()
