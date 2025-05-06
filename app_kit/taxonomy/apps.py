from django.apps import AppConfig


class TaxonomyConfig(AppConfig):
    name = 'taxonomy'
    
    def ready(self):
        import taxonomy.signals
