from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import time
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde archivo .env (opcional)
load_dotenv()

app = Flask(__name__)
CORS(app)  # Permite peticiones desde cualquier origen

# Configuración de AssemblyAI
# Primero intenta leer desde variable de entorno, si no usa el valor hardcodeado
ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY', 'bfa9693c209840539fd901196346c4a6')
ASSEMBLYAI_BASE_URL = "https://api.assemblyai.com"
PORT = int(os.getenv('PORT', 5000))

headers = {
    "authorization": ASSEMBLYAI_API_KEY
}

def upload_audio_to_assemblyai(audio_file):
    """Sube el archivo de audio a AssemblyAI y retorna la URL"""
    upload_url = f"{ASSEMBLYAI_BASE_URL}/v2/upload"
    
    response = requests.post(
        upload_url,
        headers=headers,
        data=audio_file
    )
    
    if response.status_code == 200:
        return response.json()["upload_url"]
    else:
        raise Exception(f"Error al subir el audio: {response.text}")

def transcribe_audio(audio_url):
    """Inicia la transcripción y retorna el ID del transcript"""
    transcript_url = f"{ASSEMBLYAI_BASE_URL}/v2/transcript"
    
    data = {
        "audio_url": audio_url,
        "language_detection": True,
        "speech_models": ["universal-3-pro", "universal-2"]
    }
    
    response = requests.post(transcript_url, json=data, headers=headers)
    
    if response.status_code == 200:
        return response.json()['id']
    else:
        raise Exception(f"Error al iniciar transcripción: {response.text}")

def get_transcription_result(transcript_id):
    """Obtiene el resultado de la transcripción (con polling)"""
    polling_endpoint = f"{ASSEMBLYAI_BASE_URL}/v2/transcript/{transcript_id}"
    
    while True:
        response = requests.get(polling_endpoint, headers=headers)
        transcription_result = response.json()
        
        if transcription_result['status'] == 'completed':
            return {
                "status": "success",
                "text": transcription_result['text'],
                "language_code": transcription_result.get('language_code'),
                "confidence": transcription_result.get('confidence'),
                "words": transcription_result.get('words')  # Palabras individuales con timestamps
            }
        elif transcription_result['status'] == 'error':
            return {
                "status": "error",
                "error": transcription_result['error']
            }
        else:
            time.sleep(3)

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar que la API está funcionando"""
    return jsonify({
        "status": "ok", 
        "message": "API de transcripción funcionando",
        "version": "1.0.0"
    }), 200

@app.route('/transcribe', methods=['POST'])
def transcribe():
    """
    Endpoint principal para transcribir audio
    Acepta archivos MP3 mediante form-data con key 'audio'
    """
    try:
        # Verificar que se envió un archivo
        if 'audio' not in request.files:
            return jsonify({
                "status": "error",
                "message": "No se encontró ningún archivo de audio. Usa la key 'audio' en form-data"
            }), 400
        
        audio_file = request.files['audio']
        
        # Verificar que el archivo tiene un nombre
        if audio_file.filename == '':
            return jsonify({
                "status": "error",
                "message": "El archivo no tiene nombre"
            }), 400
        
        # Verificar extensión del archivo
        allowed_extensions = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.webm')
        if not audio_file.filename.lower().endswith(allowed_extensions):
            return jsonify({
                "status": "error",
                "message": f"Formato de archivo no soportado. Usa: {', '.join(allowed_extensions)}"
            }), 400
        
        # 1. Subir el archivo a AssemblyAI
        print(f"📤 Subiendo archivo '{audio_file.filename}' a AssemblyAI...")
        audio_url = upload_audio_to_assemblyai(audio_file.read())
        print(f"✅ Audio subido exitosamente")
        
        # 2. Iniciar transcripción
        print("🎙️  Iniciando transcripción...")
        transcript_id = transcribe_audio(audio_url)
        print(f"📋 Transcripción iniciada con ID: {transcript_id}")
        
        # 3. Obtener resultado (con polling)
        print("⏳ Esperando resultado de transcripción...")
        result = get_transcription_result(transcript_id)
        
        if result['status'] == 'success':
            print(f"✅ Transcripción completada exitosamente")
        else:
            print(f"❌ Error en transcripción: {result.get('error')}")
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/transcribe-url', methods=['POST'])
def transcribe_from_url():
    """
    Endpoint alternativo para transcribir desde una URL
    Acepta JSON con formato: {"audio_url": "https://..."}
    """
    try:
        data = request.get_json()
        
        if not data or 'audio_url' not in data:
            return jsonify({
                "status": "error",
                "message": "Debes proporcionar 'audio_url' en el body JSON"
            }), 400
        
        audio_url = data['audio_url']
        
        # 1. Iniciar transcripción
        print(f"🎙️  Iniciando transcripción desde URL: {audio_url}")
        transcript_id = transcribe_audio(audio_url)
        print(f"📋 Transcripción iniciada con ID: {transcript_id}")
        
        # 2. Obtener resultado
        print("⏳ Esperando resultado de transcripción...")
        result = get_transcription_result(transcript_id)
        
        if result['status'] == 'success':
            print(f"✅ Transcripción completada exitosamente")
        else:
            print(f"❌ Error en transcripción: {result.get('error')}")
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/transcribe-async', methods=['POST'])
def transcribe_async():
    """
    Endpoint asíncrono: inicia la transcripción y retorna el ID inmediatamente
    El cliente puede consultar el estado usando /status/{transcript_id}
    """
    try:
        audio_url = None
        
        # Verificar si es archivo o URL
        if 'audio' in request.files:
            audio_file = request.files['audio']
            if audio_file.filename == '':
                return jsonify({"status": "error", "message": "El archivo no tiene nombre"}), 400
            
            print(f"📤 Subiendo archivo '{audio_file.filename}'...")
            audio_url = upload_audio_to_assemblyai(audio_file.read())
        else:
            data = request.get_json()
            if not data or 'audio_url' not in data:
                return jsonify({
                    "status": "error",
                    "message": "Proporciona un archivo 'audio' o 'audio_url' en JSON"
                }), 400
            audio_url = data['audio_url']
        
        # Iniciar transcripción
        print(f"🎙️  Iniciando transcripción...")
        transcript_id = transcribe_audio(audio_url)
        print(f"📋 Transcripción iniciada: {transcript_id}")
        
        return jsonify({
            "status": "processing",
            "transcript_id": transcript_id,
            "message": "Transcripción iniciada. Usa /status/{transcript_id} para consultar el estado"
        }), 202
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/status/<transcript_id>', methods=['GET'])
def get_status(transcript_id):
    """
    Consulta el estado de una transcripción asíncrona
    """
    try:
        polling_endpoint = f"{ASSEMBLYAI_BASE_URL}/v2/transcript/{transcript_id}"
        response = requests.get(polling_endpoint, headers=headers)
        result = response.json()
        
        status = result['status']
        
        if status == 'completed':
            return jsonify({
                "status": "completed",
                "text": result['text'],
                "language_code": result.get('language_code'),
                "confidence": result.get('confidence')
            }), 200
        elif status == 'error':
            return jsonify({
                "status": "error",
                "error": result['error']
            }), 200
        else:
            return jsonify({
                "status": "processing",
                "message": f"Transcripción en proceso... (estado: {status})"
            }), 200
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "status": "error",
        "message": "Endpoint no encontrado"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "status": "error",
        "message": "Error interno del servidor"
    }), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Iniciando API de Transcripción")
    print("=" * 60)
    print(f"📡 Puerto: {PORT}")
    print(f"🔑 API Key configurada: {'✅ Sí' if ASSEMBLYAI_API_KEY else '❌ No'}")
    print("=" * 60)
    print("\nEndpoints disponibles:")
    print("  GET  /health              - Health check")
    print("  POST /transcribe          - Transcribir archivo (síncrono)")
    print("  POST /transcribe-url      - Transcribir desde URL (síncrono)")
    print("  POST /transcribe-async    - Iniciar transcripción (asíncrono)")
    print("  GET  /status/<id>         - Consultar estado (asíncrono)")
    print("=" * 60)
    
    # Ejecutar en modo desarrollo
    app.run(debug=True, host='0.0.0.0', port=PORT)
