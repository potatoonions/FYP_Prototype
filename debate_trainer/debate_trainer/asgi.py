"""
ASGI config for debate_trainer project.
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "debate_trainer.settings")
application = get_asgi_application()

