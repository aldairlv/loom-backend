# WebSockets + Push Notifications Architecture

## Arquitectura General del Sistema

Tu aplicación ahora soporta **notificaciones en tiempo real** con una arquitectura híbrida:

```
┌─────────────────────────────────────────────────────────────┐
│                      Usuario Abre la App                    │
│                                                              │
│   ┌──────────────────────────────────────────────────┐     │
│   │  App se conecta a WebSocket /ws/notifications/  │     │
│   │  Usuario se marca como ONLINE en Redis          │     │
│   └────────────────────────┬─────────────────────────┘     │
│                            │                                 │
│                            ▼                                 │
│              ┌─────────────────────────────┐               │
│              │ Evento: Usuario A da Like   │               │
│              │ a Usuario B                 │               │
│              └────────────┬────────────────┘               │
│                           │                                 │
│                  ┌────────▼─────────┐                     │
│                  │ Celery Task      │                     │
│                  │ (Background Job) │                     │
│                  └────────┬─────────┘                     │
│                           │                                 │
│                ┌──────────▼──────────┐                    │
│                │ ¿Usuario B Online?  │                    │
│                └──────┬───────┬──────┘                    │
│                       │       │                            │
│                   SÍ │       │ NO                         │
│                       ▼       ▼                            │
│              ┌─────────────┐  ┌──────────────┐            │
│              │ WebSocket   │  │ Firebase     │            │
│              │ (instantáneo)│  │ Push FCM     │            │
│              │ + BD        │  │ (batería)    │            │
│              └─────────────┘  └──────────────┘            │
│                                                              │
│              ┌─────────────────────────────┐              │
│              │ Usuario B recibe notificación│              │
│              │ en tiempo real o como Push  │              │
│              └─────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

## Componentes Implementados

### 1. **Django Channels** - WebSockets en tiempo real
- Cuando la app está abierta, mantiene una conexión persistente
- Recibe notificaciones instantáneamente por WebSocket
- No consume batería innecesariamente

### 2. **Celery + Redis** - Tareas asincrónicas
- Procesa notificaciones en segundo plano
- Verifica si el usuario está online (en Redis)
- Decide si enviar por WebSocket o FCM

### 3. **Firebase Cloud Messaging (FCM)** - Push Notifications
- Cuando la app está cerrada o en background
- Entrega notificaciones a través del sistema operativo
- Soporta Android, iOS y Web

### 4. **Redis** - Capa de comunicación
- Almacena estado de conexiones WebSocket
- Cache para información de usuarios online
- Broker para Celery

### 5. **PostgreSQL** - Base de datos
- Registra `UserDevice` (dispositivos del usuario)
- Almacena `Notification` (historial de notificaciones)
- Rastrea `is_read` estado de cada notificación

## Archivos Creados/Modificados

```
core_api/
├── loom/
│   ├── settings.py          ✏️ Agregado: CHANNEL_LAYERS, FIREBASE, ASGI_APPLICATION
│   ├── asgi.py              ✏️ Actualizado para soportar WebSockets
│   └── celery.py            ✓ Sin cambios requeridos
│
├── apps/notifications/
│   ├── consumers.py         ✨ NUEVO - WebSocket Consumer
│   ├── routing.py           ✨ NUEVO - Rutas de WebSocket
│   ├── services.py          ✏️ Reescrito - Servicio de notificaciones
│   ├── tasks.py             ✏️ Actualizado - Tareas de Celery
│   ├── models.py            ✓ Sin cambios requeridos (UserDevice ya existe)
│   ├── views.py             ✓ RegisterDeviceView ya existe
│   ├── serializers.py       ✓ UserDeviceSerializer ya existe
│   └── urls.py              ✓ Ya incluye endpoints de dispositivos
│
└── FIREBASE_CONFIG.md       ✨ NUEVO - Guía de configuración
└── INTEGRATION_EXAMPLES.md  ✨ NUEVO - Ejemplos de integración
```

## Setup y Configuración

### Paso 1: Instalar dependencias
```bash
pip install firebase-admin channels-redis redis
pip freeze > requirements.txt
```

✅ Ya completado en tu entorno.

### Paso 2: Configurar Firebase Cloud Messaging

1. Ve a [Firebase Console](https://console.firebase.google.com/)
2. Crea un proyecto o selecciona uno existente
3. Descarga credenciales JSON (Configuración > Cuentas de servicio > Nueva clave privada)
4. Coloca el archivo en: `core_api/config/firebase-credentials.json`

### Paso 3: Configurar variables de entorno

En tu `.env` o `docker-compose.yml`:

```bash
# Firebase
FIREBASE_CREDENTIALS_PATH=/app/config/firebase-credentials.json

# Redis (Channels + Celery)
REDIS_HOST=redis
REDIS_PORT=6379

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

### Paso 4: Ejecutar migraciones

```bash
python manage.py makemigrations
python manage.py migrate
```

### Paso 5: Iniciar servicios

```bash
# Terminal 1: Django (HTTP + WebSocket)
python manage.py runserver

# Terminal 2: Celery Worker
celery -A loom worker -l info

# Terminal 3: Celery Beat (scheduler para tareas periódicas)
celery -A loom beat -l info

# Terminal 4: Redis (si no usas Docker)
redis-server
```

O con Docker Compose:

```bash
docker-compose up -d
```

## Cómo Funciona

### Flujo cuando usuario A da Like al post de usuario B

1. **Cliente (App Mobile)**
   ```
   POST /api/v1/interactions/likes/
   {
       "post_id": "550e8400-e29b-41d4-a716-446655440000"
   }
   ```

2. **Django View** registra el Like en BD
   ```python
   like, created = Like.objects.create(profile=user.profile, post=post)
   
   if created:
       # Disparar tarea en Celery (no espera respuesta)
       send_like_notification.delay(
           actor_id=user.id,
           recipient_id=post.author.id,
           post_id=str(post.id)
       )
   ```

3. **Celery Worker** recibe la tarea
   ```
   Tarea: send_like_notification
   - Busca al usuario B en Redis
   - Verifica: ¿Usuario B está online?
   ```

4. **Si está online** (WebSocket conectado)
   ```
   - Envía por WebSocket instantáneamente
   - App muestra: "Juan te dio un like" con animación
   - Sin Push Notification
   - Sin consumo de batería
   ```

5. **Si está offline** (sin WebSocket)
   ```
   - Busca dispositivos FCM del usuario B
   - Envía Push Notification a Firebase
   - Google/Apple entrega a su teléfono
   - Usuario ve notificación en la barra
   ```

6. **BD**: Registra Notification como `is_read=False`
   - Cuando usuario B abre la notificación, marca como `is_read=True`

## API Endpoints

### Notificaciones (WebSocket)
```
ws://localhost:8000/ws/notifications/
    - Requiere autenticación con JWT
    - Recibe mensajes en tiempo real
    - Envía heartbeat cada 30s: {"type": "ping"}
    - Marca como leído: {"type": "mark_read", "notification_id": "..."}
```

### Obtener historial de notificaciones
```
GET /api/v1/notifications/
    - Cursor pagination
    - Devuelve últimas 20 notificaciones leídas/no leídas
```

### Registrar dispositivo FCM
```
POST /api/v1/notifications/devices/
{
    "device_id": "ABC123XYZ",
    "registration_token": "eXXXXXXXXXXXXXXXXXXXXXXX",
    "device_type": "android"  // o "ios", "web"
}

GET /api/v1/notifications/devices/
    - Lista todos los dispositivos del usuario

DELETE /api/v1/notifications/devices/{device_id}/
    - Desactiva un dispositivo
```

## Prueba Local

### 1. Registrar dispositivo
```bash
curl -X POST http://localhost:8000/api/v1/notifications/devices/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "test-device-001",
    "registration_token": "test_fcm_token_12345",
    "device_type": "android"
  }'
```

### 2. Conectarse al WebSocket
```bash
# Usar wscat o una librería WebSocket
wscat -c "ws://localhost:8000/ws/notifications/?token=YOUR_JWT_TOKEN"
```

### 3. Simular un Like en otra terminal
```bash
# Django shell
python manage.py shell

from notifications.tasks import send_like_notification
send_like_notification.delay(
    actor_id=1,
    recipient_id=2,
    post_id="550e8400-e29b-41d4-a716-446655440000"
)
```

### 4. Ver notificación en WebSocket
En la terminal con wscat, deberías ver:
```json
{
  "type": "like",
  "data": {
    "actor_id": 1,
    "actor_name": "Juan Pérez",
    "post_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

## Troubleshooting

### "Redis connection refused"
- Verifica que Redis está corriendo: `redis-cli ping`
- Revisa `REDIS_HOST` y `REDIS_PORT` en settings

### "Firebase credentials not found"
- Verifica ruta: `FIREBASE_CREDENTIALS_PATH=/app/config/firebase-credentials.json`
- El archivo JSON debe ser válido

### "WebSocket connection closed"
- Verifica que `asgi.py` está correctamente configurado
- Asegúrate de usar Daphne (en `INSTALLED_APPS`)
- Para desarrollo: `python manage.py runserver` (Daphne automáticamente)

### "Celery tasks no se ejecutan"
- Inicia el worker: `celery -A loom worker -l info`
- Verifica logs: `tail -f logs/celery.log`
- Comprueba conexión a broker Redis

## Próximos Pasos

1. **Integrar en Interactions App** - Modificar vistas de Like/Follow/Comment
2. **Actualizar Cliente Mobile** - Conectar WebSocket desde Kotlin
3. **Tests** - Crear test cases para notificaciones
4. **Monitoring** - Agregar Sentry o similar para errores en producción

## Referencias

- [Django Channels Docs](https://channels.readthedocs.io/)
- [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup)
- [Celery + Django](https://docs.celeryproject.io/en/stable/django/)
- [Redis Docs](https://redis.io/documentation)
