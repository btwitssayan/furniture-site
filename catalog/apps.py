from django.apps import AppConfig


class CatalogConfig(AppConfig):
    name = 'catalog'
    default_auto_field = 'django.db.models.AutoField'

    def ready(self):
        from . import signals  # noqa: F401  (registers the search-vector hooks)
