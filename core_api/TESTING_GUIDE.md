"""
TESTING GUIDE - Pruebas Locales de WebSockets y Push Notifications

Este archivo contiene ejemplos para probar toda la funcionalidad.
"""

# ================================================================
# TEST 1: Verificar que Firebase está configurado
# ================================================================

# En Django Shell:
# python manage.py shell

import django
django.setup()

from django.conf import settings
import firebase_admin

# Verificar que Firebase está configurado
if firebase_admin._apps:
    print("✅ Firebase está correctamente inicializado")
else:
    print("❌ Firebase NO está inicializado")
    print(f"FIREBASE_CREDENTIALS_PATH: {settings.FIREBASE_CREDENTIALS}")

# Verificar Redis
from django.core.cache import cache
try:
    cache.set('test_key', 'test_value', timeout=10)
    value = cache.get('test_key')
    if value == 'test_value':
        print("✅ Redis está funcionando correctamente")
    else:
        print("❌ Redis NO está funcionando")
except Exception as e:
    print(f"❌ Error de Redis: {str(e)}")

# Verificar Channels
from channels.layers import get_channel_layer
import asyncio

channel_layer = get_channel_layer()
print(f"✅ Channel Layer: {channel_layer}")


# ================================================================
# TEST 2: Registrar un dispositivo FCM
# ================================================================

# Con curl:
"""
curl -X POST http://localhost:8000/api/v1/notifications/devices/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "device_001",
    "registration_token": "eXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "device_type": "android"
  }'
"""

# O en Python:
import requests

token = "YOUR_JWT_TOKEN"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

response = requests.post(
    "http://localhost:8000/api/v1/notifications/devices/",
    headers=headers,
    json={
        "device_id": "test-device-001",
        "registration_token": "test_fcm_token_12345",
        "device_type": "android"
    }
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")


# ================================================================
# TEST 3: Listar dispositivos del usuario
# ================================================================

response = requests.get(
    "http://localhost:8000/api/v1/notifications/devices/",
    headers=headers
)

print(f"Dispositivos: {response.json()}")


# ================================================================
# TEST 4: Conectarse al WebSocket
# ================================================================

# Opción 1: Con wscat (CLI)
"""
npm install -g wscat
wscat -c "ws://localhost:8000/ws/notifications/?token=YOUR_JWT_TOKEN"

# En la terminal, deberías ver:
# Connected (press CTRL+C to quit)
# >
"""

# Opción 2: Con Python websockets
import asyncio
import websockets
import json

async def test_websocket():
    token = "YOUR_JWT_TOKEN"
    uri = f"ws://localhost:8000/ws/notifications/?token={token}"
    
    async with websockets.connect(uri) as websocket:
        print("✅ Conectado al WebSocket")
        
        # Enviar ping
        await websocket.send(json.dumps({
            "type": "ping"
        }))
        
        # Recibir pong
        message = await websocket.recv()
        print(f"Recibido: {message}")
        
        # Esperar notificaciones
        print("Esperando notificaciones... (Ctrl+C para salir)")
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"📢 Notificación: {data}")

# Ejecutar en la terminal
# asyncio.run(test_websocket())


# ================================================================
# TEST 5: Disparar una notificación de Like
# ================================================================

# En Django Shell:
# python manage.py shell

from notifications.tasks import send_like_notification
from django.contrib.auth import get_user_model
from posts.models import Post
from uuid import uuid4

User = get_user_model()

# Obtener usuarios
actor = User.objects.first()          # Usuario que da like
recipient = User.objects.all()[1]     # Usuario que recibe notificación
post = Post.objects.first()           # Post que recibe like

print(f"Actor: {actor.username}")
print(f"Recipient: {recipient.username}")
print(f"Post: {post.id}")

# Disparar tarea
result = send_like_notification.delay(
    actor_id=actor.id,
    recipient_id=recipient.id,
    post_id=str(post.id)
)

print(f"✅ Tarea disparada: {result.id}")

# Ver resultado
print(f"Resultado: {result.get()}")  # Espera a que se complete


# ================================================================
# TEST 6: Verificar que el usuario está online
# ================================================================

from notifications.services import NotificationService

user_id = recipient.id
is_online = NotificationService.is_user_online(user_id)

print(f"¿Usuario {recipient.username} está online? {is_online}")


# ================================================================
# TEST 7: Obtener historial de notificaciones
# ================================================================

response = requests.get(
    "http://localhost:8000/api/v1/notifications/",
    headers=headers
)

print(f"Notificaciones: {response.json()}")


# ================================================================
# TEST 8: Simular usuario desconectado (FCM fallback)
# ================================================================

# 1. Cerrar sesión WebSocket (o no conectarse)
# 2. Disparar notificación
# 3. Ver que se envía a Firebase en lugar de WebSocket

# En logs de Celery, deberías ver:
# "Notificación like enviada por método: fcm"


# ================================================================
# TEST 9: Marcar notificación como leída
# ================================================================

# Vía WebSocket:
"""
wscat -c "ws://localhost:8000/ws/notifications/?token=YOUR_JWT_TOKEN"

# Enviar:
{
  "type": "mark_read",
  "notification_id": "550e8400-e29b-41d4-a716-446655440000"
}

# Respuesta: La notificación se marcará como leída en BD
"""


# ================================================================
# TEST 10: Verificar logs de Celery
# ================================================================

"""
En terminal con Celery Worker activo (celery -A loom worker -l info):

Deberías ver algo como:
    [2026-06-05 10:30:45,123: INFO/MainProcess] Received task: notifications.tasks.send_like_notification[...]
    [2026-06-05 10:30:46,456: INFO/MainProcess] Notificación de like enviada a user1 por método: websocket
    [2026-06-05 10:30:46,789: INFO/MainProcess] Task notifications.tasks.send_like_notification[...] succeeded in 0.5s: {...}
"""


# ================================================================
# CHECKLIST COMPLETO
# ================================================================

"""
✅ Instalación
    [ ] pip install firebase-admin channels-redis
    [ ] pip freeze > requirements.txt

✅ Configuración Django
    [ ] settings.py - ASGI_APPLICATION agregado
    [ ] settings.py - CHANNEL_LAYERS configurado
    [ ] settings.py - FIREBASE_CREDENTIALS_PATH configurado
    [ ] asgi.py actualizado con WebSocket routing

✅ Archivos Creados
    [ ] notifications/consumers.py - WebSocket Consumer
    [ ] notifications/routing.py - WebSocket routing
    [ ] notifications/services.py - Lógica de notificaciones
    [ ] notifications/tasks.py - Tareas de Celery

✅ Firebase
    [ ] Firebase project creado en console.firebase.google.com
    [ ] JSON de credenciales descargado
    [ ] JSON colocado en /config/firebase-credentials.json
    [ ] FIREBASE_CREDENTIALS_PATH en .env

✅ Redis
    [ ] Redis instalado/corriendo (redis-server)
    [ ] REDIS_HOST y REDIS_PORT configurados

✅ Servicios Levantados
    [ ] Django: python manage.py runserver
    [ ] Celery Worker: celery -A loom worker -l info
    [ ] Celery Beat: celery -A loom beat -l info
    [ ] Redis: redis-server

✅ Tests
    [ ] Test 1 - Firebase inicializado
    [ ] Test 2 - Registrar dispositivo
    [ ] Test 3 - Listar dispositivos
    [ ] Test 4 - Conectar WebSocket
    [ ] Test 5 - Disparar notificación de Like
    [ ] Test 6 - Verificar usuario online
    [ ] Test 7 - Obtener historial de notificaciones
    [ ] Test 8 - Simular FCM fallback
    [ ] Test 9 - Marcar como leída
    [ ] Test 10 - Ver logs de Celery

✅ Integración en Apps
    [ ] interactions/views.py - Llamar send_like_notification.delay()
    [ ] relationships/views.py - Llamar notify_new_follow.delay()
    [ ] posts/views.py - Llamar send_interaction_notification.delay()

✅ Producción Ready
    [ ] Usar Daphne en lugar de runserver
    [ ] Usar worker manager (systemd o supervisor)
    [ ] Configurar Sentry para error tracking
    [ ] Usar certificados SSL/TLS para WebSocket
"""


# ================================================================
# TROUBLESHOOTING - Comandos de Diagnóstico
# ================================================================

"""
# Ver si Celery tasks están siendo ejecutadas
celery -A loom events -c "django_celery_beat.schedulers:DatabaseScheduler"

# Monitor de Redis
redis-cli
> KEYS "user_online_*"  # Ver usuarios online
> GET "user_online_1"   # Ver usuario específico

# Ver tareas en cola (pending)
celery -A loom inspect active

# Ver historial de tareas completadas
celery -A loom inspect stats

# Limpiar queue de Celery
celery -A loom purge

# Ver si Django puede acceder a Firebase
python manage.py shell
> import firebase_admin
> from firebase_admin import messaging
> print(firebase_admin._apps)  # Debe mostrar una app inicializada
"""
