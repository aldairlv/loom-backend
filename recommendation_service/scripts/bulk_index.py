import os
import psycopg2
import requests
from PIL import Image
from io import BytesIO
from tabulate import tabulate
import numpy as np

from core.model_loader import get_model
from core.chroma_manager import collection

def run_bulk_sync():
    """
    Sincroniza los posts de PostgreSQL con ChromaDB, generando embeddings para texto e imágenes.
    """
    # 1. Conexión a la base de datos usando la variable de entorno (más seguro)
    conn_str = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://")
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    
    # 2. Query para obtener todos los datos necesarios de los posts
    cur.execute("""
    SELECT 
    p.id, 
    COALESCE(t.tag_list, 'Sin tags') as tags,
    COALESCE(txt.texto_completo, 'Sin texto') as texto,
    (
        SELECT ib.media->0->>'url'
        FROM posts_imageblock ib 
        JOIN posts_contentblock cb2 ON ib.contentblock_ptr_id = cb2.id 
        WHERE cb2.post_id = p.id 
        LIMIT 1
    ) as img_url
FROM posts_post p
-- Subquery para tags (sin duplicar filas principales)
LEFT JOIN (
    SELECT pt.post_id, STRING_AGG(DISTINCT t.name, ', ') as tag_list
    FROM posts_post_tags pt
    JOIN posts_tag t ON pt.tag_id = t.id
    GROUP BY pt.post_id
) t ON p.id = t.post_id
-- Subquery para texto (sin duplicar filas principales)
LEFT JOIN (
    SELECT post_id, STRING_AGG(text, ' ' ORDER BY "order") AS texto_completo
    FROM (
        SELECT DISTINCT cb.post_id, tb.text, cb."order"
        FROM posts_contentblock cb
        JOIN posts_textblock tb 
            ON cb.id = tb.contentblock_ptr_id
    ) sub
    GROUP BY post_id
) txt ON p.id = txt.post_id
    """)

    print("🔍 Ejecutando query en PostgreSQL...")
    rows = cur.fetchall()
    if not rows:
        print("✅ No hay nuevos posts para indexar.")
        cur.close()
        conn.close()
        return

    model = get_model()
    
    # 3. Imprimir un resumen de los datos obtenidos para depuración
    headers = ["ID", "Tags", "Texto (Primeros 50 caracteres)", "¿Tiene Imagen?"]
    table_data = []
    for row in rows:
        post_id, tags, texto, img_url = row
        texto_preview = (texto[:300] + '...') if len(texto) > 50 else texto
        tiene_img = "✅" if img_url else "❌"
        table_data.append([post_id, tags, texto_preview, tiene_img])
    
    print("\n--- DATOS OBTENIDOS DE LA BASE DE DATOS ---")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    print(f"\nTotal de posts a procesar: {len(rows)}\n")

    # 4. Procesar e indexar cada post
    print("🚀 Empezando proceso de embedding e indexación...")
    for post_id, tags, texto, img_url in rows:
        # Fusionar tags y texto para un embedding más rico en contexto
        texto_combinado = f"Tags: {tags}. Contenido: {texto}"
        print(texto_combinado)
        texto_seguro = texto_combinado[:230]
        text_vector = model.encode(texto_seguro, convert_to_numpy=True)

        # Si hay imagen, la descargamos, generamos su embedding y lo promediamos con el de texto
        if img_url:
            try:
                response = requests.get(img_url, stream=True, timeout=10)
                response.raise_for_status()
                img = Image.open(BytesIO(response.content))
                img_vector = model.encode(img, convert_to_numpy=True)
                # Promediamos los vectores para obtener una representación multimodal
                vector_final = (text_vector + img_vector) / 2.0
            except Exception as e:
                print(f"⚠️  Error al procesar imagen para post {post_id}: {e}. Usando solo texto.")
                vector_final = text_vector
        else:
            vector_final = text_vector

        # 5. Añadir el resultado a ChromaDB
        # Usamos 'upsert' para que si el ID ya existe, se actualice en lugar de duplicarse.
        collection.add(
            embeddings=[vector_final.tolist()],
            ids=[str(post_id)],
            metadatas=[{"tags": tags, "texto": texto}] # Metadatos para filtrado
        )
        print(f"✅ Post {post_id} indexado/actualizado.")
    
    
    print("\n🎉 Proceso de sincronización completado.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    # Este bloque permite ejecutar el script directamente desde la línea de comandos
    run_bulk_sync()
    
    ##print("🔍 Ejecutando query en PostgreSQL...")
