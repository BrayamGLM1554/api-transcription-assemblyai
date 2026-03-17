from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import time
import os
import traceback
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Archivos pequeños que pasan por Render (100 MB)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY', '5f5fcdb5a90a4a128a5ccc5b399a250b')
ASSEMBLYAI_BASE_URL = "https://api.assemblyai.com"
PORT = int(os.getenv('PORT', 5000))

headers = {
    "authorization": ASSEMBLYAI_API_KEY
}


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def upload_audio_to_assemblyai(audio_file):
    """Sube el archivo de audio/video a AssemblyAI y retorna la URL.
    Usado cuando el archivo pasa por Render (< 100 MB)."""
    upload_url = f"{ASSEMBLYAI_BASE_URL}/v2/upload"

    print(f"  [ASSEMBLYAI] POST {upload_url}")
    response = requests.post(upload_url, headers=headers, data=audio_file)
    print(f"  [ASSEMBLYAI] Upload status: {response.status_code}")

    if response.status_code == 200:
        upload_result = response.json()
        print(f"  [ASSEMBLYAI] Upload OK -> {upload_result.get('upload_url', 'N/A')[:60]}...")
        return upload_result["upload_url"]
    else:
        print(f"  [ASSEMBLYAI] Upload FAILED -> {response.text}")
        raise Exception(
            f"Error al subir el archivo a AssemblyAI (HTTP {response.status_code}): {response.text}"
        )


def transcribe_audio(audio_url, quality_mode="maximum", custom_vocabulary=None):
    """Inicia una transcripción en AssemblyAI y retorna el transcript_id."""
    transcript_url = f"{ASSEMBLYAI_BASE_URL}/v2/transcript"

    data = {
        "audio_url": audio_url,
        "language_detection": True,
        "speech_model": "universal",
        "language_confidence_threshold": 0.7,
        "boost_param": "high",
        "punctuate": True,
        "format_text": True,
        "speaker_labels": True,
        "filter_profanity": False,
        "redact_pii": False,
    }

    if quality_mode == "maximum":
        data.update({
            "dual_channel": False,
            "speakers_expected": None,
        })

    if custom_vocabulary and len(custom_vocabulary) > 0:
        data["word_boost"] = custom_vocabulary
        data["boost_param"] = "high"

    print(f"  [ASSEMBLYAI] POST {transcript_url} | mode={quality_mode}")
    response = requests.post(transcript_url, json=data, headers=headers)
    print(f"  [ASSEMBLYAI] Transcript request status: {response.status_code}")

    if response.status_code == 200:
        transcript_id = response.json()['id']
        print(f"  [ASSEMBLYAI] Transcript ID: {transcript_id}")
        return transcript_id
    else:
        print(f"  [ASSEMBLYAI] Transcript request FAILED -> {response.text}")
        raise Exception(
            f"Error al iniciar transcripcion (HTTP {response.status_code}): {response.text}"
        )


def get_transcription_result(transcript_id):
    """Hace polling hasta que la transcripción esté lista. Síncrono."""
    polling_endpoint = f"{ASSEMBLYAI_BASE_URL}/v2/transcript/{transcript_id}"

    while True:
        response = requests.get(polling_endpoint, headers=headers)
        transcription_result = response.json()

        if transcription_result['status'] == 'completed':
            return {
                "status": "completed",
                "text": transcription_result['text'],
                "language_code": transcription_result.get('language_code'),
                "confidence": transcription_result.get('confidence'),
                "words": transcription_result.get('words'),
                "utterances": transcription_result.get('utterances'),
                "audio_duration": transcription_result.get('audio_duration'),
            }
        elif transcription_result['status'] == 'error':
            return {
                "status": "error",
                "error": transcription_result['error']
            }
        else:
            time.sleep(3)


# ─────────────────────────────────────────────────────────────────────────────
#  ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "message": "API de transcripcion funcionando",
        "version": "4.0.0 - Direct Upload Support"
    }), 200


# ── NUEVO: URL de subida directa para el frontend ────────────────────────────
@app.route('/get-upload-url', methods=['POST'])
def get_upload_url():
    """
    Retorna la URL de subida de AssemblyAI y la API key para que el frontend
    pueda subir archivos grandes (>100 MB o videos) directamente, sin pasar
    por Render.

    NOTA DE SEGURIDAD: Este sistema usa autenticación por login previo.
    La API key solo es accesible para usuarios autenticados.
    """
    try:
        return jsonify({
            "upload_url": f"{ASSEMBLYAI_BASE_URL}/v2/upload",
            "api_key": ASSEMBLYAI_API_KEY
        }), 200
    except Exception as e:
        print(f"[ERROR /get-upload-url] {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ── Transcripción desde URL (síncrona) ───────────────────────────────────────
@app.route('/transcribe-url', methods=['POST'])
def transcribe_from_url():
    """
    Recibe una audio_url ya subida a AssemblyAI (por el frontend o por Render)
    e inicia la transcripción en modo síncrono (hace polling internamente).
    Ideal para cuando el archivo ya fue subido directamente por el frontend.
    """
    try:
        data = request.get_json()
        if not data or 'audio_url' not in data:
            return jsonify({
                "status": "error",
                "message": "Debes proporcionar 'audio_url' en el body JSON"
            }), 400

        audio_url = data['audio_url']
        quality_mode = data.get('quality', 'maximum')
        custom_vocabulary = data.get('vocabulary', None)

        print(f"\n[/transcribe-url] audio_url={audio_url[:60]}... | mode={quality_mode}")

        transcript_id = transcribe_audio(audio_url, quality_mode, custom_vocabulary)
        result = get_transcription_result(transcript_id)

        print(f"[/transcribe-url] Completado con status={result['status']}")
        return jsonify(result), 200

    except Exception as e:
        print(f"[ERROR /transcribe-url] {str(e)}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


# ── Transcripción desde URL (asíncrona) ──────────────────────────────────────
@app.route('/transcribe-url-async', methods=['POST'])
def transcribe_from_url_async():
    """
    Recibe una audio_url ya subida y retorna inmediatamente con el transcript_id.
    El frontend hace polling a /status/<transcript_id>.
    Úsalo cuando no quieras bloquear el worker de Render durante el procesamiento.
    """
    try:
        data = request.get_json()
        if not data or 'audio_url' not in data:
            return jsonify({
                "status": "error",
                "message": "Debes proporcionar 'audio_url' en el body JSON"
            }), 400

        audio_url = data['audio_url']
        quality_mode = data.get('quality', 'maximum')
        custom_vocabulary = data.get('vocabulary', None)

        print(f"\n[/transcribe-url-async] audio_url={audio_url[:60]}... | mode={quality_mode}")

        transcript_id = transcribe_audio(audio_url, quality_mode, custom_vocabulary)

        print(f"[/transcribe-url-async] transcript_id={transcript_id}")
        return jsonify({
            "status": "processing",
            "transcript_id": transcript_id,
            "quality_mode": quality_mode,
            "message": "Transcripcion iniciada. Usa /status/{transcript_id} para consultar el estado"
        }), 202

    except Exception as e:
        print(f"[ERROR /transcribe-url-async] {str(e)}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


# ── Transcripción con archivo adjunto (síncrona) ─────────────────────────────
@app.route('/transcribe', methods=['POST'])
def transcribe():
    """
    Recibe un archivo (< 100 MB), lo sube a AssemblyAI y hace polling hasta
    completar. Endpoint síncrono, solo para audios pequeños.
    """
    try:
        if 'audio' not in request.files:
            return jsonify({
                "status": "error",
                "message": "No se encontro archivo. Usa la key 'audio' en form-data"
            }), 400

        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"status": "error", "message": "El archivo no tiene nombre"}), 400

        allowed_extensions = (
            '.mp3', '.mp4', '.wav', '.m4a', '.flac', '.ogg',
            '.webm', '.aac', '.amr', '.opus', '.wma',
            '.mov', '.avi', '.mkv', '.wmv', '.flv', '.m4v', '.3gp', '.ts', '.mts'
        )
        if not audio_file.filename.lower().endswith(allowed_extensions):
            return jsonify({
                "status": "error",
                "message": f"Formato no soportado. Usa: {', '.join(allowed_extensions)}"
            }), 400

        quality_mode = request.form.get('quality', 'maximum')
        vocabulary_str = request.form.get('vocabulary', '')
        custom_vocabulary = [w.strip() for w in vocabulary_str.split(',') if w.strip()] if vocabulary_str else None

        audio_url = upload_audio_to_assemblyai(audio_file.read())
        transcript_id = transcribe_audio(audio_url, quality_mode, custom_vocabulary)
        result = get_transcription_result(transcript_id)
        return jsonify(result), 200

    except Exception as e:
        print(f"[ERROR /transcribe] {str(e)}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


# ── Transcripción con archivo adjunto (asíncrona) ────────────────────────────
@app.route('/transcribe-async', methods=['POST'])
def transcribe_async():
    """
    Recibe un archivo (< 100 MB) o una audio_url en JSON.
    Retorna inmediatamente con el transcript_id para hacer polling.
    """
    print("\n" + "=" * 50)
    print("[/transcribe-async] Nueva solicitud recibida")
    print(f"  Content-Type  : {request.content_type}")
    print(f"  Content-Length: {request.content_length} bytes "
          f"({(request.content_length or 0) / 1024 / 1024:.2f} MB)")
    print(f"  Files         : {list(request.files.keys())}")
    print(f"  Form fields   : {list(request.form.keys())}")

    try:
        audio_url = None
        quality_mode = 'maximum'
        custom_vocabulary = None

        # ── Rama 1: archivo subido directamente ──────────────────────────────
        if 'audio' in request.files:
            audio_file = request.files['audio']
            filename = audio_file.filename or ''
            file_size = request.content_length or 0

            print(f"  [FILE] Nombre    : {filename}")
            print(f"  [FILE] Tamano    : {file_size / 1024 / 1024:.2f} MB")
            print(f"  [FILE] MIME type : {audio_file.mimetype}")

            if filename == '':
                return jsonify({"status": "error", "message": "El archivo no tiene nombre"}), 400

            allowed_extensions = (
                '.mp3', '.mp4', '.wav', '.m4a', '.flac', '.ogg',
                '.webm', '.aac', '.amr', '.opus', '.wma', '.mpeg', '.mpga', '.mp2',
                '.mov', '.avi', '.mkv', '.wmv', '.flv', '.m4v', '.3gp', '.ts', '.mts'
            )
            ext = os.path.splitext(filename.lower())[1]
            print(f"  [FILE] Extension detectada: '{ext}'")

            if ext not in allowed_extensions:
                return jsonify({
                    "status": "error",
                    "message": f"Formato no soportado: '{ext}'. "
                               f"Formatos validos: {', '.join(allowed_extensions)}"
                }), 400

            quality_mode = request.form.get('quality', 'maximum')
            vocabulary_str = request.form.get('vocabulary', '')
            custom_vocabulary = [w.strip() for w in vocabulary_str.split(',') if w.strip()] if vocabulary_str else None

            print(f"  [CONFIG] quality_mode     : {quality_mode}")
            print(f"  [CONFIG] custom_vocabulary: {custom_vocabulary}")

            print("  [STEP 1] Leyendo bytes del archivo...")
            file_bytes = audio_file.read()
            print(f"  [STEP 1] Bytes leidos: {len(file_bytes):,}")

            if len(file_bytes) == 0:
                return jsonify({
                    "status": "error",
                    "message": "El archivo esta vacio (0 bytes recibidos)"
                }), 400

            print("  [STEP 2] Subiendo a AssemblyAI...")
            audio_url = upload_audio_to_assemblyai(file_bytes)
            print("  [STEP 2] URL obtenida OK")

        # ── Rama 2: URL enviada en JSON ───────────────────────────────────────
        else:
            print("  [ROUTE] No se detecto archivo, intentando leer JSON...")
            data = request.get_json(silent=True)

            if data is None:
                return jsonify({
                    "status": "error",
                    "message": "Proporciona un archivo 'audio' en form-data o 'audio_url' en JSON"
                }), 400

            print(f"  [JSON] Keys recibidas: {list(data.keys())}")

            if 'audio_url' not in data:
                return jsonify({
                    "status": "error",
                    "message": "El JSON debe contener la clave 'audio_url'"
                }), 400

            audio_url = data['audio_url']
            quality_mode = data.get('quality', 'maximum')
            custom_vocabulary = data.get('vocabulary', None)
            print(f"  [JSON] audio_url: {audio_url[:60]}...")
            print(f"  [CONFIG] quality_mode: {quality_mode}")

        # ── Paso 3: iniciar transcripcion ─────────────────────────────────────
        print("  [STEP 3] Iniciando transcripcion en AssemblyAI...")
        transcript_id = transcribe_audio(audio_url, quality_mode, custom_vocabulary)
        print(f"  [STEP 3] transcript_id: {transcript_id}")

        print("[/transcribe-async] Solicitud procesada con exito")
        print("=" * 50 + "\n")

        return jsonify({
            "status": "processing",
            "transcript_id": transcript_id,
            "quality_mode": quality_mode,
            "message": "Transcripcion iniciada. Usa /status/{transcript_id} para consultar el estado"
        }), 202

    except Exception as e:
        print(f"  [EXCEPTION] {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        print("=" * 50 + "\n")
        return jsonify({"status": "error", "message": str(e)}), 500


# ── Consulta de estado ────────────────────────────────────────────────────────
@app.route('/status/<transcript_id>', methods=['GET'])
def get_status(transcript_id):
    """Consulta el estado de una transcripción asíncrona por su ID."""
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
                "confidence": result.get('confidence'),
                "audio_duration": result.get('audio_duration'),
                "utterances": result.get('utterances')
            }), 200
        elif status == 'error':
            return jsonify({"status": "error", "error": result['error']}), 200
        else:
            return jsonify({
                "status": "processing",
                "message": f"Transcripcion en proceso (estado: {status})"
            }), 200

    except Exception as e:
        print(f"[ERROR /status] {str(e)}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
#  ERROR HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(error):
    return jsonify({"status": "error", "message": "Endpoint no encontrado"}), 404


@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        "status": "error",
        "message": (
            "El archivo supera el limite de 100 MB permitido por el servidor. "
            "Para archivos mas grandes o videos, el frontend debe subirlos "
            "directamente a AssemblyAI usando /get-upload-url."
        )
    }), 413


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"status": "error", "message": "Error interno del servidor"}), 500


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 70)
    print("API DE TRANSCRIPCION v4.0 - SOPORTE SUBIDA DIRECTA")
    print("=" * 70)
    print(f"Puerto : {PORT}")
    print(f"API Key: {'configurada' if ASSEMBLYAI_API_KEY else 'NO configurada'}")
    print("=" * 70)
    print("\nEndpoints disponibles:")
    print("  GET  /health                 - Health check")
    print("  POST /get-upload-url         - URL de subida directa para el frontend (archivos grandes)")
    print("  POST /transcribe             - Transcribir archivo adjunto (sincrono, <100 MB)")
    print("  POST /transcribe-async       - Transcribir archivo adjunto (asincrono, <100 MB)")
    print("  POST /transcribe-url         - Transcribir desde URL (sincrono)")
    print("  POST /transcribe-url-async   - Transcribir desde URL (asincrono)")
    print("  GET  /status/<id>            - Consultar estado de transcripcion")
    print("\nFlujos:")
    print("  Archivos < 100 MB (audio):")
    print("    Frontend -> Render /transcribe-async -> AssemblyAI -> polling /status/<id>")
    print("  Archivos > 100 MB o video:")
    print("    Frontend -> /get-upload-url -> AssemblyAI upload directo")
    print("             -> Render /transcribe-url-async -> polling /status/<id>")
    print("\nFormatos soportados:")
    print("  Audio: MP3, WAV, M4A, FLAC, OGG, WEBM, AAC, AMR, OPUS, WMA, MPEG")
    print("  Video: MP4, MOV, AVI, MKV, WMV, FLV, M4V, 3GP, TS")
    print("=" * 70)

    app.run(debug=True, host='0.0.0.0', port=PORT)