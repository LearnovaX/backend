"""
WSGI project for core project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

from src.core.observability.tracing import setup_tracing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.core.settings")

setup_tracing()
application = get_wsgi_application()
