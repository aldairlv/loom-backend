import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import requests

from .models import PendingInteraction

# Obtener un logger para este módulo
logger = logging.getLogger(__name__)

# URL del servicio de recomendaciones (usar nombre de servicio Docker)
RECOMMENDER_URL = "http://recommendation_service:8080/api/v1/users/recalculate-profile"


@shared_task(bind=True, name='core_api.apps.interactions.tasks.process_pending_interactions')
def process_pending_interactions(self):
    """
    Toma las interacciones pendientes no procesadas, las agrupa por usuario,
    envía un POST en lote al microservicio de recomendaciones y marca como
    procesadas las que se enviaron correctamente.
    """
    qs = PendingInteraction.objects.filter(processed=False).order_by('created_at')
    print(f"--- [TASK] Iniciando process_pending_interactions. Encontradas {qs.count()} interacciones pendientes. ---")
    if not qs.exists():
        print("--- [TASK] No hay interacciones pendientes. Finalizando. ---")
        return {"status": "no_pending"}

    # Agrupar por profile id
    print("--- [TASK] Agrupando interacciones por usuario... ---")
    batches = {}
    for pi in qs:
        uid = str(pi.profile_id)
        batches.setdefault(uid, []).append(pi)

    results = {"sent": 0, "failed": 0}

    for user_id, interactions in batches.items():
        payload = {
            "user_id": user_id,
            "interactions": [
                {
                    "content_id": i.content_id,
                    "content_type": i.content_type,
                    "action": i.action
                }
                for i in interactions
            ]
        }

        logger.info(f"Enviando payload para user_id={user_id}: {payload}")
        print(f"--- [TASK] Enviando payload para user_id={user_id}: {payload}")

        try:
            resp = requests.post(RECOMMENDER_URL, json=payload, timeout=10)
            logger.info(f"Respuesta para user_id={user_id}: status={resp.status_code}, body={resp.text}")
            print(f"--- [TASK] Respuesta para user_id={user_id}: status={resp.status_code}, body={resp.text}")

            if resp.status_code in (200, 201):
                # Marcar como procesadas
                with transaction.atomic():
                    now = timezone.now()
                    ids = [i.id for i in interactions]
                    print(f"--- [TASK] Marcando {len(ids)} interacciones como procesadas para user_id={user_id}.")
                    PendingInteraction.objects.filter(id__in=ids).update(processed=True, processed_at=now)
                logger.info(f"Interacciones para user_id={user_id} marcadas como procesadas.")
                results['sent'] += len(interactions)
            else:
                print(f"--- [TASK] ERROR: La petición para user_id={user_id} falló con status {resp.status_code}.")
                results['failed'] += len(interactions)
        except Exception as e:
            logger.exception(f"Fallo al procesar interacciones para user_id={user_id}. Error: {e}")
            print(f"--- [TASK] EXCEPTION al procesar user_id={user_id}. Error: {e}")
            results['failed'] += len(interactions)

    return results
