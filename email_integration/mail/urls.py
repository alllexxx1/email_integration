from django.urls import path

from email_integration.mail import views


urlpatterns = [
    path('account/add/', views.add_mail_account, name='add_mail_account'),
    path('messages/', views.mail_message_list, name='mail_message_list'),
]
