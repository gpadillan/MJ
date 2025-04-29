import streamlit as st 
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

VENTAS_PATH = "uploaded_admisiones/ventas.xlsx"
PREVENTAS_PATH = "uploaded_admisiones/preventas.xlsx"

def app():
    traducciones_meses = {
        "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
        "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
        "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
    }
    now = datetime.now()
    mes_actual = traducciones_meses[now.strftime("%B")] + " " + now.strftime("%Y")

    st.markdown(f"### 📊 Ventas y Preventas - {mes_actual}")

    df_ventas = pd.read_excel(VENTAS_PATH) if os.path.exists(VENTAS_PATH) else None
    df_preventas = pd.read_excel(PREVENTAS_PATH) if os.path.exists(PREVENTAS_PATH) else None

    if df_ventas is not None:
        st.markdown("#### Distribución de Oportunidades y Propietario")

        if 'nombre' in df_ventas.columns and 'propietario' in df_ventas.columns:
            resumen = df_ventas.groupby(['nombre', 'propietario']).size().reset_index(name='Total Oportunidades')

            fig = px.scatter(
                resumen,
                x='nombre',
                y='propietario',
                size='Total Oportunidades',
                color='propietario',
                title='',
                size_max=60,
                height=600
            )
            fig.update_layout(xaxis_title='Máster', yaxis_title='Propietario')
            st.plotly_chart(fig, use_container_width=True)

            total_importe = df_ventas['importe'].sum() if 'importe' in df_ventas.columns else 0
            total_oportunidades = len(df_ventas)
            total_preventas = df_preventas['importe'].sum() if df_preventas is not None and 'importe' in df_preventas.columns else 0

            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"""
                    <div style="padding: 1rem; background-color: #f1f3f6; border-left: 5px solid #1f77b4;
                                border-radius: 8px; width: 100%;">
                        <h4 style="margin: 0;"> Importe Total</h4>
                        <p style="font-size: 1.5rem; font-weight: bold; margin: 0;">{total_importe:,.2f} €</p>
                    </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"""
                    <div style="padding: 1rem; background-color: #f1f3f6; border-left: 5px solid #1f77b4;
                                border-radius: 8px; width: 100%;">
                        <h4 style="margin: 0;">Total Oportunidades Ganadas</h4>
                        <p style="font-size: 1.5rem; font-weight: bold; margin: 0;">{total_oportunidades}</p>
                    </div>
                """, unsafe_allow_html=True)

            with col3:
                st.markdown(f"""
                    <div style="padding: 1rem; background-color: #f1f3f6; border-left: 5px solid #1f77b4;
                                border-radius: 8px; width: 100%;">
                        <h4 style="margin: 0;"> Preventas</h4>
                        <p style="font-size: 1.5rem; font-weight: bold; margin: 0;">{total_preventas:,.2f} €</p>
                    </div>
                """, unsafe_allow_html=True)

        else:
            st.warning("❌ El archivo de ventas debe tener columnas 'nombre' y 'propietario'.")

    elif df_preventas is not None:
        st.markdown("#### 🧾 Total Preventas")
        if 'importe' in df_preventas.columns:
            total_preventas = df_preventas['importe'].sum()
            st.markdown(f"""
                <div style="padding: 1rem; background-color: #f1f3f6; border-left: 5px solid #1f77b4;
                            border-radius: 8px; width: 250px;">
                    <h4 style="margin: 0;">📦 Preventas</h4>
                    <p style="font-size: 1.5rem; font-weight: bold; margin: 0;">{total_preventas:,.2f} €</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("❌ El archivo de preventas debe tener la columna 'importe'.")

    if df_ventas is None and df_preventas is None:
        st.info("⚠️ No se han encontrado archivos de ventas o preventas.")
