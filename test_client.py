import requests
import sys

def test_health_check():
    """Prueba el endpoint de health check"""
    print("\n=== Probando Health Check ===")
    url = "http://localhost:5000/health"
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Respuesta: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_transcribe_file(audio_file_path):
    """Prueba la transcripción de un archivo local"""
    print(f"\n=== Probando Transcripción de Archivo ===")
    print(f"Archivo: {audio_file_path}")
    url = "http://localhost:5000/transcribe"
    
    try:
        with open(audio_file_path, 'rb') as f:
            files = {'audio': f}
            print("Enviando archivo...")
            response = requests.post(url, files=files)
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        
        if result['status'] == 'success':
            print(f"\n✅ Transcripción exitosa!")
            print(f"Idioma detectado: {result.get('language_code', 'N/A')}")
            print(f"Confianza: {result.get('confidence', 'N/A')}")
            print(f"\nTexto transcrito:")
            print("-" * 50)
            print(result['text'])
            print("-" * 50)
        else:
            print(f"\n❌ Error: {result.get('message', 'Error desconocido')}")
        
        return result['status'] == 'success'
        
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo {audio_file_path}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_transcribe_url(audio_url):
    """Prueba la transcripción desde una URL"""
    print(f"\n=== Probando Transcripción desde URL ===")
    print(f"URL: {audio_url}")
    url = "http://localhost:5000/transcribe-url"
    
    try:
        data = {"audio_url": audio_url}
        print("Enviando solicitud...")
        response = requests.post(url, json=data)
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        
        if result['status'] == 'success':
            print(f"\n✅ Transcripción exitosa!")
            print(f"Idioma detectado: {result.get('language_code', 'N/A')}")
            print(f"Confianza: {result.get('confidence', 'N/A')}")
            print(f"\nTexto transcrito:")
            print("-" * 50)
            print(result['text'])
            print("-" * 50)
        else:
            print(f"\n❌ Error: {result.get('message', 'Error desconocido')}")
        
        return result['status'] == 'success'
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("=" * 60)
    print("Cliente de Prueba - API de Transcripción")
    print("=" * 60)
    
    # Verificar que la API está corriendo
    if not test_health_check():
        print("\n⚠️  La API no está respondiendo. Asegúrate de que esté ejecutándose:")
        print("   python transcription_api.py")
        return
    
    print("\n¿Qué quieres probar?")
    print("1. Transcribir archivo local")
    print("2. Transcribir desde URL")
    print("3. Ambas (usar URL de ejemplo)")
    
    choice = input("\nSelecciona una opción (1-3): ").strip()
    
    if choice == "1":
        file_path = input("Ingresa la ruta del archivo de audio: ").strip()
        test_transcribe_file(file_path)
        
    elif choice == "2":
        audio_url = input("Ingresa la URL del audio: ").strip()
        if not audio_url:
            audio_url = "https://assembly.ai/wildfires.mp3"
            print(f"Usando URL de ejemplo: {audio_url}")
        test_transcribe_url(audio_url)
        
    elif choice == "3":
        # Usar URL de ejemplo
        audio_url = "https://assembly.ai/wildfires.mp3"
        test_transcribe_url(audio_url)
        
    else:
        print("Opción no válida")
    
    print("\n" + "=" * 60)
    print("Prueba completada")
    print("=" * 60)

if __name__ == "__main__":
    main()
