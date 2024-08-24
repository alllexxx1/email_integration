"""
URL configuration for email_integration project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from email_integration.mail.views import add_mail_account, mail_message_list


urlpatterns = [
    path('admin/', admin.site.urls),
    path('mail/', include('email_integration.mail.urls')),
    path('', add_mail_account, name='add_mail_account'),
    path('messages/', mail_message_list, name='mail_message_list'),
]
