from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'profiles'

    def ready(self):
        """
        Importa las señales cuando la aplicación está lista.
        """
        import profiles.signals