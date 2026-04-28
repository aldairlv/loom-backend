from django.conf import settings
from django.db import models
import uuid


class Blog(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=32, unique=True) # "istalkfashion"
    title = models.CharField(max_length=255, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blogs')
    
    # En el JSON se devuelve como un array de distintos tamaños
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    
    # Descripción en formato NPF (se puede usar un JSONField para guardar la lista de textos)
    description_npf = models.JSONField(default=list) 
