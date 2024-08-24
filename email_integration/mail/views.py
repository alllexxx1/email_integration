from django.shortcuts import render, redirect
from django.contrib import messages

from email_integration.mail.forms import MailAccountForm
from email_integration.mail.models import MailAccount, MailMessage
from email_integration.mail.utils import (
    fetch_emails,
    MailAuthenticationError,
    MailServerConnectionError
)


def add_mail_account(request):  # noqa: C901
    if request.method == 'POST':
        form = MailAccountForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            mail_account, created = MailAccount.objects.get_or_create(email=email)

            if created or mail_account.decrypt_password() != password:
                mail_account.password = password
                mail_account.save()

            try:
                fetch_emails(mail_account.email,
                             mail_account.decrypt_password(),
                             mail_account)
                messages.success(request, 'Письма успешно загружены.')
                return redirect('mail_message_list')
            except MailServerConnectionError as e:
                messages.error(request, f'Ошибка подключения: {e}')
            except MailAuthenticationError as e:
                messages.error(request, f'Ошибка аутентификации: {e}')
            except Exception as e:
                messages.error(request, f'Произошла ошибка при загрузке писем: {str(e)}')

    else:
        form = MailAccountForm()

    return render(request, 'mail/add_account.html', {'form': form})


def mail_message_list(request):
    messages = MailMessage.objects.all().order_by('-sent_date')
    return render(request, 'mail/message_list.html', {'messages': messages})
