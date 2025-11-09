from .celery import app as celery_app

# Expose Celery app as a module-level variable so `celery -A alx_travel_app` will find it
__all__ = ('celery_app',)
