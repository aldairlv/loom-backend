# core_api/loom/celery.py
import os
from celery import Celery

# Establecer las configuraciones por defecto de Django para Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'loom.settings')

app = Celery('loom')

# Lee las configuraciones que tengan el prefijo CELERY_ en settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descubre tareas en todas tus INSTALLED_APPS (buscará archivos tasks.py)
app.autodiscover_tasks()