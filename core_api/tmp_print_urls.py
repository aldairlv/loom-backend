import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'loom.settings')
import django
from django.urls import get_resolver, URLResolver

django.setup()

def walk(patterns, prefix=''):
    for p in patterns:
        if isinstance(p, URLResolver):
            print(prefix + str(p.pattern) + ' -> resolver')
            walk(p.url_patterns, prefix + str(p.pattern))
        else:
            methods = ','.join(p.callback.cls.http_method_names) if hasattr(p.callback, 'cls') else 'function'
            print(prefix + str(p.pattern) + ' -> ' + methods)

walk(get_resolver().url_patterns)
