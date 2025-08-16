from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import sys
import os
import json
import re
import shutil
import time
import asyncio
from datetime import datetime

import sys
import os
import json
import re
import shutil
import time
import requests
import hashlib
from datetime import datetime, timedelta

# Agregar el directorio rag al path para importar funciones de RAG
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'rag'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'bd'))

from bd.bd_supabase import supabase
from bd.dto import (
    ClaseCreateDTO, ClaseResponseDTO, ContenidoCreateDTO, ContenidoResponseDTO,
    DocenteCreateDTO, DocenteResponseDTO, DocenteLoginDTO,
    FormularioCreateDTO, FormularioResponseDTO,
    ArchivoCreateDTO, ArchivoResponseDTO, TipoArchivoEnum
)

try:
    from execute_rag import execute_rag_for_query
    from loaders import CustomPDFLoader
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    from langchain.text_splitter import RecursiveCharacterTextSplitter, SentenceTransformersTokenTextSplitter
    from langchain_google_genai import GoogleGenerativeAI
    from langchain_core.messages import SystemMessage, HumanMessage
    from dotenv import load_dotenv, find_dotenv
    print("[DEBUG] Módulos RAG importados exitosamente")
    load_dotenv(find_dotenv())
    RAG_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Algunos módulos RAG no están disponibles: {e}")
    print("[INFO] Las funciones RAG estarán limitadas")
    RAG_AVAILABLE = False
    execute_rag_for_query = None
    CustomPDFLoader = None
    chromadb = None
    SentenceTransformerEmbeddingFunction = None
    RecursiveCharacterTextSplitter = None
    SentenceTransformersTokenTextSplitter = None
    GoogleGenerativeAI = None
    SystemMessage = None
    HumanMessage = None
    

app = FastAPI(title="DocentePlus API", description="API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Frontend Next.js en desarrollo
        "http://127.0.0.1:3000",
        "http://localhost:3001",  # Por si usas otro puerto
        "https://your-production-domain.com",  # Cambiar por tu dominio de producción
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Permitir todos los headers
)

# Configuración de Deepgram para TTS
DEEPGRAM_API_KEY = os.environ.get('DEEPGRAM_API_KEY', "a780d7cc3a0d84d07be3e21bb0bd5f70d10f16e8")
DEEPGRAM_TTS_URL = "https://api.deepgram.com/v1/speak?model=aura-2-celeste-es"

CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_storage")
chroma_client = None
embedding_function = None
llm = None

if RAG_AVAILABLE:
    try:
        chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
        embedding_function = SentenceTransformerEmbeddingFunction()
        google_api_key = os.environ.get('GOOGLE_API_KEY')
        if google_api_key:
            llm = GoogleGenerativeAI(model="gemini-2.5-flash-lite", google_api_key=google_api_key)
        else:
            print("[WARNING] GOOGLE_API_KEY no encontrada")
    except Exception as e:
        print(f"[ERROR] Error configurando ChromaDB/LLM: {e}")
        chroma_client = None
        llm = None
        RAG_AVAILABLE = False

# Funciones auxiliares
def generate_collection_name_for_class(id_clase):
    """Genera un nombre de colección basado en el ID de clase"""
    return f"clase_{id_clase}"

def get_timestamp():
    """Obtiene timestamp actual"""
    return int(time.time())

def get_class_folder_path(id_clase):
    """Obtiene la ruta de la carpeta de una clase"""
    return os.path.join(files_directory, str(id_clase))

def ensure_class_folder_exists(id_clase):
    """Asegura que la carpeta de la clase existe"""
    folder_path = get_class_folder_path(id_clase)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path

def hash_password(password: str) -> str:
    """Hash de contraseña usando SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """Verificar contraseña hasheada"""
    return hash_password(password) == hashed

async def generate_audio_file(text: str, id_clase: int) -> Optional[str]:
    """
    Genera un archivo de audio usando Deepgram TTS
    Retorna el nombre del archivo generado o None si hay error
    """
    try:
        # Asegurar que la carpeta de la clase existe
        folder_path = ensure_class_folder_exists(id_clase)
        
        # Generar nombre único para el archivo
        timestamp = get_timestamp()
        audio_filename = f"{id_clase}_{timestamp}_audio.mp3"
        audio_path = os.path.join(folder_path, audio_filename)
        
        # Preparar datos para Deepgram
        data = {"text": text}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {DEEPGRAM_API_KEY}"
        }
        
        # Hacer solicitud a Deepgram
        response = requests.post(DEEPGRAM_TTS_URL, json=data, headers=headers)
        
        if response.status_code == 200:
            # Guardar archivo de audio
            with open(audio_path, "wb") as f:
                f.write(response.content)
            
            # Guardar información en base de datos
            archivo_data = {
                "id_clase": id_clase,
                "filename": audio_filename,
                "tipo": "Generado"
            }
            
            supabase.table("archivos").insert(archivo_data).execute()
            
            print(f"Archivo de audio generado: {audio_filename}")
            return audio_filename
        else:
            print(f"Error generando audio: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error generando archivo de audio: {str(e)}")
        return None

# Configurar directorio de archivos estáticos para imágenes
files_directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public/files")
if os.path.exists(files_directory):
    app.mount("/files", StaticFiles(directory=files_directory), name="files")
else:
    print(f"[WARNING] Directorio de archivos no encontrado: {files_directory}")

@app.get("/")
async def root():
    """
    Endpoint de salud de la API
    """
    return {"message": "MINEDU RAG API funcionando correctamente"}

@app.get("/health")
async def health_check():
    """
    Endpoint de diagnóstico para verificar la conexión a la base de datos
    """
    try:
        # Intentar una consulta simple para verificar la conexión
        response = supabase.table("contenido").select("count", count="exact").execute()
        
        return {
            "status": "OK",
            "database": "Connected",
            "tables_accessible": True,
            "message": "Conexión a Supabase exitosa"
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "database": "Failed",
            "tables_accessible": False,
            "error": str(e),
            "message": "Error de conexión a Supabase"
        }

# CRUD para Docentes
@app.post("/docentes", response_model=DocenteResponseDTO)
async def crear_docente(docente: DocenteCreateDTO):
    """
    Crear un nuevo docente
    """
    try:
        # Verificar si ya existe un docente con ese correo
        existing = supabase.table("docente").select("*").eq("correo", docente.correo).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Ya existe un docente con este correo")
        
        # Hash de la contraseña
        docente_data = docente.model_dump()
        docente_data["password"] = hash_password(docente_data["password"])
        
        response = supabase.table("docente").insert(docente_data).execute()
        
        if response.data:
            # No devolver la contraseña en la respuesta
            docente_response = response.data[0]
            del docente_response["password"]
            return DocenteResponseDTO(**docente_response)
        else:
            raise HTTPException(status_code=400, detail="Error al crear el docente")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.post("/docentes/login")
async def login_docente(login_data: DocenteLoginDTO):
    """
    Login de docente
    """
    try:
        response = supabase.table("docente").select("*").eq("correo", login_data.correo).execute()
        
        if not response.data:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        
        docente = response.data[0]
        
        if not verify_password(login_data.password, docente["password"]):
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        
        # No devolver la contraseña en la respuesta
        del docente["password"]
        return {
            "message": "Login exitoso",
            "docente": DocenteResponseDTO(**docente)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/docentes/{id_docente}", response_model=DocenteResponseDTO)
async def obtener_docente(id_docente: int):
    """
    Obtener un docente por ID
    """
    try:
        response = supabase.table("docente").select("id, nombre, correo").eq("id", id_docente).execute()
        
        if response.data:
            return DocenteResponseDTO(**response.data[0])
        else:
            raise HTTPException(status_code=404, detail="Docente no encontrado")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/docentes", response_model=List[DocenteResponseDTO])
async def listar_docentes():
    """
    Listar todos los docentes (sin contraseñas)
    """
    try:
        response = supabase.table("docente").select("id, nombre, correo").execute()
        return [DocenteResponseDTO(**docente) for docente in response.data]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# CRUD para Formularios
@app.post("/formularios")
async def crear_formulario():
    """
    Crear un nuevo formulario y retorna el ID generado
    """
    try:
        # Datos básicos para el formulario
        formulario_data = {}
        
        response = supabase.table("formulario").insert(formulario_data).execute()
        
        if response.data:
            return {"id": response.data[0]["id"]}
        else:
            raise HTTPException(status_code=400, detail="Error al crear el formulario")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/formularios/{id_formulario}", response_model=FormularioResponseDTO)
async def obtener_formulario(id_formulario: int):
    """
    Obtener un formulario por ID con registro de auditoría
    """
    try:
        # 1. Crear registro en tabla auditoria con datos específicos
        auditoria_data = {
            "id_entidad": id_formulario,
            "nombre_entidad": "formulario"
        }
        supabase.table("auditoria").insert(auditoria_data).execute()
        
        # 2. Esperar 3 segundos
        await asyncio.sleep(3)
        
        # 3. Obtener datos del formulario
        response = supabase.table("formulario").select("*").eq("id", id_formulario).execute()
        
        if response.data:
            return FormularioResponseDTO(**response.data[0])
        else:
            raise HTTPException(status_code=404, detail="Formulario no encontrado")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/formularios", response_model=List[FormularioResponseDTO])
async def listar_formularios():
    """
    Listar todos los formularios
    """
    try:
        response = supabase.table("formulario").select("*").execute()
        return [FormularioResponseDTO(**formulario) for formulario in response.data]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# CRUD para Clases
@app.post("/clases", response_model=ClaseResponseDTO)
async def crear_clase(clase: ClaseCreateDTO):
    """
    Crear una nueva clase
    """
    try:
        # Verificar que el docente existe
        docente_response = supabase.table("docente").select("id").eq("id", clase.id_docente).execute()
        if not docente_response.data:
            raise HTTPException(status_code=404, detail="Docente no encontrado")
        
        # Verificar que el formulario existe
        formulario_response = supabase.table("formulario").select("id").eq("id", clase.id_formulario).execute()
        if not formulario_response.data:
            raise HTTPException(status_code=404, detail="Formulario no encontrado")
        
        # Convertir el DTO a diccionario
        clase_data = clase.model_dump()
        # Agregar estado por defecto
        clase_data["estado"] = True
        
        response = supabase.table("clase").insert(clase_data).execute()
        
        if response.data:
            return ClaseResponseDTO(**response.data[0])
        else:
            raise HTTPException(status_code=400, detail="Error al crear la clase")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/clases/{id_clase}", response_model=ClaseResponseDTO)
async def obtener_clase(id_clase: int):
    """
    Obtener una clase por ID
    """
    try:
        response = supabase.table("clase").select("*").eq("id", id_clase).execute()
        
        if response.data:
            return ClaseResponseDTO(**response.data[0])
        else:
            raise HTTPException(status_code=404, detail="Clase no encontrada")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/clases", response_model=List[ClaseResponseDTO])
async def listar_clases(id_docente: Optional[int] = None):
    """
    Listar todas las clases o filtrar por docente
    """
    try:
        query = supabase.table("clase").select("*")
        
        if id_docente:
            query = query.eq("id_docente", id_docente)
            
        response = query.execute()
        
        return [ClaseResponseDTO(**clase) for clase in response.data]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# Endpoint para subir archivos
@app.post("/clases/{id_clase}/upload-files")
async def subir_archivos(id_clase: int, files: List[UploadFile] = File(...)):
    """
    Subir archivos para una clase específica
    """
    try:
        # Verificar que la clase existe
        clase_response = supabase.table("clase").select("*").eq("id", id_clase).execute()
        if not clase_response.data:
            raise HTTPException(status_code=404, detail="Clase no encontrada")
        
        # Crear carpeta si no existe
        folder_path = ensure_class_folder_exists(id_clase)
        
        uploaded_files = []
        
        for file in files:
            # Generar nombre de archivo único
            timestamp = get_timestamp()
            file_extension = os.path.splitext(file.filename)[1]
            new_filename = f"{id_clase}_{timestamp}{file_extension}"
            file_path = os.path.join(folder_path, new_filename)
            
            # Guardar archivo
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Guardar en base de datos
            archivo_data = {
                "id_clase": id_clase,
                "filename": new_filename,
                "tipo": "Subido"
            }
            
            archivo_response = supabase.table("archivos").insert(archivo_data).execute()
            
            uploaded_files.append({
                "original_filename": file.filename,
                "saved_filename": new_filename,
                "file_path": file_path,
                "size": os.path.getsize(file_path)
            })
        
        return {
            "message": f"Se subieron {len(uploaded_files)} archivos correctamente",
            "files": uploaded_files
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/clases/{id_clase}/archivos")
async def listar_archivos_clase(id_clase: int, tipo: Optional[str] = Query(None, description="Filtrar por tipo: Subido o Generado")):
    """
    Listar todos los archivos de una clase, opcionalmente filtrados por tipo
    """
    try:
        # Verificar que la clase existe
        clase_response = supabase.table("clase").select("*").eq("id", id_clase).execute()
        if not clase_response.data:
            raise HTTPException(status_code=404, detail="Clase no encontrada")
        
        # Obtener archivos de la clase
        query = supabase.table("archivos").select("*").eq("id_clase", id_clase)
        
        # Filtrar por tipo si se especifica
        if tipo and tipo in ["Subido", "Generado"]:
            query = query.eq("tipo", tipo)
        
        archivos_response = query.execute()
        
        archivos_info = []
        folder_path = get_class_folder_path(id_clase)
        
        for archivo in archivos_response.data:
            file_path = os.path.join(folder_path, archivo['filename'])
            if os.path.exists(file_path):
                archivos_info.append({
                    "id": archivo['id'],
                    "filename": archivo['filename'],
                    "tipo": archivo.get('tipo', 'Subido'),  # Valor por defecto para archivos antiguos
                    "size": os.path.getsize(file_path),
                    "download_url": f"/clases/{id_clase}/archivos/{archivo['filename']}/download"
                })
        
        return {
            "id_clase": id_clase,
            "filtro_tipo": tipo,
            "archivos": archivos_info,
            "total_archivos": len(archivos_info)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/clases/{id_clase}/archivos/{filename}/download")
async def descargar_archivo(id_clase: int, filename: str):
    """
    Descargar un archivo específico de una clase
    """
    try:
        # Verificar que la clase existe
        clase_response = supabase.table("clase").select("*").eq("id", id_clase).execute()
        if not clase_response.data:
            raise HTTPException(status_code=404, detail="Clase no encontrada")
        
        # Verificar que el archivo existe en la base de datos
        archivo_response = supabase.table("archivos").select("*").eq("id_clase", id_clase).eq("filename", filename).execute()
        if not archivo_response.data:
            raise HTTPException(status_code=404, detail="Archivo no encontrado en la base de datos")
        
        # Construir ruta del archivo
        folder_path = get_class_folder_path(id_clase)
        file_path = os.path.join(folder_path, filename)
        
        # Verificar que el archivo existe físicamente
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Archivo no encontrado en el sistema")
        
        # Determinar el tipo de contenido basado en la extensión
        file_extension = os.path.splitext(filename)[1].lower()
        media_type_map = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.txt': 'text/plain',
            '.mp3': 'audio/mpeg',
            '.mp4': 'video/mp4',
            '.zip': 'application/zip'
        }
        
        media_type = media_type_map.get(file_extension, 'application/octet-stream')
        
        # Retornar el archivo para descarga
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.delete("/clases/{id_clase}/archivos/{filename}")
async def eliminar_archivo(id_clase: int, filename: str):
    """
    Eliminar un archivo específico de una clase
    """
    try:
        # Verificar que la clase existe
        clase_response = supabase.table("clase").select("*").eq("id", id_clase).execute()
        if not clase_response.data:
            raise HTTPException(status_code=404, detail="Clase no encontrada")
        
        # Verificar que el archivo existe en la base de datos
        archivo_response = supabase.table("archivos").select("*").eq("id_clase", id_clase).eq("filename", filename).execute()
        if not archivo_response.data:
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        archivo_id = archivo_response.data[0]['id']
        
        # Eliminar archivo físico
        folder_path = get_class_folder_path(id_clase)
        file_path = os.path.join(folder_path, filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Eliminar registro de la base de datos
        supabase.table("archivos").delete().eq("id", archivo_id).execute()
        
        return {
            "message": f"Archivo {filename} eliminado correctamente",
            "filename": filename,
            "id_clase": id_clase
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/clases/{id_clase}/contenidos", response_model=List[ContenidoResponseDTO])
async def obtener_contenidos_clase(id_clase: int):
    """
    Obtener todos los contenidos de una clase
    """
    try:
        response = supabase.table("contenido").select("*").eq("id_clase", id_clase).execute()
        return [ContenidoResponseDTO(**contenido) for contenido in response.data]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/contenidos/{id_contenido}", response_model=ContenidoResponseDTO)
async def obtener_contenido(id_contenido: int):
    """
    Obtener un contenido específico
    """
    try:
        response = supabase.table("contenido").select("*").eq("id", id_contenido).execute()
        
        if response.data:
            return ContenidoResponseDTO(**response.data[0])
        else:
            raise HTTPException(status_code=404, detail="Contenido no encontrado")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# Endpoint principal de procesamiento
@app.post("/clases/{id_clase}/process")
async def procesar_clase(id_clase: int):
    """
    Procesar archivos de una clase y generar contenido usando RAG
    """
    try:
        if not RAG_AVAILABLE:
            raise HTTPException(
                status_code=503, 
                detail="Servicios RAG no disponibles. Verifica las dependencias y configuración."
            )
        
        clase_response = supabase.table("clase").select("*").eq("id", id_clase).execute()
        if not clase_response.data:
            raise HTTPException(status_code=404, detail="Clase no encontrada")
        
        clase_data = clase_response.data[0]
        
        archivos_response = supabase.table("archivos").select("*").eq("id_clase", id_clase).execute()
        if not archivos_response.data:
            raise HTTPException(status_code=400, detail="No hay archivos para procesar en esta clase")
        
        # 1. PROCESAR ARCHIVOS Y CREAR/ACTUALIZAR COLECCIÓN CHROMA
        if not chroma_client or not embedding_function:
            raise HTTPException(status_code=500, detail="ChromaDB no está configurado correctamente")
            
        collection_name = generate_collection_name_for_class(id_clase)
        folder_path = get_class_folder_path(id_clase)
        
        # Extraer textos de todos los PDFs
        all_texts = []
        for archivo in archivos_response.data:
            file_path = os.path.join(folder_path, archivo['filename'])
            if os.path.exists(file_path) and file_path.lower().endswith('.pdf'):
                try:
                    loader = CustomPDFLoader(file_path)
                    documents = loader.load()
                    for doc in documents:
                        if doc.page_content.strip():
                            all_texts.append(doc.page_content.strip())
                except Exception as e:
                    print(f"Error procesando {file_path}: {str(e)}")
        
        if not all_texts:
            raise HTTPException(status_code=400, detail="No se pudo extraer texto de los archivos PDF")
        
        # Dividir textos en chunks
        splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ". ", " ", ""],
            chunk_size=1000,
            chunk_overlap=0
        )
        joined_text = '\n\n'.join(all_texts)
        character_split_texts = splitter.split_text(joined_text)
        
        token_splitter = SentenceTransformersTokenTextSplitter(chunk_overlap=0, tokens_per_chunk=256)
        token_split_texts = []
        for t in character_split_texts:
            token_split_texts += token_splitter.split_text(t)
        
        # Crear o actualizar colección en ChromaDB
        collection_names = [col.name for col in chroma_client.list_collections()]
        
        if collection_name in collection_names:
            # Eliminar colección existente
            chroma_client.delete_collection(name=collection_name)
        
        # Crear nueva colección
        chroma_collection = chroma_client.create_collection(
            name=collection_name, 
            embedding_function=embedding_function
        )
        
        # Agregar documentos a la colección
        ids = [str(i) for i in range(len(token_split_texts))]
        chroma_collection.add(ids=ids, documents=token_split_texts)
        
        # 2. GENERAR CONTENIDO USANDO RAG Y LLM
        if not llm:
            raise HTTPException(status_code=500, detail="LLM no está configurado correctamente. Verifica GOOGLE_API_KEY.")
            
        content_generated = await generate_educational_content(clase_data, chroma_collection)
        
        # 3. GUARDAR CONTENIDO EN BASE DE DATOS
        saved_contents = []
        for content_item in content_generated:
            contenido_data = {
                "id_clase": id_clase,
                "tipo_recurso_generado": content_item["tipo_recurso"],
                "contenido": content_item["contenido"],
                "estado": True
            }
            
            contenido_response = supabase.table("contenido").insert(contenido_data).execute()
            if contenido_response.data:
                saved_contents.append(ContenidoResponseDTO(**contenido_response.data[0]))
        
        return {
            "message": "Clase procesada exitosamente",
            "collection_name": collection_name,
            "documents_processed": len(token_split_texts),
            "contents_generated": len(saved_contents),
            "generated_content": saved_contents
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# Función para generar contenido educativo
async def generate_educational_content(clase_data, chroma_collection):
    """
    Genera contenido educativo basado en los datos de la clase y el contexto de ChromaDB
    """
    try:
        # Construir query para recuperar contexto relevante
        query_parts = []
        if clase_data.get('area'):
            query_parts.append(clase_data['area'])
        if clase_data.get('tema'):
            query_parts.append(clase_data['tema'])
        if clase_data.get('objetivos_aprendizaje'):
            query_parts.append(clase_data['objetivos_aprendizaje'])
        
        query = " ".join(query_parts) if query_parts else "contenido educativo"
        
        # Recuperar documentos relevantes
        results = chroma_collection.query(query_texts=[query], n_results=10)
        retrieved_documents = results['documents'][0]
        context = "\n\n".join(retrieved_documents)
        
        # Determinar tipos de recursos a generar
        tipos_recursos = []
        if clase_data.get('tipo_recursos_generar'):
            # Parsear los tipos de recursos solicitados
            recursos_solicitados = clase_data['tipo_recursos_generar'].split(',')
            for recurso in recursos_solicitados:
                recurso = recurso.strip()
                if recurso:
                    tipos_recursos.append(recurso)
        
        if not tipos_recursos:
            # Tipos por defecto basados en el perfil de aprendizaje
            perfil = clase_data.get('perfil', 'Lector')
            if perfil == 'Visual':
                tipos_recursos = ['Presentación (ppt)']
            elif perfil == 'Auditivo':
                tipos_recursos = ['Audio']
            elif perfil == 'Lector':
                tipos_recursos = ['Guía de estudio (escrita)']
            elif perfil == 'Kinestesico':
                tipos_recursos = ['Dinámica participativa']
            else:
                tipos_recursos = ['Guía de estudio (escrita)']
        
        generated_content = []
        
        for tipo_recurso in tipos_recursos[:3]:  # Limitar a 3 recursos máximo
            # Construir prompt específico para cada tipo de recurso
            content = await generate_specific_content(clase_data, context, tipo_recurso)
            
            if content:
                generated_content.append({
                    "tipo_recurso": tipo_recurso,
                    "contenido": content
                })
        
        return generated_content
        
    except Exception as e:
        print(f"Error generando contenido: {str(e)}")
        return []

async def generate_specific_content(clase_data, context, tipo_recurso):
    """
    Genera contenido específico para un tipo de recurso
    """
    
    try:
        if tipo_recurso == 'Audio':
            # Construir prompt específico para audio (texto más corto)
            system_prompt = f"""
            Eres un experto asistente pedagógico especializado en crear contenido educativo de alta calidad.
            Debes crear un script para un archivo de audio basado en la información de la clase y el contexto proporcionado.
            
            Información de la clase:
            - Área: {clase_data.get('area', 'No especificada')}
            - Tema: {clase_data.get('tema', 'No especificado')}
            - Nivel educativo: {clase_data.get('nivel_educativo', 'No especificado')}
            - Perfil de aprendizaje: {clase_data.get('perfil', 'No especificado')}
            - Tipo de sesión: {clase_data.get('tipo_sesion', 'No especificado')}
            - Modalidad: {clase_data.get('modalidad', 'No especificada')}
            - Objetivos de aprendizaje: {clase_data.get('objetivos_aprendizaje', 'No especificados')}
            - Resultado taxonomía: {clase_data.get('resultado_taxonomia', 'No especificado')}
            - Conocimientos previos: {clase_data.get('conocimientos_previos_estudiantes', 'No especificados')}
            - Aspectos motivacionales: {clase_data.get('aspectos_motivacionales', 'No especificados')}
            - Estilo de material: {clase_data.get('estilo_material', 'No especificado')}
            
            El contenido debe:
            1. El script no debe superar las 100 palabras.
            2. Ser apropiado para el nivel educativo indicado
            3. Seguir el estilo de material especificado
            4. Incorporar los aspectos motivacionales
            5. Alinearse con los objetivos de aprendizaje
            6. Considerar el perfil de aprendizaje de los estudiantes
            7. Ser claro y natural para audio
            
            IMPORTANTE: Responde ÚNICAMENTE con el texto del script, sin explicaciones adicionales.
            """
            
            user_prompt = f"""
            Contexto educativo extraído de los materiales:
            {context}
            
            Crear el script para el audio siguiendo las especificaciones de la clase.
            """
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            # Generar el texto del script
            script_response = llm.invoke(messages)
            script_text = script_response
            
            # Generar el archivo de audio usando el script
            id_clase = clase_data.get('id')
            audio_filename = await generate_audio_file(script_text, id_clase)
            
            if audio_filename:
                # Retornar el script junto con información del archivo de audio
                audio_url = f"/files/{id_clase}/{audio_filename}"
                return f"**Script de Audio:**\n\n{script_text}\n\n**Archivo de audio generado:** [{audio_filename}]({audio_url})\n\n**URL del audio:** `{audio_url}`"
            else:
                # Si no se pudo generar el audio, retornar solo el script
                return f"**Script de Audio:**\n\n{script_text}\n\n*Nota: No se pudo generar el archivo de audio automáticamente.*"
                
        else:
            # Construir prompt específico según el tipo de recurso
            system_prompt = f'''
                Eres un experto asistente pedagógico especializado en crear contenido educativo de alta calidad.
                Debes crear un {tipo_recurso.lower()} basado en la información de la clase y el contexto proporcionado.

                Información de la clase:
                - Área: {clase_data.get('area', 'No especificada')}
                - Tema: {clase_data.get('tema', 'No especificado')}
                - Nivel educativo: {clase_data.get('nivel_educativo', 'No especificado')}
                - Perfil de aprendizaje: {clase_data.get('perfil', 'No especificado')}
                - Duración estimada: {clase_data.get('duracion_estimada', 'No especificada')} minutos
                - Tipo de sesión: {clase_data.get('tipo_sesion', 'No especificado')}
                - Modalidad: {clase_data.get('modalidad', 'No especificada')}
                - Objetivos de aprendizaje: {clase_data.get('objetivos_aprendizaje', 'No especificados')}
                - Resultado taxonomía: {clase_data.get('resultado_taxonomia', 'No especificado')}
                - Conocimientos previos: {clase_data.get('conocimientos_previos_estudiantes', 'No especificados')}
                - Aspectos motivacionales: {clase_data.get('aspectos_motivacionales', 'No especificados')}
                - Estilo de material: {clase_data.get('estilo_material', 'No especificado')}

                El contenido debe:
                1. Estar completamente en formato HTML (solo con el contenido que iría en el body, el header o doctype e incluso los estilos son innecesarios)
                2. Ser apropiado para el nivel educativo indicado
                3. Seguir el estilo de material especificado
                4. Incorporar los aspectos motivacionales
                5. Alinearse con los objetivos de aprendizaje
                6. Considerar el perfil de aprendizaje de los estudiantes
                7. Ser específico para el tipo de recurso: {tipo_recurso}

                IMPORTANTE: Responde ÚNICAMENTE con el contenido en formato HTML, como en el siguiente ejemplo
                <h1>Guía: Derivadas</h1>
                <h2>1. Introducción</h2>
                <p>Las derivadas miden tasas de cambio y pendientes. Newton y Leibniz las desarrollaron en el siglo XVII.</p>
                <h2>2. Objetivos</h2>
                <ul>
                <li>Entender derivada como cambio instantáneo.</li>
                <li>Verla como pendiente de tangente.</li>
                </ul>
                <h2>3. Conceptos</h2>
                <p><strong>Definición:</strong> \( f'(a) = \lim_{{h \to 0}} \frac{{f(a+h)-f(a)}}{{h}} \)</p>
                <h2>4. Notación</h2>
                <p>Leibniz: \( \frac{{dy}}{{dx}} \)</p>
                '''

            
            user_prompt = f"""
            Contexto educativo extraído de los materiales:
            {context}
            
            Crear un {tipo_recurso} siguiendo las especificaciones de la clase.
            """
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = llm.invoke(messages)
            return response
        
    except Exception as e:
        print(f"Error generando contenido específico: {str(e)}")
        return None