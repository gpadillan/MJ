import streamlit as st

def inicio_page():
    st.markdown("<h1 style='text-align: center;'>📘 Bienvenido al Sistema de Gestión</h1>", unsafe_allow_html=True)
    
    st.markdown(
        """
        <div style='text-align: center; padding: 2rem; font-size: 1.3rem;'>
            <em>"Si enseñamos a los estudiantes de hoy como enseñamos ayer, <br>
            le estaremos robando el mañana."</em><br><br>
            <strong>— John Dewey</strong>
        </div>
        """,
        unsafe_allow_html=True
    )
