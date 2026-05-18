from django.db import transaction
from .models import Post, PostContent

def create_post(author, data, contents_data=None):
    """Crea un post, sus tags y sus contenidos asociados."""
    tags = data.pop('tags', [])
    contents_data = contents_data or [] # Contenido nuevo proporcionado por el usuario para este reblog

    # Extraer parent_id y root_id de data.
    # Los eliminamos de 'data' para no pasarlos como UUIDs directamente a Post.objects.create,
    # sino como objetos Post después de la lógica.
    parent_post_id = data.pop('parent', None)
    root_post_obj = data.pop('root', None) # root_post_obj ya es un objeto Post o None

    with transaction.atomic():
        # 1. parent_post_obj ya es un objeto Post (o None) gracias al serializador
        parent_post_obj = parent_post_id # Renombramos para claridad
        data['parent'] = parent_post_obj

        # 2. Manejar la relación 'root' basada en 'parent' o un 'root_id' explícito
        if parent_post_obj:
            # Si hay un post padre, el 'root' del nuevo post es el 'root' del padre,
            # o el padre mismo si el padre es un post original.
            root_post_obj = parent_post_obj.root if parent_post_obj.root else parent_post_obj
        # Si no hay parent_post_obj y root_post_obj ya es un objeto Post (o None),
        # lo mantenemos como está. Si no se proporcionó root_post_id, root_post_obj será None.

        data['root'] = root_post_obj # Asignar el objeto Post real (o None)

        # 3. Crear el nuevo post
        post = Post.objects.create(author=author, **data)
        
        # 4. Añadir tags
        if tags:
            post.tags.set(tags)
        
        # 5. Manejar contenidos
        if contents_data:
            # Si el usuario proporcionó contenido nuevo para este reblog, usarlo.
            for i, content_item in enumerate(contents_data):
                if 'order' not in content_item:
                    content_item['order'] = i
                PostContent.objects.create(post=post, **content_item)
        elif parent_post_obj:
            # Si no se proporcionó contenido nuevo, pero hay un post padre, copiar su contenido.
            parent_post_contents = parent_post_obj.contents.all().order_by('order')
            for content_item in parent_post_contents:
                PostContent.objects.create(
                    post=post,
                    type=content_item.type,
                    order=content_item.order,
                    text=content_item.text,
                    media=content_item.media # Referenciar el mismo objeto Media (no duplicar)
                )

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