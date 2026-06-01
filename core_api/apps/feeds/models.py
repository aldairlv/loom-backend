from django.db import models
# feed/models.py
import uuid
from django.conf import settings

class PendingFeedItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pending_feed_items')
    
    # E.g., "TAGS_SUGGESTION", "USER_SUGGESTION"
    tipo = models.CharField(max_length=50) 
    titulo = models.CharField(max_length=255)
    
    # Aquí guardas los IDs de los perfiles o tags recomendados: {"ids": ["uuid-1", "uuid-2"]}
    payload = models.JSONField(default=dict) 
    
    is_consumed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']