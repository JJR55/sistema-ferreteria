import requests

def get_usd_to_dop_rate():
    """
    Obtiene la tasa de cambio actual de USD a DOP desde una API gratuita.
    """
    try:
        # Usamos una API pública y gratuita que no requiere clave
        api_url = "https://open.er-api.com/v6/latest/USD"
        response = requests.get(api_url, timeout=5) # Timeout de 5 segundos
        response.raise_for_status()  # Lanza un error si la petición no fue exitosa (ej. 404, 500)
        
        data = response.json()
        rate = data.get("rates", {}).get("DOP")
        return rate
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"Error al obtener la tasa de cambio: {e}")
        return None # Devolver None si hay un error de red o de formato