import streamlit as st

# Base de datos de usuarios
USUARIOS = {
    "admin": {"password": "admin", "role": "admin"},
    "AntonioM": {"password": "Mainjobs=50-", "role": "viewer"},
    "JorgeG": {"password": "Mainjobs=50-", "role": "viewer"},
    "GabrielAles": {"password": "Mainjobs=50-", "role": "viewer"},
    "SusanaPerez": {"password": "Mainjobs=50-", "role": "viewer"},
    "PalomaS": {"password": "Mainjobs=50-", "role": "viewer"},
    "AlejandroR": {"password": "Mainjobs$14-", "role": "viewer"},
    "AguaS": {"password": "Mainjobs$18-", "role": "viewer"},
    "LauraR": {"password": "Mainjobs$19-", "role": "viewer"},
    "IsabelJ": {"password": "Mainjobs$22-", "role": "viewer"},
    "RobertoA": {"password": "Mainjobs$16-", "role": "viewer"},
    "RemeC": {"password": "Mainjobs$74-", "role": "viewer"},
    "MamenM": {"password": "Mainjobs$50-", "role": "viewer"},
    "AnaM": {"password": "Mainjobs$10-", "role": "viewer"},
    "Juanantonio": {"password": "Mainjobs=50-", "role": "viewer"},
    "AliciaP": {"password": "Mainjobs=90", "role": "viewer"},
}

# Función para verificar credenciales
def check_credentials(username, password):
    if username in USUARIOS and USUARIOS[username]["password"] == password:
        return True, USUARIOS[username]["role"]
    return False, None

# Página de login
def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("assets/grupo-mainjobs.png", use_container_width=True)
        except Exception as e:
            st.warning(f"❌ No se pudo cargar el logotipo: {e}")

        st.markdown("<div class='card'><h4 style='text-align:center;'>Acceder al sistema de gestión</h4></div>", unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Iniciar sesión")

            if submit:
                valid, role = check_credentials(username, password)
                if valid:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.session_state['role'] = role
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
