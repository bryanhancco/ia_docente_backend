# process_data.py
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from langchain.text_splitter import RecursiveCharacterTextSplitter, SentenceTransformersTokenTextSplitter
from dotenv import load_dotenv, find_dotenv
import os
from loaders import CustomPDFLoader

# Cargar las variables de entorno
load_dotenv(find_dotenv())

PDF_BASE_PATH = f"../public/files/"
CHROMA_DIR = "../chroma_storage"  


def generate_collection_name(docente, id_clase):
    """Genera un nombre de colección basado en el docente y la clase"""
    # Convertir a formato válido para nombres de colección
    docente_clean = docente.lower().replace(' ', '_').replace('í', 'i').replace('á', 'a')
    return f"data_{docente_clean}_{id_clase}"

def extract_pdf_texts(pdf_path):
    """Extrae texto de un solo archivo PDF"""
    texts = []
    if not os.path.exists(pdf_path):
        print(f"Advertencia: El archivo {pdf_path} no existe. Saltando...")
        return texts
    
    print(f"Procesando PDF: {pdf_path}")
    try:
        loader = CustomPDFLoader(pdf_path)
        documents = loader.load()
        
        # Extraer el contenido de texto de cada documento
        for doc in documents:
            if doc.page_content.strip():  # Verificar que el contenido no esté vacío
                texts.append(doc.page_content.strip())
            else:
                print(f"Advertencia: Página vacía encontrada en {pdf_path}")
        
        print(f"Total de páginas extraídas de {pdf_path}: {len(texts)}")
    except Exception as e:
        print(f"Error procesando {pdf_path}: {str(e)}")
    
    return texts

def token_split(texts):
    if not texts:
        raise ValueError("La lista de textos está vacía, no se puede continuar con la fragmentación.")
    
    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ". ", " ", ""],
        chunk_size=1000,
        chunk_overlap=0
    )
    joined_text = '\n\n'.join(texts)
    character_split_texts = splitter.split_text(joined_text)

    if not character_split_texts:
        raise ValueError("La fragmentación por caracteres produjo una lista vacía.")
    
    token_splitter = SentenceTransformersTokenTextSplitter(chunk_overlap=0, tokens_per_chunk=256)
    token_split_texts = []
    for t in character_split_texts:
        token_split_texts += token_splitter.split_text(t)

    if not token_split_texts:
        raise ValueError("La fragmentación por tokens produjo una lista vacía.")
    
    return token_split_texts

# === INICIALIZAR CLIENTE CHROMA PERSISTENTE ===

chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
embedding_function = SentenceTransformerEmbeddingFunction()

# === PROCESAMIENTO PRINCIPAL ===

def process_pdf_collection(pdf_path):
    """Procesa un PDF individual y crea/actualiza su colección correspondiente"""
    try:
        # Extraer área y grado del nombre del archivo
        area, grado = extract_area_and_grade_from_path(pdf_path)
        collection_name = generate_collection_name(area, grado)
        
        print(f"\n=== Procesando {area} - {grado} ===")
        print(f"Nombre de colección: {collection_name}")
        
        # Verificar si la colección ya existe
        collection_names = [col.name for col in chroma_client.list_collections()]
        
        if collection_name in collection_names:
            print(f"Colección existente encontrada: {collection_name}")
            chroma_collection = chroma_client.get_collection(name=collection_name, embedding_function=embedding_function)
            return chroma_collection
        else:
            print(f"Colección no encontrada. Procesando archivo PDF: {pdf_path}")
            pdf_texts = extract_pdf_texts(pdf_path)
            
            if not pdf_texts:
                print(f"No se extrajo texto del archivo {pdf_path}. Saltando...")
                return None
            
            token_split_texts = token_split(pdf_texts)
            ids = [str(i) for i in range(len(token_split_texts))]

            chroma_collection = chroma_client.create_collection(name=collection_name, embedding_function=embedding_function)
            chroma_collection.add(ids=ids, documents=token_split_texts)
            print(f"Colección {collection_name} creada y almacenada persistentemente.")
            return chroma_collection
            
    except Exception as e:
        print(f"Error procesando {pdf_path}: {str(e)}")
        return None

# Procesar todos los PDFs
print("=== INICIANDO PROCESAMIENTO DE TODOS LOS PDFs ===")
collections_created = []

for pdf_path in PDF_PATHS:
    collection = process_pdf_collection(pdf_path)
    if collection:
        collections_created.append(collection.name)

print(f"\n=== RESUMEN ===")
print(f"Colecciones procesadas/creadas: {len(collections_created)}")
for collection_name in collections_created:
    print(f"- {collection_name}")

print("\nProcesamiento completado.")
