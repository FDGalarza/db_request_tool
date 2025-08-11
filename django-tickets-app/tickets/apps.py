from django.apps import AppConfig

class TicketsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tickets'
    
    def ready(self):
        # Importar señales si las necesitas
        pass
