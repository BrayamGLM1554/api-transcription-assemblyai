from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import time
import os
import re
import tempfile
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY', 'bfa9693c209840539fd901196346c4a6')
ASSEMBLYAI_BASE_URL = "https://api.assemblyai.com"
PORT = int(os.getenv('PORT', 5000))

headers = {
    "authorization": ASSEMBLYAI_API_KEY
}

# ─────────────────────────────────────────────────────────────────────────────
#  UPLOAD — stream a disco (evita colgarse con archivos grandes)
# ─────────────────────────────────────────────────────────────────────────────

def upload_audio_to_assemblyai(flask_file_storage):
    upload_url = f"{ASSEMBLYAI_BASE_URL}/v2/upload"

    suffix = os.path.splitext(flask_file_storage.filename or "audio.mp3")[1] or ".mp3"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = tmp.name
        flask_file_storage.save(tmp_path)

    size_mb = os.path.getsize(tmp_path) / 1024 / 1024
    print(f"  Temp: {tmp_path} ({size_mb:.1f} MB)")

    try:
        with open(tmp_path, "rb") as f:
            response = requests.post(upload_url, headers=headers, data=f)

        if response.status_code == 200:
            print(f"  Upload OK")
            return response.json()["upload_url"]

        raise Exception(f"Error al subir: {response.status_code} - {response.text}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ─────────────────────────────────────────────────────────────────────────────
#  TRANSCRIPCION
# ─────────────────────────────────────────────────────────────────────────────

def transcribe_audio_with_entities(audio_url):
    transcript_url = f"{ASSEMBLYAI_BASE_URL}/v2/transcript"

    data = {
        "audio_url": audio_url,

        # Igual que transcription_api_v2.py (funciona en produccion)
        "language_detection": True,
        "speech_models": ["universal-3-pro", "universal-2"],
        "language_confidence_threshold": 0.7,
        "boost_param": "high",
        "punctuate": True,
        "format_text": True,
        "speaker_labels": True,
        "filter_profanity": False,
        "redact_pii": False,

        # Extra para cabildo
        "entity_detection": True,
        "speakers_expected": None,
    }

    response = requests.post(transcript_url, json=data, headers=headers)
    if response.status_code == 200:
        transcript_id = response.json()['id']
        print(f"  Transcripcion iniciada: {transcript_id}")
        return transcript_id

    raise Exception(f"Error al iniciar transcripcion: {response.status_code} - {response.text}")


# ─────────────────────────────────────────────────────────────────────────────
#  POLLING
# ─────────────────────────────────────────────────────────────────────────────

def get_transcription_status(transcript_id):
    """Consulta estado UNA vez — el front hace polling cada 3s."""
    polling_endpoint = f"{ASSEMBLYAI_BASE_URL}/v2/transcript/{transcript_id}"
    response = requests.get(polling_endpoint, headers=headers)
    result = response.json()
    status = result['status']

    if status == 'completed':
        return {
            "status": "completed",
            "text": result.get('text', ''),
            "utterances": result.get('utterances', []),
            "entities": result.get('entities', []),
            "language_code": result.get('language_code'),
            "confidence": result.get('confidence'),
            "audio_duration": result.get('audio_duration'),
        }
    elif status == 'error':
        return {"status": "error", "error": result.get('error', 'Error desconocido')}
    else:
        return {"status": "processing", "message": f"Estado AssemblyAI: {status}"}


def poll_until_done(transcript_id):
    """Polling bloqueante para endpoint sincrono."""
    polling_endpoint = f"{ASSEMBLYAI_BASE_URL}/v2/transcript/{transcript_id}"
    while True:
        response = requests.get(polling_endpoint, headers=headers)
        result = response.json()
        status = result['status']

        if status == 'completed':
            return {
                "status": "completed",
                "text": result.get('text', ''),
                "utterances": result.get('utterances', []),
                "entities": result.get('entities', []),
                "language_code": result.get('language_code'),
                "confidence": result.get('confidence'),
                "audio_duration": result.get('audio_duration'),
            }
        elif status == 'error':
            return {"status": "error", "error": result.get('error', 'Error desconocido')}
        else:
            time.sleep(3)


# ─────────────────────────────────────────────────────────────────────────────
#  SPEAKER MAPPING — detecta nombres reales, rechaza frases genéricas
# ─────────────────────────────────────────────────────────────────────────────

# Palabras que NUNCA forman parte de un nombre de persona
STOP_WORDS = {
    'municipal', 'constitucional', 'general', 'jurídico', 'jurídica',
    'hacendario', 'hacendaria', 'ordinaria', 'extraordinaria', 'honorable',
    'secretaria', 'secretario', 'para', 'que', 'los', 'las', 'del', 'de',
    'la', 'el', 'comentar', 'informar', 'brindar', 'sugiere', 'propone',
    'comenta', 'señora', 'señor', 'ciudadana', 'ciudadano', 'este', 'esta',
    'iniciativa', 'reglamento', 'sesión', 'cabildo', 'agua', 'potable',
    'organismo', 'administración', 'comisión', 'fraccionamientos', 'cargo',
    'carácter', 'efecto', 'objeto', 'manera', 'forma', 'parte', 'caso',
    'orden', 'día', 'punto', 'acta', 'anterior', 'lectura', 'siguiente',
    'presente', 'presidenta', 'presidente', 'moderadora', 'moderador',
}

# Apellidos comunes en México
APELLIDOS = {
    'García', 'González', 'Hernández', 'López', 'Martínez', 'Pérez',
    'Ramírez', 'Rodríguez', 'Sánchez', 'Torres', 'Flores', 'Rivera',
    'Gómez', 'Díaz', 'Reyes', 'Cruz', 'Morales', 'Jiménez', 'Gutiérrez',
    'Chávez', 'Medrano', 'Miranda', 'Tobar', 'Mendoza', 'Velázquez',
    'Cornejo', 'Larios', 'Altamirano', 'Godínez', 'Ayala', 'Salazar',
    'Ángeles', 'Hurtado', 'Monterrubio', 'Zelayno', 'Fuentes', 'Cortés',
    'Quadrini', 'Medina', 'León', 'Celerino', 'Fernández',
}

# Nombres propios frecuentes
NOMBRES_PROPIOS = {
    'Jocelyn', 'María', 'Isabel', 'Jaime', 'Eugenio', 'Rosario', 'Jesús',
    'Arturo', 'Jennifer', 'César', 'Belinda', 'Edgar', 'Lisette', 'Fidel',
    'Sadi', 'Yanis', 'Melitón', 'Adelir', 'Rubí', 'Eva', 'Marta', 'Delia',
    'Osvaldo', 'Antonio', 'Enrique', 'Juan', 'Alberto', 'José', 'Manuel',
    'Yeri', 'Axili', 'Aksidy', 'Paola', 'Rogelio', 'Fernanda', 'Higinio',
}

# Patrón base: captura hasta 4 palabras con mayúscula (nombres reales)
_NOM = r'([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+(?:de\s+|del\s+|la\s+)?[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,3})'

# Patrones de cesión de palabra — de más específico a más general
PATRONES_CESION = [
    # "hace uso de la voz [rol?] Nombre Apellido"
    rf'(?:hace?\s+uso\s+de\s+la\s+voz|uso\s+de\s+la\s+voz)\s+'
    rf'(?:de\s+)?(?:el|la)?\s*'
    rf'(?:regidor|regidora|síndico|síndica|secretaria|secretario|'
    rf'presidente|presidenta|ingeniero|ingeniera|licenciado|licenciada|'
    rf'doctor|doctora|coordinadora|director|directora|profesor|profesora)?\s*'
    rf'{_NOM}',

    # "solicita el uso de la voz [la|el] [rol?] Nombre"
    rf'solicita?\s+(?:el\s+)?uso\s+de\s+(?:la\s+)?voz\s+'
    rf'(?:la|el)?\s*'
    rf'(?:regidor|regidora|síndico|síndica|secretaria|presidenta|presidente)?\s*'
    rf'{_NOM}',

    # "cede la palabra a Nombre"
    rf'cede?\s+(?:la\s+)?palabra\s+(?:a|al|a\s+la)?\s*{_NOM}',

    # "regidor/regidora Nombre Apellido"
    rf'(?:regidor|regidora)\s+(?:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+)?{_NOM}',

    # "síndico/síndica jurídico/hacendario Nombre Apellido"
    rf'(?:síndico|síndica)\s+(?:jurídico|jurídica|hacendario|hacendaria)\s+{_NOM}',

    # "ingeniero/a | licenciado/a | doctor/a | profesor/a Nombre Apellido"
    rf'(?:ingeniero|ingeniera|licenciado|licenciada|doctor|doctora|'
    rf'profesor|profesora)\s+{_NOM}',
]


def _es_nombre_real(texto: str) -> bool:
    """
    Valida que el texto capturado sea un nombre real de persona
    y no una frase genérica del discurso.
    """
    palabras = texto.strip().split()

    # Demasiado largo → es una frase, no un nombre
    if len(palabras) > 5 or len(palabras) == 0:
        return False

    # Contiene alguna stop word → frase de contexto, no nombre
    if any(p.lower() in STOP_WORDS for p in palabras):
        return False

    # Debe tener al menos un apellido o nombre conocido
    tiene_apellido = any(p in APELLIDOS for p in palabras)
    tiene_nombre   = any(p in NOMBRES_PROPIOS for p in palabras)

    return tiene_apellido or tiene_nombre


def extract_speaker_names_from_entities(utterances: list, entities: list) -> dict:
    """
    Detecta nombres reales cuando se cede la palabra en sesión de cabildo.

    Lógica:
      1. Recorre cada utterance buscando patrones de cesión.
      2. Extrae el candidato a nombre con regex limitado.
      3. Valida con _es_nombre_real() para rechazar frases genéricas.
      4. Asigna el nombre detectado al SIGUIENTE hablante.
    """
    speaker_mapping: dict = {}

    for i, utterance in enumerate(utterances):
        speaker = utterance.get('speaker', '')
        text    = utterance.get('text', '')

        for patron in PATRONES_CESION:
            match = re.search(patron, text, re.IGNORECASE)
            if not match:
                continue

            nombre_raw = match.group(1).strip()

            if not _es_nombre_real(nombre_raw):
                print(f"  ⚠️  Rechazado (no es nombre): '{nombre_raw}'")
                continue

            # Asignar al siguiente hablante
            if i + 1 < len(utterances):
                next_speaker = utterances[i + 1]['speaker']
                # Preferir el nombre más largo/completo si ya había uno
                if (next_speaker not in speaker_mapping or
                        len(nombre_raw) > len(speaker_mapping[next_speaker])):
                    speaker_mapping[next_speaker] = nombre_raw
                    print(f"  ✅ Speaker {next_speaker} = '{nombre_raw}'")

    return speaker_mapping


def format_transcript_with_speakers(utterances: list, speaker_mapping: dict) -> str:
    lines = []
    for utterance in utterances:
        speaker_id   = utterance.get('speaker', '?')
        text         = utterance.get('text', '')
        speaker_name = speaker_mapping.get(speaker_id, f"Speaker {speaker_id}")
        lines.append(f"{speaker_name}: {text}")
    return "\n\n".join(lines)


def build_success_payload(raw_result: dict) -> dict:
    utterances      = raw_result.get('utterances', [])
    entities        = raw_result.get('entities', [])
    speaker_mapping = extract_speaker_names_from_entities(utterances, entities)
    formatted_text  = format_transcript_with_speakers(utterances, speaker_mapping)
    raw_result['formatted_text']  = formatted_text
    raw_result['speaker_mapping'] = speaker_mapping
    raw_result['total_speakers']  = len(set(u['speaker'] for u in utterances))
    return raw_result


# ─────────────────────────────────────────────────────────────────────────────
#  ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "message": "API de transcripcion para cabildos",
        "version": "4.5.0"
    }), 200


@app.route('/transcribe-cabildo', methods=['POST'])
def transcribe_cabildo():
    try:
        if 'audio' not in request.files:
            return jsonify({"status": "error", "message": "No se encontro archivo de audio"}), 400

        audio_file = request.files['audio']
        print(f"\nArchivo: {audio_file.filename}")

        print("Subiendo...")
        audio_url = upload_audio_to_assemblyai(audio_file)

        print("Transcribiendo...")
        transcript_id = transcribe_audio_with_entities(audio_url)

        print("Esperando resultado...")
        raw = poll_until_done(transcript_id)

        if raw['status'] == 'completed':
            result = build_success_payload(raw)
            print(f"OK | Hablantes: {result['total_speakers']} | Nombres: {len(result['speaker_mapping'])}/{result['total_speakers']}")
        else:
            result = raw

        return jsonify(result), 200

    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/transcribe-cabildo-async', methods=['POST'])
def transcribe_cabildo_async():
    try:
        if 'audio' not in request.files:
            return jsonify({"status": "error", "message": "No se encontro archivo de audio"}), 400

        audio_file = request.files['audio']
        print(f"\nArchivo: {audio_file.filename}")

        print("Subiendo...")
        audio_url = upload_audio_to_assemblyai(audio_file)
        print("Audio subido OK")

        print("Iniciando transcripcion...")
        transcript_id = transcribe_audio_with_entities(audio_url)

        return jsonify({
            "status": "processing",
            "transcript_id": transcript_id,
            "message": f"Transcripcion iniciada. Consulta /status-cabildo/{transcript_id}"
        }), 202

    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/status-cabildo/<transcript_id>', methods=['GET'])
def get_status_cabildo(transcript_id):
    try:
        raw = get_transcription_status(transcript_id)

        if raw['status'] == 'completed':
            result = build_success_payload(raw)
            print(f"OK | Hablantes: {result['total_speakers']} | Nombres: {len(result['speaker_mapping'])}/{result['total_speakers']}")
            return jsonify(result), 200

        return jsonify(raw), 200

    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({"status": "error", "message": "Endpoint no encontrado"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"status": "error", "message": "Error interno del servidor"}), 500


if __name__ == '__main__':
    print("=" * 70)
    print("  API DE TRANSCRIPCION PARA SESIONES DE CABILDO v4.5")
    print("=" * 70)
    print(f"  Puerto : {PORT}")
    print(f"  API Key: {'Configurada' if ASSEMBLYAI_API_KEY else 'NO CONFIGURADA'}")
    print("=" * 70)
    print("  Endpoints:")
    print("    GET  /health                    - Health check")
    print("    POST /transcribe-cabildo         - Transcribir (sincrono)")
    print("    POST /transcribe-cabildo-async   - Iniciar transcripcion (asincrono)")
    print("    GET  /status-cabildo/<id>        - Consultar estado")
    print("=" * 70)

    app.run(debug=True, host='0.0.0.0', port=PORT)