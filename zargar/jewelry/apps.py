from django.apps import AppConfig


class JewelryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'zargar.jewelry'
    verbose_name = 'Jewelry Management'
    
    def ready(self):
        """Import signals when app is ready."""
        try:
            import zargar.jewelry.signals
        except ImportError as e:
            # Temporarily ignore import errors during development
            print(f"Warning: Could not import signals: {e}")