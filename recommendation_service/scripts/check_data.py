from core.chroma_manager import collection
import json

def debug_chroma():
    # .get() sin parámetros trae los datos de la colección actual
    # limitamos a 10 para no saturar la consola
    data = collection.get(
        limit=10,
        include=["embeddings", "metadatas", "documents"] 
    )

    if not data["ids"]:
        print("Empty collection 📭")
        return

    print(f"\n--- EXPLORANDO CHROMA: {len(data['ids'])} registros encontrados ---")
    
    for i in range(len(data['ids'])):
        print(f"\n📍 Registro {i+1}")
        print(f"ID: {data['ids'][i]}")
        print(f"Metadatos: {json.dumps(data['metadatas'][i], indent=2)}")
        
        # El vector (embedding)
        embedding = data['embeddings'][i]
        print(f"Embedding (dimensión {len(embedding)}): {embedding[:5]}... (truncado)")
        
        # Documento (si lo usaste, si no aparecerá None)
        print(f"Documento: {data['documents'][i] if data['documents'] else 'No definido'}")
        print("-" * 40)

if __name__ == "__main__":
    debug_chroma()