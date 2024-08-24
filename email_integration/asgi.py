"""
ASGI config for email_integration project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'email_integration.settings')
django_asgi_app = get_asgi_application()

from django.urls import path  # noqa: E402

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from email_integration.mail.consumers import MailConsumer  # noqa: E402


application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter([
            path('ws/mail/', MailConsumer.as_asgi())
        ])
    ),
})
