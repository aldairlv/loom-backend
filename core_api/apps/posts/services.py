from django.db import connection, transaction
from .models import Post, PostContent


def build_post_trail(post):
    """Construye el trail de ancestros desde el post más antiguo hasta el padre directo."""
    if not post.parent_id:
        return []

    ancestor_ids = []
    if connection.vendor == 'postgresql':
        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH RECURSIVE ancestors AS (
                    SELECT id, parent_id, 0 AS level
                    FROM posts_post
                    WHERE id = %s
                  UNION ALL
                    SELECT p.id, p.parent_id, a.level + 1
                    FROM posts_post p
                    JOIN ancestors a ON p.id = a.parent_id
                )
                SELECT id
                FROM ancestors
                WHERE id != %s
                ORDER BY level DESC
                """,
                [post.id, post.id],
            )
            ancestor_ids = [row[0] for row in cursor.fetchall()]

    if not ancestor_ids:
        current = post.parent
        while current:
            ancestor_ids.append(current.id)
            current = current.parent
        ancestor_ids.reverse()

    if not ancestor_ids:
        return []

    queryset = Post.objects.filter(id__in=ancestor_ids).select_related('author').prefetch_related('contents')
    posts_by_id = {post.id: post for post in queryset}
    ordered_posts = [posts_by_id[post_id] for post_id in ancestor_ids if post_id in posts_by_id]
    trail_posts = [ancestor for ancestor in ordered_posts if ancestor.contents.exists()]
    return trail_posts


def create_post(author, data, contents_data=None):
    """Crea un post, sus tags y sus contenidos asociados."""
    tags = data.pop('tags', []) # Los tags ya son objetos Tag gracias a TagRelatedField
    contents_data = contents_data or [] # Viene de 'contents_input'

    # Extraer parent_id y root_id de data.
    # Los eliminamos de 'data' para no pasarlos como UUIDs directamente a Post.objects.create,
    # sino como objetos Post después de la lógica.
    parent_post_obj = data.pop('parent', None) # Ya es un objeto Post o None gracias al serializer
    root_post_obj = data.pop('root', None) # Ya es un objeto Post o None
    
    with transaction.atomic():
        # 1. parent_post_obj ya es un objeto Post (o None) gracias al serializador
        data['parent'] = parent_post_obj

        # 2. Manejar la relación 'root' basada en 'parent' o un 'root_id' explícito
        if parent_post_obj:
            # Si hay un post padre, el 'root' del nuevo post es el 'root' del padre,
            # o el padre mismo si el padre es un post original.
            root_post_obj = parent_post_obj.root if parent_post_obj.root else parent_post_obj
        # Si no hay parent_post_obj y root_post_obj ya es un objeto Post (o None),
        # lo mantenemos como está. Si no se proporcionó root_post_id, root_post_obj será None.

        data['root'] = root_post_obj # Asignar el objeto Post real (o None)

        # 3. Crear el nuevo post. 'data' ahora contiene 'status', 'layout', etc.
        post = Post.objects.create(author=author, **data)
        
        # 4. Añadir tags
        if tags:
            post.tags.set(tags)
        
        # 5. Manejar contenidos (lógica actualizada)
        if contents_data:
            # Crear PostContent a partir de la lista 'contents_input'.
            # El 'order' se basa en el índice de la lista.
            for i, content_item in enumerate(contents_data):
                content_item['order'] = i # Asignación implícita del orden
                PostContent.objects.create(post=post, **content_item)

        return post

def update_post(post, data):
    """Actualiza un post existente."""
    tags = data.pop('tags', None)
    
    for attr, value in data.items():
        setattr(post, attr, value)
    post.save()
    
    if tags is not None:
        post.tags.set(tags)
    return post

def delete_post(post):
    """Implementa un borrado lógico (soft delete)."""
    post.is_deleted = True
    post.save()