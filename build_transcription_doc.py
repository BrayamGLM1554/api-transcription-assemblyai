from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from datetime import datetime

doc = Document()
for section in doc.sections:
    section.top_margin    = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin   = Cm(2.5)
    section.right_margin  = Cm(2.5)

C_DARK     = RGBColor(0x00, 0x3B, 0x7E)
C_MID      = RGBColor(0x19, 0x76, 0xD2)
C_GRAY     = RGBColor(0x74, 0x85, 0x98)
C_BLACK    = RGBColor(0x1A, 0x20, 0x2C)
C_WHITE    = RGBColor(0xFF, 0xFF, 0xFF)
C_BLUE_LT  = RGBColor(0xE3, 0xF0, 0xFB)
C_CODE_TXT = RGBColor(0x63, 0xB3, 0xED)
C_TEAL     = RGBColor(0x00, 0xBC, 0xD4)
C_COVER_LT = RGBColor(0xA0, 0xC4, 0xF1)

def set_cell_bg(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd  = OxmlElement('w:shd')
    shd.set(qn('w:val'),   'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'),  hex_color)
    tcPr.append(shd)

def set_cell_borders(cell, color="CCCCCC"):
    tcPr    = cell._tc.get_or_add_tcPr()
    tcBdrs  = OxmlElement('w:tcBorders')
    for side in ['top','left','bottom','right']:
        b = OxmlElement(f'w:{side}')
        b.set(qn('w:val'),   'single')
        b.set(qn('w:sz'),    '4')
        b.set(qn('w:space'), '0')
        b.set(qn('w:color'), color)
        tcBdrs.append(b)
    tcPr.append(tcBdrs)

def set_cell_margins(cell, top=80, bottom=80, left=120, right=120):
    tcPr  = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for side, val in [('top',top),('left',left),('bottom',bottom),('right',right)]:
        m = OxmlElement(f'w:{side}')
        m.set(qn('w:w'),    str(val))
        m.set(qn('w:type'), 'dxa')
        tcMar.append(m)
    tcPr.append(tcMar)

def heading(level, text):
    styles = {1:'Heading 1', 2:'Heading 2', 3:'Heading 3'}
    p   = doc.add_paragraph(style=styles.get(level,'Normal'))
    run = p.add_run(text)
    run.bold = True
    run.font.name = 'Arial'
    run.font.color.rgb = {1:C_DARK, 2:C_MID, 3:C_DARK}.get(level, C_DARK)
    run.font.size      = Pt({1:16, 2:13, 3:11}.get(level, 11))
    return p

def para(text, bold=False, italic=False, size=10.5, color=None, align=None):
    p   = doc.add_paragraph(style='Normal')
    if align: p.alignment = align
    run = p.add_run(text)
    run.bold    = bold
    run.italic  = italic
    run.font.name      = 'Arial'
    run.font.size      = Pt(size)
    run.font.color.rgb = color if color else C_BLACK
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after  = Pt(3)
    return p

def bullet(text):
    p   = doc.add_paragraph(style='List Bullet')
    run = p.add_run(text)
    run.font.name      = 'Arial'
    run.font.size      = Pt(10.5)
    run.font.color.rgb = C_BLACK
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after  = Pt(2)
    return p

def spacer(pts=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(pts)
    p.paragraph_format.space_after  = Pt(0)

def divider():
    p    = doc.add_paragraph()
    pPr  = p._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bot  = OxmlElement('w:bottom')
    bot.set(qn('w:val'),   'single')
    bot.set(qn('w:sz'),    '6')
    bot.set(qn('w:space'), '1')
    bot.set(qn('w:color'), '1976D2')
    pBdr.append(bot)
    pPr.append(pBdr)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after  = Pt(6)

def code_block(lines):
    tbl  = doc.add_table(rows=1, cols=1)
    tbl.style = 'Table Grid'
    cell = tbl.rows[0].cells[0]
    set_cell_bg(cell, '1E2535')
    set_cell_margins(cell, 100, 100, 150, 150)
    cell._tc.clear_content()
    for line in lines:
        p   = cell.add_paragraph()
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after  = Pt(1)
        run = p.add_run(line)
        run.font.name      = 'Courier New'
        run.font.size      = Pt(9)
        run.font.color.rgb = C_CODE_TXT
    spacer(4)

def make_table(headers, rows, col_widths_cm):
    tbl = doc.add_table(rows=1+len(rows), cols=len(headers))
    tbl.style     = 'Table Grid'
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    for i, w in enumerate(col_widths_cm):
        for row in tbl.rows:
            row.cells[i].width = Cm(w)
    hdr = tbl.rows[0]
    for i, h in enumerate(headers):
        cell = hdr.cells[i]
        set_cell_bg(cell, '003B7E')
        set_cell_margins(cell)
        run = cell.paragraphs[0].add_run(h)
        run.bold = True; run.font.name = 'Arial'
        run.font.size = Pt(9.5); run.font.color.rgb = C_WHITE
    for ri, row_data in enumerate(rows):
        row = tbl.rows[ri+1]
        bg  = 'FFFFFF' if ri % 2 == 0 else 'F0F4FA'
        for ci, cell_text in enumerate(row_data):
            cell = row.cells[ci]
            set_cell_bg(cell, bg)
            set_cell_margins(cell)
            run = cell.paragraphs[0].add_run(cell_text)
            run.font.name = 'Arial'; run.font.size = Pt(9.5)
            run.font.color.rgb = C_BLACK
    spacer(4)

def http_badge(method, endpoint, description):
    colors = {'POST':'276749','GET':'1976D2','PUT':'C05621','DELETE':'9B2335'}
    bg = colors.get(method,'1976D2')
    tbl = doc.add_table(rows=1, cols=3)
    tbl.style = 'Table Grid'
    for i, w in enumerate([2.0, 5.5, 8.0]):
        tbl.rows[0].cells[i].width = Cm(w)
    c0 = tbl.rows[0].cells[0]
    set_cell_bg(c0, bg); set_cell_margins(c0)
    p0 = c0.paragraphs[0]; p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r0 = p0.add_run(method)
    r0.bold=True; r0.font.name='Arial'; r0.font.size=Pt(10); r0.font.color.rgb=C_WHITE
    c1 = tbl.rows[0].cells[1]
    set_cell_bg(c1,'F0F4FA'); set_cell_margins(c1)
    r1 = c1.paragraphs[0].add_run(endpoint)
    r1.bold=True; r1.font.name='Courier New'; r1.font.size=Pt(9.5); r1.font.color.rgb=C_DARK
    c2 = tbl.rows[0].cells[2]
    set_cell_bg(c2,'FFFFFF'); set_cell_margins(c2)
    r2 = c2.paragraphs[0].add_run(description)
    r2.font.name='Arial'; r2.font.size=Pt(9.5); r2.font.color.rgb=C_GRAY
    spacer(4)

# ═══════════════════════════════════════════════════════════════════════
# PORTADA
# ═══════════════════════════════════════════════════════════════════════
tbl_c = doc.add_table(rows=1, cols=1)
tbl_c.style = 'Table Grid'
cc = tbl_c.rows[0].cells[0]
set_cell_bg(cc, '003B7E')
set_cell_margins(cc, 300, 300, 300, 300)
cc._tc.clear_content()
for txt, sz, bld, col in [
    ('DOCUMENTACION TECNICA', 11, True, C_COVER_LT),
    ('Sistema de Transcripcion Automatica', 20, True, C_WHITE),
    ('STA', 36, True, C_TEAL),
    ('API de Transcripcion  -  AssemblyAI Integration', 13, False, C_COVER_LT),
]:
    pp = cc.add_paragraph(); pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rr = pp.add_run(txt)
    rr.bold=bld; rr.font.name='Arial'; rr.font.size=Pt(sz); rr.font.color.rgb=col
cc.paragraphs[0].paragraph_format.space_before = Pt(10)
cc.paragraphs[-1].paragraph_format.space_after = Pt(10)

spacer(8)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('Modulo: transcription_api_v2  -  Flask + AssemblyAI')
r.bold=True; r.font.name='Arial'; r.font.size=Pt(12); r.font.color.rgb=C_DARK
spacer(6); divider(); spacer(6)

p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('Desarrollado por')
r.bold=True; r.font.name='Arial'; r.font.size=Pt(11); r.font.color.rgb=C_GRAY
spacer(4)

dt = doc.add_table(rows=1, cols=3)
dt.style = 'Table Grid'; dt.alignment = WD_TABLE_ALIGNMENT.CENTER
for i,(l1,l2) in enumerate([('Ing. Brayam Gilberto','Lopez Morales'),('Ing. Arturo Darinel','Lopez Castillo'),('Ing. Juan Mateo','Hernandez de Luna')]):
    dc = dt.rows[0].cells[i]; dc.width = Cm(5.3)
    set_cell_bg(dc,'E3F0FB'); set_cell_borders(dc,'1976D2'); set_cell_margins(dc,120,120,120,120)
    dc._tc.clear_content()
    pp = dc.add_paragraph(); pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rr = pp.add_run(l1); rr.bold=True; rr.font.name='Arial'; rr.font.size=Pt(10); rr.font.color.rgb=C_DARK
    pp = dc.add_paragraph(); pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rr = pp.add_run(l2); rr.font.name='Arial'; rr.font.size=Pt(10); rr.font.color.rgb=C_DARK

spacer(8)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('Fecha: ' + datetime.now().strftime('%d de %B de %Y'))
r.font.name='Arial'; r.font.size=Pt(10); r.font.color.rgb=C_GRAY
doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════
# 1. INTRODUCCION
# ═══════════════════════════════════════════════════════════════════════
heading(1,'1. Introduccion')
para('La API de Transcripcion Automatica de STA es un servicio REST desarrollado con Flask (Python) que permite transcribir archivos de audio de alta duracion utilizando la plataforma AssemblyAI. El servicio expone endpoints sincronos y asincronos, soporta multiples formatos de audio, ofrece modos de calidad configurables y esta disenado para ser consumido por el frontend React del sistema STA.')
spacer()
heading(2,'1.1 Proposito')
para('Proveer un backend de transcripcion robusto y de alta precision para:')
bullet('Transcribir archivos de audio subidos directamente (hasta 500 MB).')
bullet('Transcribir audio desde URLs publicas.')
bullet('Soportar transcripciones asincronas para audios de larga duracion (hasta 4 horas).')
bullet('Retornar texto, codigo de idioma detectado, nivel de confianza e informacion de hablantes.')
bullet('Operar en tres modos de calidad: standard, high y maximum.')
spacer()
heading(2,'1.2 Alcance')
para('Este documento cubre la API de transcripcion (transcription_api_v2.py). No incluye el modulo de autenticacion ni la interfaz de usuario React del sistema STA.')
spacer(); divider(); doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════
# 2. ARQUITECTURA
# ═══════════════════════════════════════════════════════════════════════
heading(1,'2. Arquitectura del Proyecto')
spacer()
heading(2,'2.1 Estructura de Archivos')
code_block([
    'API_AssemblyAI/',
    '  transcription_api_v2.py   # API principal (Flask)',
    '  requirements.txt          # Dependencias Python',
    '  runtime.txt               # Version de Python (3.11.0)',
    '  README.md                 # Documentacion basica',
    '  .env                      # Variables de entorno (no en repo)',
    '  .venv/                    # Entorno virtual Python',
])
spacer()
heading(2,'2.2 Stack Tecnologico')
make_table(['Tecnologia','Version','Rol'],
[['Python','3.11.0','Lenguaje de programacion'],
 ['Flask','3.0.0','Framework web / API REST'],
 ['flask-cors','4.0.0','Soporte CORS para frontend'],
 ['requests','2.31.0','Cliente HTTP para AssemblyAI'],
 ['python-dotenv','1.0.0','Carga de variables de entorno'],
 ['gunicorn','21.2.0','Servidor WSGI para produccion'],
 ['AssemblyAI','API v2','Motor de transcripcion IA'],
],[4,3,8.5])
spacer()
heading(2,'2.3 Flujo de Operacion')
para('El flujo general de una transcripcion es el siguiente:')
bullet('El cliente envia el archivo de audio o URL al endpoint correspondiente.')
bullet('La API sube el audio al servidor de AssemblyAI mediante POST /v2/upload.')
bullet('Se inicia el trabajo de transcripcion enviando la configuracion a POST /v2/transcript.')
bullet('En modo sincrono, la API realiza polling a GET /v2/transcript/{id} hasta completar.')
bullet('En modo asincrono, se retorna el transcript_id inmediatamente para consultas posteriores.')
bullet('El resultado final incluye texto, idioma detectado, confianza y datos de hablantes.')
spacer(); divider(); doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════
# 3. CONFIGURACION
# ═══════════════════════════════════════════════════════════════════════
heading(1,'3. Configuracion e Instalacion')
heading(2,'3.1 Requisitos Previos')
bullet('Python 3.11.0 instalado.')
bullet('Cuenta activa en AssemblyAI con API Key valida.')
bullet('pip (gestor de paquetes Python).')
spacer()
heading(2,'3.2 Crear Entorno Virtual')
code_block([
    '# Windows',
    'python -m venv .venv',
    '.venv\\Scripts\\activate',
    '',
    '# Linux / macOS',
    'python3 -m venv .venv',
    'source .venv/bin/activate',
])
spacer()
heading(2,'3.3 Instalar Dependencias')
code_block(['pip install -r requirements.txt'])
spacer()
para('Contenido de requirements.txt:')
code_block([
    'Flask==3.0.0',
    'flask-cors==4.0.0',
    'requests==2.31.0',
    'python-dotenv==1.0.0',
    'gunicorn==21.2.0',
])
spacer()
heading(2,'3.4 Variables de Entorno (.env)')
para('Crear el archivo .env en la raiz del proyecto:')
code_block([
    'ASSEMBLYAI_API_KEY=tu_api_key_de_assemblyai',
    'PORT=5000',
])
make_table(['Variable','Descripcion','Requerida'],
[['ASSEMBLYAI_API_KEY','Clave de autenticacion de la API de AssemblyAI','Si'],
 ['PORT','Puerto en el que escucha el servidor (default: 5000)','No'],
],[5,8,2.5])
spacer()
para('Nota: Si no se crea el archivo .env, la API intentara usar la clave hardcodeada como fallback. Para produccion siempre usar variables de entorno.', italic=True, color=C_GRAY)
spacer()
heading(2,'3.5 Iniciar el Servidor')
para('Modo desarrollo:')
code_block(['python transcription_api_v2.py'])
para('Modo produccion con Gunicorn:')
code_block([
    'pip install gunicorn',
    'gunicorn -w 4 -b 0.0.0.0:5000 transcription_api_v2:app',
])
para('Salida esperada al iniciar:')
code_block([
    '====================================================================',
    'API DE TRANSCRIPCION - ALTA PRECISION (>97% CONFIABILIDAD)',
    '====================================================================',
    'Puerto: 5000',
    'API Key configurada: Si',
    '====================================================================',
    'Endpoints disponibles:',
    '  GET  /health',
    '  POST /transcribe',
    '  POST /transcribe-url',
    '  POST /transcribe-async  (recomendado para audios largos)',
    '  GET  /status/<id>',
])
divider(); doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════
# 4. DESCRIPCION DE MODULOS
# ═══════════════════════════════════════════════════════════════════════
heading(1,'4. Descripcion de Funciones Internas')
spacer()
heading(2,'4.1 upload_audio_to_assemblyai(audio_file)')
para('Sube los bytes del archivo de audio al servidor de AssemblyAI mediante POST a /v2/upload.')
make_table(['Parametro','Tipo','Descripcion'],
[['audio_file','bytes','Contenido binario del archivo de audio leido con .read()'],
],[4,2.5,9])
para('Retorna: String con la URL temporal del audio en los servidores de AssemblyAI.')
para('Lanza Exception si el upload falla (status != 200).')
spacer()

heading(2,'4.2 transcribe_audio(audio_url, quality_mode, custom_vocabulary)')
para('Envia la configuracion de transcripcion a AssemblyAI e inicia el trabajo. Soporta tres modos de calidad y vocabulario personalizado.')
make_table(['Parametro','Tipo','Default','Descripcion'],
[['audio_url','str','Requerido','URL del audio en AssemblyAI o URL publica'],
 ['quality_mode','str','high','Modo de calidad: standard, high o maximum'],
 ['custom_vocabulary','list','None','Lista de palabras para reforzar el reconocimiento'],
],[3.5,2,2,8])
spacer()
heading(3,'Configuracion enviada a AssemblyAI')
make_table(['Parametro','Valor','Efecto'],
[['language_detection','True','Deteccion automatica del idioma del audio'],
 ['speech_models','universal-3-pro, universal-2','Modelos de mayor precision disponibles'],
 ['language_confidence_threshold','0.7','Umbral minimo de confianza para idioma'],
 ['boost_param','high','Preprocesamiento de audio para mayor claridad'],
 ['punctuate','True','Insercion automatica de puntuacion'],
 ['format_text','True','Formato de numeros, fechas y monedas'],
 ['speaker_labels','True','Identificacion de diferentes hablantes'],
 ['filter_profanity','False','Sin filtro (maximiza precision)'],
 ['word_boost','custom_vocabulary','Refuerzo de palabras especificas (si se provee)'],
],[4.5,3.5,7.5])
para('Retorna: String con el transcript_id asignado por AssemblyAI.')
spacer()

heading(2,'4.3 get_transcription_result(transcript_id)')
para('Realiza polling a GET /v2/transcript/{id} con intervalos de 3 segundos hasta obtener resultado. Se usa en los endpoints sincronos.')
make_table(['Estado AssemblyAI','Accion'],
[['queued / processing','Espera 3 segundos y reintenta'],
 ['completed','Retorna texto, idioma, confianza, palabras y utterances'],
 ['error','Retorna el mensaje de error de AssemblyAI'],
],[4,11.5])
spacer(); divider(); doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════
# 5. ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════
heading(1,'5. Referencia de Endpoints')
para('URL base del servidor local:')
code_block(['http://localhost:5000'])
spacer()

# 5.1 Health
heading(2,'5.1  GET /health - Health Check')
http_badge('GET','/health','Verifica que la API esta en linea')
heading(3,'Respuesta exitosa (200)')
code_block([
    '{',
    '  "status": "ok",',
    '  "message": "API de transcripcion funcionando",',
    '  "version": "3.0.0 - High Accuracy (>97%)"',
    '}',
])
spacer()

# 5.2 POST /transcribe
heading(2,'5.2  POST /transcribe - Transcripcion Sincrona (Archivo)')
http_badge('POST','/transcribe','Transcribe un archivo de audio. Espera hasta completar (sincrono)')
para('Recomendado para audios cortos (menos de 10 minutos). Para audios largos usar /transcribe-async.')
spacer()
heading(3,'Request - Form-data')
make_table(['Campo','Tipo','Requerido','Descripcion'],
[['audio','File','Si','Archivo de audio a transcribir'],
 ['quality','String','No','Modo de calidad: standard, high, maximum (default: maximum)'],
 ['vocabulary','String','No','Palabras clave separadas por comas para reforzar reconocimiento'],
],[2.5,2,2,9])
spacer()
heading(3,'Formatos de audio soportados')
para('MP3, MP4, WAV, M4A, FLAC, OGG, WEBM, AAC, AMR, OPUS, WMA')
spacer()
heading(3,'Ejemplo con cURL')
code_block([
    'curl -X POST http://localhost:5000/transcribe \\',
    '  -F "audio=@/ruta/al/audio.mp3" \\',
    '  -F "quality=maximum" \\',
    '  -F "vocabulary=AssemblyAI,transcripcion,STA"',
])
heading(3,'Ejemplo con Python')
code_block([
    'import requests',
    '',
    'url   = "http://localhost:5000/transcribe"',
    'files = {"audio": open("mi_audio.mp3", "rb")}',
    'data  = {"quality": "maximum"}',
    'res   = requests.post(url, files=files, data=data)',
    'print(res.json())',
])
heading(3,'Respuestas')
make_table(['Codigo','Condicion','Cuerpo de respuesta (resumen)'],
[['200 OK','Transcripcion exitosa','{ "status":"success", "text":"...", "language_code":"es", "confidence":0.97, "words":[...], "utterances":[...], "audio_duration":120 }'],
 ['400 Bad Request','Sin archivo audio','{ "status":"error", "message":"No se encontro ningun archivo de audio" }'],
 ['400 Bad Request','Archivo sin nombre','{ "status":"error", "message":"El archivo no tiene nombre" }'],
 ['400 Bad Request','Formato invalido','{ "status":"error", "message":"Formato de archivo no soportado..." }'],
 ['500 Internal Error','Falla en AssemblyAI','{ "status":"error", "message":"<detalle>" }'],
],[2,3.5,10])
spacer()

# 5.3 POST /transcribe-url
heading(2,'5.3  POST /transcribe-url - Transcripcion Sincrona (URL)')
http_badge('POST','/transcribe-url','Transcribe audio desde una URL publica (sincrono)')
spacer()
heading(3,'Request - JSON Body')
make_table(['Campo','Tipo','Requerido','Descripcion'],
[['audio_url','String','Si','URL publica del archivo de audio'],
 ['quality','String','No','Modo de calidad (default: maximum)'],
 ['vocabulary','Array','No','Lista de palabras: ["palabra1","palabra2"]'],
],[2.5,2,2,9])
spacer()
heading(3,'Ejemplo con cURL')
code_block([
    'curl -X POST http://localhost:5000/transcribe-url \\',
    '  -H "Content-Type: application/json" \\',
    '  -d \'{"audio_url": "https://ejemplo.com/audio.mp3", "quality": "maximum"}\'',
])
heading(3,'Ejemplo con Python')
code_block([
    'import requests',
    '',
    'url  = "http://localhost:5000/transcribe-url"',
    'data = {',
    '    "audio_url":  "https://ejemplo.com/audio.mp3",',
    '    "quality":    "maximum",',
    '    "vocabulary": ["AssemblyAI", "transcripcion"]',
    '}',
    'res = requests.post(url, json=data)',
    'print(res.json())',
])
heading(3,'Respuestas')
make_table(['Codigo','Condicion','Respuesta'],
[['200 OK','Exito','{ "status":"success", "text":"...", "language_code":"es", "confidence":0.97 }'],
 ['400 Bad Request','Sin audio_url','{ "status":"error", "message":"Debes proporcionar audio_url en el body JSON" }'],
 ['500 Internal Error','Error AssemblyAI','{ "status":"error", "message":"<detalle>" }'],
],[2,3.5,10])
spacer()

# 5.4 POST /transcribe-async
heading(2,'5.4  POST /transcribe-async - Transcripcion Asincrona (RECOMENDADO)')
http_badge('POST','/transcribe-async','Inicia transcripcion y retorna transcript_id inmediatamente')
para('Endpoint recomendado para audios mayores a 10 minutos. El cliente recibe el transcript_id y consulta el estado con GET /status/{id}. El frontend STA usa este endpoint.')
spacer()
heading(3,'Request - Form-data (archivo) o JSON (URL)')
make_table(['Campo','Tipo','Requerido','Descripcion'],
[['audio','File','Si*','Archivo de audio (* o usar audio_url)'],
 ['audio_url','String','Si*','URL del audio (* o usar archivo)'],
 ['quality','String','No','Modo de calidad (default: maximum)'],
 ['vocabulary','String/Array','No','Palabras clave separadas por coma o array JSON'],
],[2.5,2,2,9])
spacer()
heading(3,'Formatos soportados (asincrono)')
para('MP3, MP4, WAV, M4A, FLAC, OGG, WEBM, AAC, AMR, OPUS, WMA, MPEG, MPGA, MP2')
spacer()
heading(3,'Ejemplo con archivo')
code_block([
    'curl -X POST http://localhost:5000/transcribe-async \\',
    '  -F "audio=@conferencia.mp3" \\',
    '  -F "quality=maximum"',
])
heading(3,'Ejemplo con URL')
code_block([
    'curl -X POST http://localhost:5000/transcribe-async \\',
    '  -H "Content-Type: application/json" \\',
    '  -d \'{"audio_url": "https://ejemplo.com/audio.mp3"}\'',
])
heading(3,'Respuesta exitosa (202 Accepted)')
code_block([
    '{',
    '  "status":        "processing",',
    '  "transcript_id": "abc123xyz",',
    '  "quality_mode":  "maximum",',
    '  "message":       "Transcripcion iniciada. Usa /status/{transcript_id} para consultar"',
    '}',
])
make_table(['Codigo','Condicion','Respuesta'],
[['202 Accepted','Transcripcion iniciada','{ "status":"processing", "transcript_id":"...", "quality_mode":"..." }'],
 ['400 Bad Request','Sin archivo ni URL','{ "status":"error", "message":"Proporciona audio o audio_url" }'],
 ['400 Bad Request','Formato invalido','{ "status":"error", "message":"Formato no soportado..." }'],
 ['500 Internal Error','Error en upload','{ "status":"error", "message":"<detalle>" }'],
],[2,3.5,10])
spacer()

# 5.5 GET /status
heading(2,'5.5  GET /status/{transcript_id} - Consultar Estado')
http_badge('GET','/status/{transcript_id}','Consulta el estado de una transcripcion asincrona')
spacer()
heading(3,'Parametro de ruta')
make_table(['Parametro','Tipo','Descripcion'],
[['transcript_id','String','ID retornado por /transcribe-async'],
],[3.5,2,10])
spacer()
heading(3,'Ejemplo')
code_block(['curl http://localhost:5000/status/abc123xyz'])
heading(3,'Respuestas posibles')
code_block([
    '# En proceso:',
    '{ "status": "processing", "message": "Transcripcion en proceso... (estado: queued)" }',
    '',
    '# Completada:',
    '{',
    '  "status":         "completed",',
    '  "text":           "Texto completo de la transcripcion...",',
    '  "language_code":  "es",',
    '  "confidence":     0.97,',
    '  "audio_duration": 3600,',
    '  "utterances":     [...]',
    '}',
    '',
    '# Error:',
    '{ "status": "error", "error": "Descripcion del error de AssemblyAI" }',
])
make_table(['Estado','Descripcion','Cuando ocurre'],
[['processing','El audio esta en cola o siendo procesado','Segundos o minutos despues de iniciar'],
 ['completed','Transcripcion finalizada exitosamente','Depende de duracion del audio'],
 ['error','Fallo en AssemblyAI','Audio corrupto, formato invalido, etc.'],
],[3,6,6.5])
spacer(); divider(); doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════
# 6. MODOS DE CALIDAD
# ═══════════════════════════════════════════════════════════════════════
heading(1,'6. Modos de Calidad')
para('La API soporta tres modos de calidad que afectan la precision de la transcripcion y el tiempo de procesamiento.')
spacer()
make_table(['Modo','Precision Estimada','Descripcion','Caso de uso'],
[['standard','85 - 90%','Configuracion basica sin optimizaciones adicionales','Audio de alta calidad, un hablante, sin ruido'],
 ['high','90 - 95%','Configuracion optimizada con boost de audio y puntuacion','Audio con algo de ruido o multiples hablantes'],
 ['maximum','95 - 99%','Configuracion completa con todos los parametros activados','Grabaciones de baja calidad o terminologia tecnica'],
],[2.5,3,5.5,4.5])
spacer()
para('El modo maximum activa adicionalmente los parametros dual_channel: False y speakers_expected: None para compatibilidad maxima con cualquier tipo de audio.')
spacer()
heading(2,'6.1 Vocabulario Personalizado (word_boost)')
para('El parametro vocabulary permite proporcionar una lista de palabras o terminos tecnicos que AssemblyAI reforzara durante el reconocimiento. Esto puede mejorar la precision entre 5 y 15 puntos porcentuales adicionales cuando el audio contiene terminologia especializada.')
spacer()
heading(3,'Ejemplo de uso')
code_block([
    '# Via form-data:',
    'vocabulary=AssemblyAI,transcripcion,STA,Machine Learning,Flask',
    '',
    '# Via JSON:',
    '"vocabulary": ["AssemblyAI", "transcripcion", "STA", "Machine Learning"]',
])
spacer(); divider(); doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════
# 7. PRUEBAS CON POSTMAN
# ═══════════════════════════════════════════════════════════════════════
heading(1,'7. Pruebas con Postman')
spacer()
heading(2,'7.1 Health Check')
make_table(['Campo','Valor'],
[['Metodo','GET'],['URL','http://localhost:5000/health'],
],[4,11.5])
spacer()

heading(2,'7.2 Transcripcion Sincrona (archivo)')
make_table(['Campo','Valor'],
[['Metodo','POST'],['URL','http://localhost:5000/transcribe'],
 ['Body tipo','form-data'],
 ['Key: audio (File)','Seleccionar archivo de audio desde el disco'],
 ['Key: quality (Text)','maximum'],
 ['Key: vocabulary (Text)','palabra1,palabra2 (opcional)'],
],[4,11.5])
spacer()

heading(2,'7.3 Transcripcion desde URL')
make_table(['Campo','Valor'],
[['Metodo','POST'],['URL','http://localhost:5000/transcribe-url'],
 ['Header','Content-Type: application/json'],
 ['Body (raw JSON)','{ "audio_url": "https://ejemplo.com/audio.mp3", "quality": "maximum" }'],
],[4,11.5])
spacer()

heading(2,'7.4 Transcripcion Asincrona (flujo completo)')
para('Paso 1 - Iniciar transcripcion:')
make_table(['Campo','Valor'],
[['Metodo','POST'],['URL','http://localhost:5000/transcribe-async'],
 ['Body tipo','form-data'],
 ['Key: audio (File)','Seleccionar archivo de audio'],
 ['Key: quality (Text)','maximum'],
],[4,11.5])
spacer()
para('Paso 2 - Consultar estado (repetir hasta obtener "completed"):')
make_table(['Campo','Valor'],
[['Metodo','GET'],['URL','http://localhost:5000/status/<transcript_id_del_paso_1>'],
],[4,11.5])
para('Nota: El transcript_id se obtiene del campo "transcript_id" de la respuesta del Paso 1. Consultar cada 3-5 segundos hasta que el status sea "completed".', italic=True, color=C_GRAY)
spacer(); divider(); doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════
# 8. MANEJO DE ERRORES
# ═══════════════════════════════════════════════════════════════════════
heading(1,'8. Manejo de Errores')
spacer()
heading(2,'8.1 Errores del Cliente (4xx)')
make_table(['Codigo','Mensaje','Causa','Solucion'],
[['400','No se encontro ningun archivo','No se envio el campo audio en form-data','Usar key "audio" y tipo File'],
 ['400','El archivo no tiene nombre','Se envio el campo vacio','Seleccionar un archivo valido'],
 ['400','Formato no soportado','Extension de archivo no valida','Usar MP3, WAV, M4A, FLAC, OGG, WEBM, AAC, AMR, OPUS, WMA'],
 ['400','Debes proporcionar audio_url','JSON sin campo audio_url','Incluir campo audio_url en el body'],
 ['404','Endpoint no encontrado','Ruta incorrecta','Verificar la URL del endpoint'],
],[2,3.5,4,6])
spacer()
heading(2,'8.2 Errores del Servidor (5xx)')
make_table(['Codigo','Causa','Solucion'],
[['500','API Key de AssemblyAI invalida','Verificar ASSEMBLYAI_API_KEY en .env'],
 ['500','Error al subir el audio a AssemblyAI','Verificar conexion a internet y tamano del archivo'],
 ['500','Error al iniciar transcripcion','Verificar que el formato de audio sea valido'],
 ['500','Timeout en polling','El audio es muy largo; usar modo asincrono'],
],[2,5,8.5])
spacer()
heading(2,'8.3 Limite de Tamano de Archivo')
para('La API esta configurada para aceptar archivos de hasta 500 MB. Si el archivo supera este limite, Flask retornara un error 413 (Request Entity Too Large) automaticamente.')
spacer(); divider(); doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════
# 9. SEGURIDAD Y PRODUCCION
# ═══════════════════════════════════════════════════════════════════════
heading(1,'9. Seguridad y Despliegue en Produccion')
spacer()
heading(2,'9.1 API Key')
bullet('Nunca exponer la API key de AssemblyAI en el codigo fuente o repositorios publicos.')
bullet('Usar siempre variables de entorno (.env) y agregar .env a .gitignore.')
bullet('Rotar la API key periodicamente desde el panel de AssemblyAI.')
spacer()
heading(2,'9.2 CORS')
para('La API usa flask-cors con configuracion abierta (CORS(app)) que permite peticiones desde cualquier origen. Para produccion, restringir a los dominios autorizados:')
code_block([
    'from flask_cors import CORS',
    '',
    '# Desarrollo (abierto)',
    'CORS(app)',
    '',
    '# Produccion (restrictivo)',
    'CORS(app, resources={r"/api/*": {"origins": "https://tu-dominio.com"}})',
])
spacer()
heading(2,'9.3 Gunicorn (Produccion)')
para('Para entornos de produccion, Flask no debe usarse en modo debug. Usar Gunicorn como servidor WSGI:')
code_block([
    '# 4 workers, puerto 5000',
    'gunicorn -w 4 -b 0.0.0.0:5000 transcription_api_v2:app',
    '',
    '# Con timeout extendido para audios largos',
    'gunicorn -w 4 -b 0.0.0.0:5000 --timeout 600 transcription_api_v2:app',
])
spacer()
heading(2,'9.4 Variables de Entorno en Produccion')
code_block([
    '# Linux / macOS',
    'export ASSEMBLYAI_API_KEY="tu_api_key"',
    'export PORT=5000',
    '',
    '# Windows PowerShell',
    '$env:ASSEMBLYAI_API_KEY = "tu_api_key"',
    '$env:PORT = "5000"',
])
spacer(); divider(); doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════
# 10. DEPENDENCIAS
# ═══════════════════════════════════════════════════════════════════════
heading(1,'10. Dependencias del Proyecto')
spacer()
make_table(['Paquete','Version','Descripcion'],
[['Flask','3.0.0','Microframework web para Python. Gestiona rutas, requests y responses.'],
 ['flask-cors','4.0.0','Extension Flask para habilitar CORS. Permite llamadas desde el frontend React.'],
 ['requests','2.31.0','Libreria HTTP para Python. Usada para comunicarse con la API de AssemblyAI.'],
 ['python-dotenv','1.0.0','Carga variables de entorno desde archivos .env en el directorio raiz.'],
 ['gunicorn','21.2.0','Servidor WSGI de produccion para aplicaciones Python/WSGI como Flask.'],
],[3.5,2,10])
spacer()
heading(2,'10.1 Runtime')
make_table(['Archivo','Contenido','Proposito'],
[['runtime.txt','python-3.11.0','Indica a plataformas como Render o Heroku la version de Python a usar'],
],[4,3.5,8]  )
spacer(); divider(); doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════
# 11. GLOSARIO
# ═══════════════════════════════════════════════════════════════════════
heading(1,'11. Glosario')
make_table(['Termino','Definicion'],
[['AssemblyAI','Plataforma de IA especializada en reconocimiento automatico de voz (ASR) y procesamiento de audio.'],
 ['ASR','Automatic Speech Recognition. Tecnologia para convertir voz en texto.'],
 ['Polling','Tecnica donde el cliente consulta periodicamente el estado de una operacion hasta que finaliza.'],
 ['transcript_id','Identificador unico asignado por AssemblyAI a cada trabajo de transcripcion.'],
 ['word_boost','Parametro de AssemblyAI para reforzar el reconocimiento de palabras especificas.'],
 ['utterance','Segmento de audio atribuido a un hablante especifico en transcripciones con speaker_labels.'],
 ['WSGI','Web Server Gateway Interface. Protocolo para comunicacion entre servidores web y apps Python.'],
 ['CORS','Cross-Origin Resource Sharing. Permite al frontend consumir la API desde otro dominio.'],
 ['Gunicorn','Green Unicorn. Servidor HTTP WSGI para Unix, usado para desplegar Flask en produccion.'],
 ['confidence','Valor entre 0 y 1 que indica la certeza del modelo sobre la precision de la transcripcion.'],
],[3.5,12])
spacer(); divider(); spacer(10)

p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('-- Fin del Documento --')
r.italic=True; r.font.name='Arial'; r.font.size=Pt(10); r.font.color.rgb=C_GRAY
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('STA 2026 - Ing. Brayam Lopez - Ing. Arturo Lopez - Ing. Juan Hernandez')
r.font.name='Arial'; r.font.size=Pt(9); r.font.color.rgb=C_GRAY

doc.save('C:/Users/braya/Downloads/STA_Transcripcion_API_Documentacion.docx')
print('OK')