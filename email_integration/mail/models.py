from cryptography.fernet import Fernet
import base64

from django.db import models
from django.conf import settings


def get_cipher():
    key = base64.urlsafe_b64encode(settings.SECRET_KEY[:32].encode())
    return Fernet(key)


class MailAccount(models.Model):
    email = models.EmailField()
    password = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        cipher = get_cipher()
        self.password = cipher.encrypt(self.password.encode()).decode()
        super().save(*args, **kwargs)

    def decrypt_password(self):
        cipher = get_cipher()
        return cipher.decrypt(self.password.encode()).decode()

    def __str__(self):
        return self.email


class MailMessage(models.Model):
    mail_account = models.ForeignKey(
        MailAccount,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    sent_date = models.DateTimeField()
    body = models.TextField()
    attachments = models.JSONField(default=list)

    def __str__(self):
        return f'Email from: {self.mail_account} | Subject: {self.subject}'
