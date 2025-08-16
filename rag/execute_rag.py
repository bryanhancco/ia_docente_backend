# execute_rag.py
import chromadb
from langchain_google_genai import GoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv, find_dotenv
import os

# Cargar las variables de entorno
load_dotenv(find_dotenv())

def word_wrap(text, width=87):
    """
    Wraps the given text to the specified width.

    Args:
    text (str): The text to wrap.
    width (int): The width to wrap the text to.

    Returns:
    str: The wrapped text.
    """
    return "\n".join([text[i : i + width] for i in range(0, len(text), width)])


# === CONFIGURACIÓN ===
# Usar path absoluto para chroma_storage
import os
CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_storage")  

chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
embedding_function = chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction()

# Aplying Langchain & Google Generative AI
google_api_key = os.environ['GOOGLE_API_KEY']
llm = GoogleGenerativeAI(model="gemini-2.5-flash-lite", google_api_key=google_api_key)

# === FUNCIONES AUXILIARES ===

def extract_area_and_grade_from_query(query):
    """Extrae el área y grado de la query"""
    # Dividir por ' - ' para obtener las partes
    parts = query.split(' - ')
    if len(parts) >= 2:
        area = parts[0].strip()
        grado = parts[1].strip()
        return area, grado
    else:
        raise ValueError(f"Formato de query no válido. Esperado: 'Área - Grado - Tema - Cantidad'. Recibido: {query}")

def generate_collection_name(area, grado):
    """Genera un nombre de colección basado en área y grado"""
    # Convertir a formato válido para nombres de colección (igual que en process_data.py)
    area_clean = area.lower().replace(' ', '_').replace('í', 'i').replace('á', 'a')
    grado_clean = grado.lower().replace(' ', '_')
    return f"data_{area_clean}_{grado_clean}"

def get_collection_for_query(query):
    """Obtiene la colección de ChromaDB correspondiente a la query"""
    # Extraer área y grado de la query
    area, grado = extract_area_and_grade_from_query(query)
    collection_name = generate_collection_name(area, grado)
    
    print(f"Área extraída: {area}")
    print(f"Grado extraído: {grado}")
    print(f"Nombre de colección: {collection_name}")
    
    # Verificar si la colección existe
    collection_names = [col.name for col in chroma_client.list_collections()]
    
    if collection_name not in collection_names:
        available_collections = ', '.join(collection_names)
        raise Exception(f"La colección '{collection_name}' no se encuentra en Chroma. "
                       f"Colecciones disponibles: {available_collections}. "
                       f"Asegúrate de ejecutar 'process_data.py' primero para crear las colecciones.")
    
    # Obtener la colección
    chroma_collection = chroma_client.get_collection(name=collection_name, embedding_function=embedding_function)
    print(f"Colección '{collection_name}' cargada exitosamente.\n")
    
    return chroma_collection

def rag(query, retrieved_documents):
    information = "\n\n".join(retrieved_documents)

    # Construimos los mensajes
    messages = [
        SystemMessage(
            content=(
                "You are a helpful expert assistant specialized in creating multiple-choice questions "
                "for Peruvian primary education (grades 1 to 6) according to the national curriculum. "
                "The user will always provide a complete topic structure in the following format: "
                "'<Área> - <Grado> - <Subtema> - <Cantidad de preguntas>'. "
                "You must ONLY use the provided topic as the context for generating questions. "
                "Each question must be suitable for the indicated grade level, "
                "with age-appropriate vocabulary and concepts according to the Peruvian curriculum. "
                "For each question, you must provide exactly four answer choices (A, B, C, D), "
                "where only one choice is correct. "
                "Clearly indicate which choice is correct using an integer from 1 to 4 "
                "(1 = A, 2 = B, 3 = C, 4 = D). "
                "Return the final result as a JSON-formatted string in the following structure: "
                "[ "
                "  { "
                '  "pregunta": "Pregunta específica", '
                '  "alternativa_A": "detalle de la alternativa", '
                '  "alternativa_B": "detalle de la alternativa", '
                '  "alternativa_C": "detalle de la alternativa", '
                '  "alternativa_D": "detalle de la alternativa", '
                '  "alternativa_correcta": entero del 1 al 4 '
                "  }, "
                "  {...} "
                "] "
            )
        ),
        HumanMessage(
            content=f"Question: {query}\n\nInformation:\n{information}"
        )
    ]

    # Ejecuta el modelo con los mensajes
    response = llm.invoke(messages)

    return response

def execute_rag_for_query(query):
    """
    Ejecuta el pipeline RAG completo para una query específica
    """
    try:
        print(f"Procesando query: {query}")
        
        # Obtener la colección correspondiente basada en la query
        chroma_collection = get_collection_for_query(query)

        # Realizar la búsqueda en la colección específica
        results = chroma_collection.query(query_texts=[query], n_results=5)

        # Obtener todos los documentos de la consulta
        retrieved_documents = results['documents'][0]

        # Ejecutar la consulta RAG
        output = rag(query=query, retrieved_documents=retrieved_documents)
        
        return output
        
    except Exception as e:
        print(f"Error procesando query '{query}': {str(e)}")
        return None

# Función principal que permite entrada dinámica
def main():
    import sys
    
    if len(sys.argv) > 1:
        # Si se proporciona una query como argumento de línea de comandos
        query = sys.argv[1]
    else:
        # Query por defecto para pruebas
        query = "Ciencia y Tecnología - Primer Grado - Reconocemos las plantas como seres vivos - 5 preguntas"
    
    # Ejecutar RAG
    output = execute_rag_for_query(query)
    
    if output:
        print("\n=== RESULTADO ===")
        print(word_wrap(output))
    else:
        print("No se pudo generar respuesta para la query.")

if __name__ == "__main__":
    main()
