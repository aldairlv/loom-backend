class MultiSerializerViewSetMixin:
    """
    Permite a un ViewSet usar diferentes serializadores para diferentes acciones.
    Define un diccionario `serializer_classes` en tu ViewSet:
    `serializer_classes = {'list': MyListSerializer, 'create': MyCreateSerializer}`
    """
    def get_serializer_class(self):
        try:
            return self.serializer_classes[self.action]
        except (KeyError, AttributeError):
            # Si no se define un serializador para la acción, usa el por defecto.
            return super().get_serializer_class()