import logging
import os

logger = logging.getLogger(__name__)


def ensure_firebase_initialized():
    """
    Inicializa Firebase Admin SDK si aún no está inicializado.

    Returns:
        tuple[bool, str | None]: (ok, error_message)
    """
    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        return False, 'firebase-admin no está instalado'

    if firebase_admin._apps:
        return True, None

    cred_path = os.environ.get('FIREBASE_CREDENTIALS_PATH')
    if not cred_path:
        return False, (
            'FIREBASE_CREDENTIALS_PATH no está configurado. '
            'Añádelo al .env (ej: /app/config/firebase-credentials.json).'
        )

    if not os.path.exists(cred_path):
        return False, f'Archivo de credenciales Firebase no encontrado: {cred_path}'

    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    logger.info('Firebase Admin SDK inicializado correctamente.')
    return True, None
