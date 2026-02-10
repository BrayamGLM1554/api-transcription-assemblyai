# API de Transcripción con AssemblyAI

API REST creada con Flask para transcribir archivos de audio usando AssemblyAI.

## 🚀 Instalación

1. Instala las dependencias:
```bash
pip install -r requirements.txt
```

2. Ejecuta la API:
```bash
python transcription_api.py
```

La API estará disponible en `http://localhost:5000`

## 📋 Endpoints Disponibles

### 1. Health Check
**GET** `/health`

Verifica que la API está funcionando.

**Respuesta:**
```json
{
  "status": "ok",
  "message": "API de transcripción funcionando"
}
```

### 2. Transcribir Archivo de Audio
**POST** `/transcribe`

Transcribe un archivo de audio MP3 (o WAV, M4A, FLAC).

**Cómo usarlo:**
- Método: POST
- Content-Type: multipart/form-data
- Key: `audio`
- Valor: Tu archivo de audio

**Ejemplo con cURL:**
```bash
curl -X POST http://localhost:5000/transcribe \
  -F "audio=@/ruta/a/tu/audio.mp3"
```

**Ejemplo con Python:**
```python
import requests

url = "http://localhost:5000/transcribe"
files = {'audio': open('mi_audio.mp3', 'rb')}
response = requests.post(url, files=files)

print(response.json())
```

**Ejemplo con Postman:**
1. Selecciona método POST
2. URL: `http://localhost:5000/transcribe`
3. Ve a la pestaña "Body"
4. Selecciona "form-data"
5. Agrega key: `audio` (tipo: File)
6. Selecciona tu archivo MP3

**Respuesta exitosa:**
```json
{
  "status": "success",
  "text": "Texto transcrito del audio...",
  "language_code": "es",
  "confidence": 0.95
}
```

**Respuesta de error:**
```json
{
  "status": "error",
  "message": "Descripción del error"
}
```

### 3. Transcribir desde URL
**POST** `/transcribe-url`

Transcribe un audio desde una URL pública.

**Cómo usarlo:**
- Método: POST
- Content-Type: application/json
- Body: JSON con la URL del audio

**Ejemplo con cURL:**
```bash
curl -X POST http://localhost:5000/transcribe-url \
  -H "Content-Type: application/json" \
  -d '{"audio_url": "https://assembly.ai/wildfires.mp3"}'
```

**Ejemplo con Python:**
```python
import requests

url = "http://localhost:5000/transcribe-url"
data = {"audio_url": "https://assembly.ai/wildfires.mp3"}
response = requests.post(url, json=data)

print(response.json())
```

## 🔧 Configuración

### Cambiar API Key
En el archivo `transcription_api.py`, modifica la línea:
```python
ASSEMBLYAI_API_KEY = "tu_api_key_aqui"
```

### Cambiar Puerto
En el archivo `transcription_api.py`, en la última línea:
```python
app.run(debug=True, host='0.0.0.0', port=5000)  # Cambia 5000 por el puerto que quieras
```

## 📝 Formatos de Audio Soportados

- MP3
- WAV
- M4A
- FLAC

## ⚙️ Características

✅ Detección automática de idioma
✅ Usa modelos universal-3-pro y universal-2
✅ Soporta CORS (puede ser llamado desde frontend)
✅ Manejo de errores robusto
✅ Polling automático hasta que la transcripción esté completa

## 🐛 Solución de Problemas

**Error: No se encontró ningún archivo de audio**
- Asegúrate de usar la key `audio` en form-data
- Verifica que estás enviando un archivo, no una cadena de texto

**Error: Formato de archivo no soportado**
- Usa archivos MP3, WAV, M4A o FLAC
- Verifica que la extensión del archivo sea correcta

**Error 401 Unauthorized**
- Verifica que tu API key de AssemblyAI sea válida
- Asegúrate de que la API key esté correctamente configurada

## 📦 Producción

Para producción, considera usar un servidor WSGI como Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 transcription_api:app
```

## 🔒 Seguridad

**IMPORTANTE:** La API key está hardcodeada en el ejemplo. Para producción:
1. Usa variables de entorno
2. No subas la API key a repositorios públicos
3. Implementa autenticación en tu API

Ejemplo usando variables de entorno:
```python
import os
ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY')
```

Luego ejecuta:
```bash
export ASSEMBLYAI_API_KEY="tu_api_key"
python transcription_api.py
```