# posts/serializers.py
from rest_framework import serializers
from posts.models import Post
# Importamos el PostSerializer principal para reutilizar su estructura
from posts.serializers import PostSerializer
from profiles.serializers import ProfileSerializer
import uuid

# 1. El envoltorio del elemento individual del Feed
class FeedPostWrapperSerializer(serializers.Serializer):
    """
    Este serializador transforma un Post de la base de datos
    en el formato polimórfico que espera el frontend.
    """
    def to_representation(self, instance: Post | dict):
        # Soportamos tanto instancias de Post como payloads ya serializados desde Redis.
        if isinstance(instance, dict):
            post_data = instance
        else:
            post_data = PostSerializer(instance, context=self.context).data

        # Creamos el diccionario con la estructura polimórfica base
        polymorphic_data = {
            "objectType": "post",  # El discriminador clave
            "streamGlobalPosition": self.context.get('position', 0), # Opcional si quieres calcularlo en bucle
            "streamSessionId": self.context.get('session_id', '')
        }

        # Inyectamos todos los campos que devuelve PostSerializer en la raíz
        # del objeto para que cada elemento tenga exactamente la misma forma
        # que un `Post` serializado, pero con las claves extra del stream.
        # Aseguramos que el `id` sea string (PostSerializer normalmente ya lo hace).
        if isinstance(post_data, dict):
            polymorphic_data.update(post_data)
        else:
            # Fallback: si por alguna razón PostSerializer no devolviera dict
            polymorphic_data.update({
                "id": str(instance.id),
                "contents": post_data.get('contents') if hasattr(post_data, 'get') else None,
            })

        # Garantizar tipo de `id` como cadena
        polymorphic_data['id'] = str(polymorphic_data.get('id', instance.id))

        return polymorphic_data



# ==========================================
# 2. WRAPPERS VIRTUALES PARA COMPONENTES DE PENDIENTES
# ==========================================
class FeedTitleWrapperSerializer(serializers.Serializer):
    def to_representation(self, instance):
        # instance será un diccionario temporal creado en la vista
        return {
            "objectType": "title",
            "id": f"feedObject:title:{instance['pending_id'][:8]}",
            "text": instance['text'],
            "alignment": "left",
            "streamGlobalPosition": self.context.get('position', 0),
            "streamSessionId": self.context.get('session_id', '')
        }
    



# =======================================================
# SUB-SERIALIZADORES: Los elementos internos del Carrusel
# =======================================================

class CarouselUserCardSerializer(serializers.Serializer):
    """Estructura interna cuando el elemento es un Usuario.
    Inyecta todos los datos del perfil de manera similar a FeedPostWrapperSerializer.
    """
    def to_representation(self, instance):
        # Soportamos tanto instancias de Profile como payloads ya serializados desde Redis.
        if isinstance(instance, dict):
            profile_data = instance
        else:
            profile_data = ProfileSerializer(instance, context=self.context).data

        # Creamos el diccionario con la estructura polimórfica base para usuario
        polymorphic_data = {
            "objectType": "user",  # El discriminador clave
            "serveId": f"serve:user:{uuid.uuid4().hex[:8]}",
            "display": {
                "sponsored": False,
                "canDismiss": False,
                "reason": "En tu órbita"
            },
            "recommendationReason": None,
            "dismissal": {
                "options": [{"text": "No me interesa este usuario", "destructive": False}]
            }
        }

        # Inyectamos todos los campos que devuelve ProfileSerializer en la raíz
        # del objeto para que cada elemento tenga exactamente la misma forma
        # que un `Profile` serializado, pero con las claves extra de la recomendación.
        if isinstance(profile_data, dict):
            polymorphic_data.update(profile_data)
        else:
            # Fallback: si por alguna razón ProfileSerializer no devolviera dict
            polymorphic_data.update({
                "id": str(instance.id),
            })

        # Garantizar tipo de `id` como cadena
        polymorphic_data['id'] = str(polymorphic_data.get('id', instance.id))

        return polymorphic_data




class CarouselTagCardSerializer(serializers.Serializer):
    """Estructura interna cuando el elemento es un Tag/Etiqueta"""
    def to_representation(self, tag_name):
        return {
            "objectType": "tag_card",
            "id": f"feedObject:tag:{uuid.uuid4().hex[:8]}",
            "tag": tag_name,
            "isTrending": True
        }

# =======================================================
# SERIALIZADOR ENVOLTORIO PRINCIPAL DEL CAROUSEL
# =======================================================

class FeedCarouselWrapperSerializer(serializers.Serializer):
    """
    Se encarga de armar la raíz del carrusel y delegar el renderizado 
    de sus elementos internos según el tipo de sugerencia.
    """
    def to_representation(self, instance):
        tipo = instance.get('tipo')
        payload = instance.get('payload', {})
        pending_id = instance.get('pending_id', '')
        
        inner_elements = []
        
        # POLIMORFISMO DE SEGUNDO NIVEL: Evaluamos el tipo de carrusel
        if tipo == "USER_SUGGESTION":
            for item in payload.get('items', []):
                serializer = CarouselUserCardSerializer(item, context=self.context)
                inner_elements.append(serializer.data)
                
        elif tipo == "TAG_SUGGESTION":
            for tag_name in payload.get('tags', []):
                inner_elements.append(CarouselTagCardSerializer(tag_name).data)

        # Retornamos la raíz del objeto Carousel
        return {
            "objectType": "carousel",
            "id": f"feedObject:carousel:{pending_id[:8]}",
            "elements": inner_elements,
            "streamGlobalPosition": self.context.get('position', 0),
            "streamSessionId": self.context.get('session_id', '')
        }

# 2. El serializador de la respuesta global (Estructura Tumblr)
class FeedResponseSerializer(serializers.Serializer):
    meta = serializers.SerializerMethodField()
    response = serializers.SerializerMethodField()

    def get_meta(self, obj):
        request = self.context.get('request')
        user_id = str(request.user.id) if request and request.user.is_authenticated else None
        return {
            "status": 200,
            "msg": "OK",
            "xRoomUserId": user_id
        }

    def get_response(self, obj):
        # 'obj' aquí será la lista de posts devuelta por el servicio
        request = self.context.get('request')
        session_id = self.context.get('session_id', 'default_session')
        # Obtener el cursor enriquecido (puede ser None)
        cursor = self.context.get('cursor')
        start_position = self.context.get('start_position', 1)

        """elements_data = []
        for index, post in enumerate(obj):
            # position ahora parte desde start_position en vez de empezar siempre en 1
            position = start_position + index
            context = {'request': request, 'position': position, 'session_id': session_id}
            serializer = FeedPostWrapperSerializer(post, context=context)
            elements_data.append(serializer.data)"""
        
        # Iteramos sobre la lista unificada. La posición global se calcula en orden estricto (1, 2, 3...)
        elements_data = []
        for index, item in enumerate(obj):
            context = {'request': request, 'position': start_position + index, 'session_id': session_id}
            
            # Condición de renderizado polimórfico
            if isinstance(item, Post):
                serializer = FeedPostWrapperSerializer(item, context=context)
                elements_data.append(serializer.data)
                
            elif isinstance(item, dict) and item.get('virtual_type') == 'title':
                serializer = FeedTitleWrapperSerializer(item, context=context)
                elements_data.append(serializer.data)
                
            elif isinstance(item, dict) and item.get('virtual_type') == 'carousel':
                serializer = FeedCarouselWrapperSerializer(item, context=context)
                elements_data.append(serializer.data)

        return {
            "feed": {
                "elements": elements_data,
                "queryParams": {"cursor": cursor}
            }
        }