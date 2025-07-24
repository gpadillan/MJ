# utils/geo_utils.py
import unicodedata
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import pandas as pd

PROVINCIAS_COORDS = {
    "A Coruña": (43.3623, -8.4115), "Álava": (42.8466, -2.6727), "Albacete": (38.9943, -1.8585),
    "Alicante": (38.3452, -0.4810), "Almería": (36.8340, -2.4637), "Asturias": (43.3619, -5.8494),
    "Ávila": (40.6565, -4.6816), "Badajoz": (38.8794, -6.9707), "Barcelona": (41.3851, 2.1734),
    "Bizkaia": (43.2630, -2.9350), "Burgos": (42.3439, -3.6969), "Cáceres": (39.4753, -6.3723),
    "Cádiz": (36.5164, -6.2994), "Cantabria": (43.1828, -3.9878), "Castellón": (39.9864, -0.0513),
    "Ciudad Real": (38.9860, -3.9272), "Córdoba": (37.8882, -4.7794), "Cuenca": (40.0704, -2.1374),
    "Girona": (41.9794, 2.8214), "Granada": (37.1773, -3.5986), "Guadalajara": (40.6333, -3.1667),
    "Guipúzcoa": (43.3128, -1.9744), "Huelva": (37.2614, -6.9447), "Huesca": (42.1362, -0.4089),
    "Jaén": (37.7796, -3.7849), "La Rioja": (42.4650, -2.4489), "Las Palmas": (28.1235, -15.4363),
    "León": (42.5987, -5.5671), "Lleida": (41.6176, 0.6200), "Lugo": (43.0097, -7.5560),
    "Madrid": (40.4168, -3.7038), "Málaga": (36.7213, -4.4214), "Murcia": (37.9922, -1.1307),
    "Navarra": (42.6954, -1.6761), "Ourense": (42.3364, -7.8640), "Palencia": (42.0095, -4.5241),
    "Pontevedra": (42.4310, -8.6444), "Salamanca": (40.9701, -5.6635), "Santa Cruz De Tenerife": (28.4636, -16.2518),
    "Segovia": (40.9481, -4.1184), "Sevilla": (37.3886, -5.9823), "Soria": (41.7666, -2.4799),
    "Tarragona": (41.1189, 1.2445), "Teruel": (40.3456, -1.1065), "Toledo": (39.8628, -4.0273),
    "Valencia": (39.4699, -0.3763), "Valladolid": (41.6523, -4.7245), "Zamora": (41.5033, -5.7446),
    "Zaragoza": (41.6488, -0.8891), "Ceuta": (35.8894, -5.3213), "Melilla": (35.2923, -2.9381),
    "Illes Balears": (39.6953, 3.0176)
}

PAISES_COORDS = {
    "España": (40.4637, -3.7492), "Argentina": (-38.4161, -63.6167), "Colombia": (4.5709, -74.2973),
    "México": (23.6345, -102.5528), "Chile": (-35.6751, -71.5430), "Ecuador": (-1.8312, -78.1834),
    "Perú": (-9.1899, -75.0152), "Bolivia": (-16.2902, -63.5887), "Uruguay": (-32.5228, -55.7658),
    "Venezuela": (6.4238, -66.5897), "Estados Unidos": (37.0902, -95.7129), "Francia": (46.6034, 1.8883)
}

def get_geolocator():
    return Nominatim(user_agent="geoapi_map")

def geolocalizar_pais(pais):
    geolocator = get_geolocator()
    try:
        loc = geolocator.geocode(pais, timeout=5)
        if loc:
            return (loc.latitude, loc.longitude)
    except (GeocoderTimedOut, GeocoderServiceError):
        return None
    return None

def normalize_text(text):
    if pd.isna(text):
        return ""
    original = str(text).strip().title()
    sin_tildes = unicodedata.normalize("NFKD", original).encode("ascii", "ignore").decode("utf-8")

    correcciones = {
        "Espana": "España", "Cordoba": "Córdoba", "Guipuzcoa": "Guipúzcoa", "Alava": "Álava",
        "Malaga": "Málaga", "Avila": "Ávila", "Leon": "León", "Caceres": "Cáceres", "Cadiz": "Cádiz",
        "La Coruna": "A Coruña", "Coruna": "A Coruña", "A Coruna": "A Coruña",
        "Iles Balears": "Illes Balears", "Islas Baleares": "Illes Balears", "Baleares": "Illes Balears",
        "Girona": "Girona", "Gerona": "Girona", "Lerida": "Lleida", "Orense": "Ourense",
        "Vizcaya": "Bizkaia", "Melilola": "Melilla", "Madridi": "Madrid", "Ceuta": "Ceuta", "Melilla": "Melilla"
    }

    return correcciones.get(sin_tildes, original)
