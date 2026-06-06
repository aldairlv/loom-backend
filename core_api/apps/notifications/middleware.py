from urllib.parse import parse_qs
import logging
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

User = get_user_model()

@database_sync_to_async
def get_user_from_token(token_key):
    """
    Obtiene el usuario asociado con un token de acceso JWT de forma asíncrona.
    Esta función se ejecuta en un hilo separado para no bloquear el event loop.
    """
    print(f"\n--- [JwtAuthMiddleware] Iniciando get_user_from_token ---")
    logger.info(f"[JwtAuthMiddleware] Intentando obtener usuario desde el token: {token_key[:15]}...")
    try:
        access_token = AccessToken(token_key)
        user_id = access_token.get('user_id')
        user = User.objects.get(id=user_id)
        print(f"--- [JwtAuthMiddleware] Éxito. Token válido para user_id: {user.id}, username: {user.username} ---")
        logger.info(f"[JwtAuthMiddleware] Token válido. Usuario encontrado: {user.username} (ID: {user.id})")
        return user
    except (InvalidToken, TokenError, User.DoesNotExist):
        print(f"--- [JwtAuthMiddleware] ERROR. Token inválido o usuario no existe. Devolviendo AnonymousUser. ---")
        logger.warning(f"[JwtAuthMiddleware] Token inválido o usuario no encontrado. Se devuelve AnonymousUser.")
        return AnonymousUser()


class JwtAuthMiddleware:
    """
    Middleware de autenticación JWT para Django Channels.
    Extrae el token de la query string y autentica al usuario de forma asíncrona.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        print(f"\n--- [JwtAuthMiddleware] Interceptando nueva conexión WebSocket ---")
        logger.info(f"[JwtAuthMiddleware] Nueva conexión WebSocket entrante. Path: {scope.get('path')}")

        query_string = scope.get("query_string", b"").decode("utf-8")
        print(f"--- [JwtAuthMiddleware] Query string: '{query_string}' ---")
        logger.debug(f"[JwtAuthMiddleware] Query string decodificada: {query_string}")

        query_params = parse_qs(query_string)
        token = query_params.get("token", [None])[0]

        if token:
            print(f"--- [JwtAuthMiddleware] Token encontrado en query params. Llamando a get_user_from_token. ---")
            scope['user'] = await get_user_from_token(token)
        else:
            print(f"--- [JwtAuthMiddleware] No se encontró token en query params. Asignando AnonymousUser. ---")
            logger.warning("[JwtAuthMiddleware] No se proporcionó token en la conexión WebSocket.")
            scope['user'] = AnonymousUser()

        return await self.app(scope, receive, send)