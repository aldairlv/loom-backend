from rest_framework import serializers
from .models import Tag

class TagRelatedField(serializers.SlugRelatedField):
    """
    Un campo personalizado para manejar tags.
    Hereda de SlugRelatedField para la representación (lectura),
    pero sobrescribe el manejo de la entrada (escritura) para crear tags si no existen.
    """
    def to_internal_value(self, data):
        # `get_or_create` devuelve una tupla (objeto, created_boolean)
        # Nosotros solo necesitamos el objeto.
        tag, created = Tag.objects.get_or_create(name=data.lower())
        if created:
            # Opcional: puedes imprimir o loggear cuando se crea un nuevo tag
            print(f"Nuevo tag creado: '{tag.name}'")
        return tag