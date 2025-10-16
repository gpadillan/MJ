def app():
    import os
    import streamlit as st

    # ===== MODO MANTENIMIENTO (no llamar set_page_config aquí) =====
    # Actívalo con cualquiera de estas tres vías:
    #   - bandera fija (cambia a False para reactivar)
    #   - st.secrets["maintenance_situacion_2025"] = true
    #   - variable de entorno APP_MAINTENANCE=1
    MAINTENANCE_FLAG_FILE = True  # ← pon False para volver a mostrar la página
    MAINTENANCE = (
        MAINTENANCE_FLAG_FILE
        or bool(st.secrets.get("maintenance_situacion_2025", False))
        or os.getenv("APP_MAINTENANCE", "0") == "1"
    )

    if MAINTENANCE:
        st.markdown(
            """
            # 🛠️ Estamos en reforma
            Estamos actualizando esta sección.  
            Vuelve más tarde, por favor. 🙏
            """
        )
        st.stop()  # detiene el resto de la página

    # --- a partir de aquí va tu código normal de la página ---
    # (carga de excels, gráficos, etc.)
