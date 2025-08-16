# API DocentePlus - Documentación de Endpoints

## Configuración Inicial

1. Crea un archivo `.env` basado en `.env.example`:
```
GOOGLE_API_KEY=tu_api_key_de_google_gemini
SUPABASE_URL=tu_url_de_supabase
SUPABASE_KEY=tu_clave_de_supabase
DEEPGRAM_API_KEY=tu_api_key_de_deepgram
```

2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

3. Ejecuta la API:
```bash
python run_api.py
```

## Endpoints Principales

### 1. Crear un Docente

**POST** `/docentes`

```json
{
  "nombre": "Juan Pérez",
  "correo": "juan.perez@email.com",
  "password": "mipassword123"
}
```

### 2. Login de Docente

**POST** `/docentes/login`

```json
{
  "correo": "juan.perez@email.com",
  "password": "mipassword123"
}
```

### 3. Crear un Formulario

**POST** `/formularios`

```json
{
  "enlace": "https://forms.google.com/mi-formulario",
  "cantidad_visual": 10,
  "cantidad_auditivo": 5,
  "cantidad_lector": 8,
  "cantidad_kinestesico": 3
}
```

*Nota: Las fechas de creación y cierre se generan automáticamente (actual y +1 día respectivamente)*

### 4. Crear una Clase

**POST** `/clases`

```json
{
  "id_formulario": 1,
  "id_docente": 1,
  "nombre": "Matemáticas Básicas",
  "perfil": "Auditivo",
  "area": "Matemáticas",
  "tema": "Suma y resta",
  "nivel_educativo": "Primaria",
  "duracion_estimada": 60,
  "solo_informacion_proporcionada": false,
  "conocimientos_previos_estudiantes": "Los estudiantes conocen los números del 1 al 10",
  "tipo_sesion": "Clase teorica",
  "modalidad": "Presencial",
  "objetivos_aprendizaje": "Que los estudiantes aprendan a sumar y restar números de una cifra",
  "resultado_taxonomia": "Aplicar",
  "recursos": "Pizarra, marcadores, fichas",
  "aspectos_motivacionales": "Usar juegos y dinámicas",
  "estilo_material": "Cercano y motivador",
  "tipo_recursos_generar": "Audio"
}
```

### 5. Subir Archivos para una Clase

**POST** `/clases/{id_clase}/upload-files`

Multipart form con archivos PDF.

### 6. Procesar Clase (Generar Contenido con Audio)

**POST** `/clases/{id_clase}/process`

Este endpoint:
1. Procesa todos los archivos PDF subidos para la clase
2. Crea/actualiza la colección ChromaDB específica para la clase
3. Genera contenido educativo usando RAG y LLM
4. **Para tipo de recurso "Audio": genera archivo MP3 automáticamente usando Deepgram**
5. Guarda el contenido generado en la base de datos

## Funcionalidad de Audio

### Generación Automática de Audio

Cuando se especifica "Audio" como tipo de recurso:

1. **Genera script**: El LLM crea un script educativo (máximo 100 palabras)
2. **Convierte a audio**: Usa Deepgram TTS para generar archivo MP3
3. **Guarda archivo**: Se almacena en `public/files/{id_clase}/{id_clase}_{timestamp}_audio.mp3`
4. **Actualiza BD**: Registra el archivo en la tabla `archivos`
5. **Retorna contenido**: Incluye script + URL del archivo de audio

### Acceso a Archivos de Audio

Los archivos de audio generados son accesibles públicamente en:
```
http://localhost:8000/files/{id_clase}/{nombre_archivo}.mp3
```

## Perfiles de Aprendizaje y Recursos por Defecto

Si no se especifica `tipo_recursos_generar`, se asignan automáticamente según el perfil:

- **Visual**: Presentación (ppt)
- **Auditivo**: Audio (con generación automática de MP3)
- **Lector**: Guía de estudio (escrita)
- **Kinestésico**: Dinámica participativa

## Endpoints Completos

### Docentes
- `POST /docentes` - Crear docente
- `POST /docentes/login` - Login
- `GET /docentes` - Listar docentes
- `GET /docentes/{id}` - Obtener docente

### Formularios  
- `POST /formularios` - Crear formulario (fechas automáticas)
- `GET /formularios` - Listar formularios
- `GET /formularios/{id}` - Obtener formulario

### Clases
- `POST /clases` - Crear clase
- `GET /clases` - Listar clases
- `GET /clases/{id}` - Obtener clase
- `POST /clases/{id}/upload-files` - Subir archivos
- `POST /clases/{id}/process` - Procesar con RAG + generar audio

### Contenidos
- `GET /clases/{id}/contenidos` - Contenidos de clase
- `GET /contenidos/{id}` - Contenido específico

## Flujo de Trabajo Típico

1. **Crear docente** → `POST /docentes`
2. **Login** → `POST /docentes/login`
3. **Crear formulario** → `POST /formularios`
4. **Crear clase** → `POST /clases`
5. **Subir PDFs** → `POST /clases/{id}/upload-files`
6. **Procesar clase** → `POST /clases/{id}/process` (genera audio automáticamente)
7. **Acceder a contenido y audio** → `GET /clases/{id}/contenidos`

## Variables de Entorno Requeridas

```bash
GOOGLE_API_KEY=clave_de_google_gemini
SUPABASE_URL=url_de_supabase  
SUPABASE_KEY=clave_de_supabase
DEEPGRAM_API_KEY=clave_de_deepgram_para_tts
```
