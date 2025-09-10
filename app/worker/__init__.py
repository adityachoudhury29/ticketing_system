# filepath: /home/aditya/Desktop/project/app/worker/__init__.py
# Keep this file minimal to avoid circular imports during Celery startup.
from .celery_app import celery_app
