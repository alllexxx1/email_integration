from django import forms
from email_integration.mail import models


class MailAccountForm(forms.ModelForm):
    class Meta:
        model = models.MailAccount
        fields = ['email', 'password']
        widgets = {
            'password': forms.PasswordInput(),
        }
