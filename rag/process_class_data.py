# process_class_data.py
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from langchain.text_splitter import RecursiveCharacterTextSplitter, SentenceTransformersTokenTextSplitter
from dotenv import load_dotenv, find_dotenv
import os
from loaders import CustomPDFLoader

# Cargar las variables de entorno
load_dotenv(find_dotenv())

def generate_collection_name_for_class(id_clase):
    """Genera un nombre de colección basado en el ID de clase"""
    return f"clase_{id_clase}"

def extract_pdf_texts_from_folder(folder_path):
    """Extrae texto de todos los PDFs en una carpeta"""
    texts = []
    if not os.path.exists(folder_path):
        print(f"Advertencia: La carpeta {folder_path} no existe.")
        return texts
    
    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(folder_path, pdf_file)
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
            
            print(f"Total de páginas extraídas de {pdf_path}: {len(documents)}")
        except Exception as e:
            print(f"Error procesando {pdf_path}: {str(e)}")
    
    return texts

def token_split_texts(texts):
    """Divide los textos en chunks manejables"""
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

def process_class_files(id_clase, folder_path, chroma_dir="../chroma_storage"):
    """
    Procesa todos los archivos PDF de una clase y crea/actualiza su colección en ChromaDB
    """
    try:
        # Inicializar ChromaDB
        chroma_client = chromadb.PersistentClient(path=chroma_dir)
        embedding_function = SentenceTransformerEmbeddingFunction()
        
        collection_name = generate_collection_name_for_class(id_clase)
        
        print(f"\n=== Procesando Clase {id_clase} ===")
        print(f"Carpeta: {folder_path}")
        print(f"Nombre de colección: {collection_name}")
        
        # Extraer textos de todos los PDFs de la carpeta
        pdf_texts = extract_pdf_texts_from_folder(folder_path)
        
        if not pdf_texts:
            print(f"No se extrajo texto de los archivos en {folder_path}")
            return None
        
        # Dividir textos en chunks
        token_split_texts_result = token_split_texts(pdf_texts)
        ids = [str(i) for i in range(len(token_split_texts_result))]
        
        # Verificar si la colección ya existe
        collection_names = [col.name for col in chroma_client.list_collections()]
        
        if collection_name in collection_names:
            print(f"Eliminando colección existente: {collection_name}")
            chroma_client.delete_collection(name=collection_name)
        
        # Crear nueva colección
        chroma_collection = chroma_client.create_collection(
            name=collection_name, 
            embedding_function=embedding_function
        )
        
        # Agregar documentos a la colección
        chroma_collection.add(ids=ids, documents=token_split_texts_result)
        
        print(f"Colección {collection_name} creada con {len(token_split_texts_result)} chunks.")
        return chroma_collection
        
    except Exception as e:
        print(f"Error procesando clase {id_clase}: {str(e)}")
        return None

# Función para uso directo desde la API
def get_or_create_class_collection(id_clase, folder_path, chroma_dir="../chroma_storage"):
    """
    Obtiene una colección existente o la crea si no existe
    """
    try:
        chroma_client = chromadb.PersistentClient(path=chroma_dir)
        embedding_function = SentenceTransformerEmbeddingFunction()
        collection_name = generate_collection_name_for_class(id_clase)
        
        # Verificar si la colección existe
        collection_names = [col.name for col in chroma_client.list_collections()]
        
        if collection_name in collection_names:
            # Retornar colección existente
            return chroma_client.get_collection(name=collection_name, embedding_function=embedding_function)
        else:
            # Crear nueva colección
            return process_class_files(id_clase, folder_path, chroma_dir)
            
    except Exception as e:
        print(f"Error obteniendo/creando colección para clase {id_clase}: {str(e)}")
        return None

if __name__ == "__main__":
    # Ejemplo de uso
    import sys
    
    if len(sys.argv) >= 3:
        id_clase = int(sys.argv[1])
        folder_path = sys.argv[2]
        collection = process_class_files(id_clase, folder_path)
        if collection:
            print(f"Colección creada exitosamente: {collection.name}")
        else:
            print("Error creando la colección")
    else:
        print("Uso: python process_class_data.py <id_clase> <folder_path>")
