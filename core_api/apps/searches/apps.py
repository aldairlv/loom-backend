from django.apps import AppConfig


class SearchesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'searches'

    def ready(self):
        import searches.signals  # noqa: F401
