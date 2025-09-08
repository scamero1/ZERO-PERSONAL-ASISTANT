import requests

def buscar_contextual(query):
    url = "https://google-search72.p.rapidapi.com/search?q=word%20cup&lr=en-US&num=10"
    headers = {
        "X-RapidAPI-Key": "06a866ea79mshef180cace5e58a5p18decejsne357d6d9e600",
        "X-RapidAPI-Host": "google-search72.p.rapidapi.com"
    }
    params = {
        "q": query,
        "pageNumber": "1",
        "pageSize": "3",
        "autoCorrect": "true"
    }

    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    resultados = data.get("value", [])
    respuesta = ""

    for res in resultados:
        titulo = res.get("title", "")
        descripcion = res.get("description", "")
        link = res.get("url", "")
        respuesta += f"🔹 **{titulo}**\n{descripcion}\n🔗 {link}\n\n"

    return respuesta or "No se encontraron resultados web."

def necesita_busqueda_en_tiempo_real(pregunta):
    claves = [
        "hoy", "último", "última", "ayer", "noticias", "precio", "cuánto vale",
        "cuánto está", "hora", "temperatura", "clima", "evento", "ranking",
        "actual", "resultado", "quién ganó", "fecha", "lanza", "estrena"
    ]
    return any(clave in pregunta.lower() for clave in claves)