"""
Firebase Configuration Guide for Push Notifications

Este archivo contiene las instrucciones para configurar Firebase Cloud Messaging (FCM)
en tu aplicación Django.

PASO 1: Obtener credenciales de Firebase
==========================================
1. Ve a https://console.firebase.google.com/
2. Crea un nuevo proyecto o selecciona uno existente
3. Ve a Configuración del Proyecto > Cuentas de servicio
4. Haz clic en "Generar nueva clave privada"
5. Descarga el archivo JSON

PASO 2: Colocar el archivo en tu servidor
==========================================
- Copia el archivo JSON descargado a una ubicación segura
- Ejemplo: /app/config/firebase-credentials.json

PASO 3: Configurar variables de entorno
==========================================
En tu archivo .env o docker-compose.yml, agrega:

    FIREBASE_CREDENTIALS_PATH=/app/config/firebase-credentials.json

PASO 4: Verificar que Firebase está inicializado
==========================================
Django lo inicializará automáticamente cuando levantes el servidor.

VERIFICAR CONFIGURACIÓN:
========================
Puedes verificar que Firebase está correctamente configurado en:
- Django Admin > Consultar logs

ESTRUCTURA DEL ARCHIVO JSON (EJEMPLO):
=====================================
{
  "type": "service_account",
  "project_id": "tu-proyecto",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n",
  "client_email": "firebase-adminsdk@tu-proyecto.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
"""

# Este archivo es solo documentación - la configuración real ocurre en settings.py
