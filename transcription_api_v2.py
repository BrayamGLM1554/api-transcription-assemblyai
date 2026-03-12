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

app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024 * 1024  # 4GB

ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY', '5f5fcdb5a90a4a128a5ccc5b399a250b')
ASSEMBLYAI_BASE_URL = "https://api.assemblyai.com"
PORT = int(os.getenv('PORT', 5000))

headers = {
    "authorization": ASSEMBLYAI_API_KEY
}2


def upload_audio_to_assemblyai(audio_file):
    """Sube el archivo de audio/video a AssemblyAI y retorna la URL"""
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
        raise Exception(f"Error al subir el archivo a AssemblyAI (HTTP {response.status_code}): {response.text}")


def transcribe_audio(audio_url, quality_mode="maximum", custom_vocabulary=None):
    transcript_url = f"{ASSEMBLYAI_BASE_URL}/v2/transcript"

    data = {
        "audio_url": audio_url,
        "language_detection": True,
        "speech_models": ["universal-3-pro", "universal-2"],
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
        raise Exception(f"Error al iniciar transcripcion (HTTP {response.status_code}): {response.text}")


def get_transcription_result(transcript_id):
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


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "message": "API de transcripcion funcionando",
        "version": "3.1.0 - High Accuracy (>97%)"
    }), 200


@app.route('/transcribe', methods=['POST'])
def transcribe():
    try:
        if 'audio' not in request.files:
            return jsonify({"status": "error", "message": "No se encontro archivo. Usa la key 'audio' en form-data"}), 400

        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"status": "error", "message": "El archivo no tiene nombre"}), 400

        allowed_extensions = (
            '.mp3', '.mp4', '.wav', '.m4a', '.flac', '.ogg',
            '.webm', '.aac', '.amr', '.opus', '.wma',
            '.mov', '.avi', '.mkv', '.wmv', '.flv', '.m4v', '.3gp', '.ts', '.mts'
        )
        if not audio_file.filename.lower().endswith(allowed_extensions):
            return jsonify({"status": "error", "message": f"Formato no soportado. Usa: {', '.join(allowed_extensions)}"}), 400

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


@app.route('/transcribe-url', methods=['POST'])
def transcribe_from_url():
    try:
        data = request.get_json()
        if not data or 'audio_url' not in data:
            return jsonify({"status": "error", "message": "Debes proporcionar 'audio_url' en el body JSON"}), 400

        audio_url = data['audio_url']
        quality_mode = data.get('quality', 'maximum')
        custom_vocabulary = data.get('vocabulary', None)

        transcript_id = transcribe_audio(audio_url, quality_mode, custom_vocabulary)
        result = get_transcription_result(transcript_id)
        return jsonify(result), 200

    except Exception as e:
        print(f"[ERROR /transcribe-url] {str(e)}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/transcribe-async', methods=['POST'])
def transcribe_async():
    print("\n" + "=" * 50)
    print("[/transcribe-async] Nueva solicitud recibida")
    print(f"  Content-Type : {request.content_type}")
    print(f"  Content-Length: {request.content_length} bytes ({(request.content_length or 0) / 1024 / 1024:.2f} MB)")
    print(f"  Files        : {list(request.files.keys())}")
    print(f"  Form fields  : {list(request.form.keys())}")

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
                print("  [ERROR] El archivo no tiene nombre")
                return jsonify({"status": "error", "message": "El archivo no tiene nombre"}), 400

            allowed_extensions = (
                '.mp3', '.mp4', '.wav', '.m4a', '.flac', '.ogg',
                '.webm', '.aac', '.amr', '.opus', '.wma', '.mpeg', '.mpga', '.mp2',
                '.mov', '.avi', '.mkv', '.wmv', '.flv', '.m4v', '.3gp', '.ts', '.mts'
            )
            ext = os.path.splitext(filename.lower())[1]
            print(f"  [FILE] Extension detectada: '{ext}'")

            if ext not in allowed_extensions:
                print(f"  [ERROR] Extension '{ext}' no esta en la lista permitida")
                return jsonify({
                    "status": "error",
                    "message": f"Formato no soportado: '{ext}'. Formatos validos: {', '.join(allowed_extensions)}"
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
                print("  [ERROR] El archivo esta vacio (0 bytes)")
                return jsonify({"status": "error", "message": "El archivo esta vacio (0 bytes recibidos)"}), 400

            print("  [STEP 2] Subiendo a AssemblyAI...")
            audio_url = upload_audio_to_assemblyai(file_bytes)
            print(f"  [STEP 2] URL obtenida OK")

        # ── Rama 2: URL enviada en JSON ───────────────────────────────────────
        else:
            print("  [ROUTE] No se detecto archivo, intentando leer JSON...")
            data = request.get_json(silent=True)

            if data is None:
                print("  [ERROR] Body no es JSON valido y tampoco hay archivo")
                return jsonify({
                    "status": "error",
                    "message": "Proporciona un archivo 'audio' en form-data o 'audio_url' en JSON"
                }), 400

            print(f"  [JSON] Keys recibidas: {list(data.keys())}")

            if 'audio_url' not in data:
                print("  [ERROR] El JSON no contiene 'audio_url'")
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


@app.route('/status/<transcript_id>', methods=['GET'])
def get_status(transcript_id):
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
            return jsonify({"status": "processing", "message": f"Transcripcion en proceso (estado: {status})"}), 200

    except Exception as e:
        print(f"[ERROR /status] {str(e)}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({"status": "error", "message": "Endpoint no encontrado"}), 404


@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        "status": "error",
        "message": "El archivo supera el limite de 4 GB permitido por el servidor"
    }), 413


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"status": "error", "message": "Error interno del servidor"}), 500


if __name__ == '__main__':
    print("=" * 70)
    print("API DE TRANSCRIPCION - ALTA PRECISION (>97% CONFIABILIDAD)")
    print("=" * 70)
    print(f"Puerto : {PORT}")
    print(f"API Key : {'configurada' if ASSEMBLYAI_API_KEY else 'NO configurada'}")
    print("=" * 70)
    print("\nEndpoints disponibles:")
    print("  GET  /health              - Health check")
    print("  POST /transcribe          - Transcribir archivo (sincrono)")
    print("  POST /transcribe-url      - Transcribir desde URL (sincrono)")
    print("  POST /transcribe-async    - Iniciar transcripcion (asincrono)")
    print("  GET  /status/<id>         - Consultar estado (asincrono)")
    print("\nFormatos soportados:")
    print("  Audio: MP3, WAV, M4A, FLAC, OGG, WEBM, AAC, AMR, OPUS, WMA, MPEG")
    print("  Video: MP4, MOV, AVI, MKV, WMV, FLV, M4V, 3GP, TS")
    print("=" * 70)

    app.run(debug=True, host='0.0.0.0', port=PORT)