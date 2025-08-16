# API DocentePlus - Documentación de Endpoints

## Configuración Inicial

1. Crea un archivo `.env` basado en `.env.example`:
```
GOOGLE_API_KEY=tu_api_key_de_google_gemini
SUPABASE_URL=tu_url_de_supabase
SUPABASE_KEY=tu_clave_de_supabase
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

### 1. Crear una Clase

**POST** `/clases`

```json
{
  "id_formulario": 1,
  "id_docente": 1,
  "nombre": "Matemáticas Básicas",
  "perfil": "Visual",
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
  "tipo_recursos_generar": "Esquema visual / mapa mental, Juego o simulación"
}
```

### 2. Subir Archivos para una Clase

**POST** `/clases/{id_clase}/upload-files`

Multipart form con archivos PDF.

Ejemplo usando curl:
```bash
curl -X POST "http://localhost:8000/clases/1/upload-files" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@documento1.pdf" \
  -F "files=@documento2.pdf"
```

### 3. Procesar Clase (Generar Contenido)

**POST** `/clases/{id_clase}/process`

Este endpoint:
1. Procesa todos los archivos PDF subidos para la clase
2. Crea/actualiza la colección ChromaDB específica para la clase
3. Genera contenido educativo usando RAG y LLM
4. Guarda el contenido generado en la base de datos

Respuesta:
```json
{
  "message": "Clase procesada exitosamente",
  "collection_name": "clase_1",
  "documents_processed": 25,
  "contents_generated": 2,
  "generated_content": [
    {
      "id": 1,
      "id_clase": 1,
      "tipo_recurso_generado": "Esquema visual / mapa mental",
      "contenido": "# Mapa Mental: Suma y Resta\n\n## Conceptos Básicos...",
      "estado": true
    }
  ]
}
```

### 4. Obtener Contenidos de una Clase

**GET** `/clases/{id_clase}/contenidos`

### 5. Obtener una Clase

**GET** `/clases/{id_clase}`

### 6. Listar Clases

**GET** `/clases?id_docente=1`

## Tipos de Recursos Generados

La API puede generar los siguientes tipos de recursos:

- ☐ Video explicativo
- ☐ Esquema visual / mapa mental  
- ☐ Artículo o lectura
- ☐ Dinámica participativa
- ☐ Juego o simulación
- ☐ Evaluación corta o rúbrica
- ☐ Caso práctico / situación real
- ☐ Otro

## Estructura de Archivos

```
backend/
├── api/
│   └── api.py              # API principal con todos los endpoints
├── bd/
│   ├── bd_supabase.py      # Configuración de Supabase
│   └── dto.py              # DTOs para clases y contenido
├── rag/
│   ├── execute_rag.py      # Funciones RAG originales
│   ├── process_class_data.py # Procesamiento específico por clase
│   └── loaders.py          # Cargadores de documentos
├── public/
│   └── files/              # Archivos subidos organizados por clase
│       ├── 1/              # Archivos de la clase 1
│       ├── 2/              # Archivos de la clase 2
│       └── ...
├── chroma_storage/         # Base de datos vectorial ChromaDB
└── .env                    # Variables de entorno
```

## Flujo de Trabajo Típico

1. **Crear una clase** con `POST /clases`
2. **Subir archivos PDF** con `POST /clases/{id}/upload-files`
3. **Procesar la clase** con `POST /clases/{id}/process`
4. **Consultar el contenido generado** con `GET /clases/{id}/contenidos`

## Archivos Estáticos

Los archivos subidos son accesibles públicamente en:
`http://localhost:8000/files/{id_clase}/{nombre_archivo}`

## Notas Importantes

- Los archivos se guardan con el formato: `{id_clase}_{timestamp}.{extension}`
- Se crea una colección ChromaDB específica por clase: `clase_{id}`
- El contenido generado está en formato Markdown
- La API requiere archivos PDF para el procesamiento
- Se requiere configurar las variables de entorno para Google Gemini y Supabase
