import requests

# Clave de API de Deepgram
DEEPGRAM_API_KEY = "a780d7cc3a0d84d07be3e21bb0bd5f70d10f16e8"

# URL de la API de Deepgram para TTS
url = "https://api.deepgram.com/v1/speak?model=aura-2-celeste-es"

# Texto que quieres convertir a voz
data = {
    "text": "Es una buena historia para contar"
}

# Cabeceras de la solicitud
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Token {DEEPGRAM_API_KEY}"
}

# Realiza la solicitud POST y obtiene la respuesta como binario
response = requests.post(url, json=data, headers=headers)

# Verifica si la solicitud fue exitosa
if response.status_code == 200:
    # Guarda el contenido en un archivo MP3 local
    with open("your_output_file.mp3", "wb") as f:
        f.write(response.content)
    print("Archivo guardado como your_output_file.mp3")
else:
    print(f"Error {response.status_code}: {response.text}")
