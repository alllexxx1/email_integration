import imaplib
import email
from email.header import decode_header
from .models import MailMessage
from dateutil.parser import parse as date_parse
import re
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
import warnings
import os
from asgiref.sync import sync_to_async
import asyncio


class MailServerConnectionError(Exception):
    pass


class MailAuthenticationError(Exception):
    pass


def connect_to_mail_server(email_address, password):
    if email_address.endswith("gmail.com"):
        imap_server = 'imap.gmail.com'
    elif email_address.endswith('yandex.ru'):
        imap_server = 'imap.yandex.ru'
    elif email_address.endswith('mail.ru') or email_address.endswith('bk.ru'):
        imap_server = 'imap.mail.ru'
    else:
        raise ValueError('Unsupported email provider')
    try:
        imap = imaplib.IMAP4_SSL(imap_server)
        imap.login(email_address, password)
    except imaplib.IMAP4.error as e:
        raise MailAuthenticationError(f"Authentication failed: {str(e)}")

    return imap


def fetch_email_ids(mail):
    mail.select('INBOX')
    status, messages = mail.search(None, 'ALL')
    email_ids = messages[0].split()
    return email_ids


def decode_header_value(header_value):
    decoded_value, encoding = decode_header(header_value)[0]
    if isinstance(decoded_value, bytes):
        return decoded_value.decode(encoding or "utf-8")
    return decoded_value


def extract_email_metadata(msg):
    subject = decode_header_value(msg["Subject"])
    sender = decode_header_value(msg.get("From"))
    date = date_parse(msg.get("Date"))
    return subject, sender, date


def extract_email_body(msg):  # noqa: C901
    text_body = None
    html_body = None
    attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                    decoded_filename = decode_header_value(filename)
                    sanitized_filename = re.sub(r'[\\/*?:"<>|]', "", decoded_filename)
                    attachments.append(sanitized_filename)
            elif content_type == "text/plain":
                text_body = part.get_payload(decode=True).decode()
            elif content_type == "text/html":
                html_body = part.get_payload(decode=True).decode()

    else:
        content_type = msg.get_content_type()
        body = msg.get_payload(decode=True).decode()
        if content_type == "text/plain":
            text_body = body
        elif content_type == "text/html":
            html_body = body

    return text_body, html_body, attachments


def extract_essential_info_from_table(html_body):
    if not html_body.strip().startswith("<"):
        return ""

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", MarkupResemblesLocatorWarning)
        soup = BeautifulSoup(html_body, "lxml")

    tables = soup.find_all("table")
    essential_info = ""

    for table in tables:
        headers = []
        rows = table.find_all("tr")
        for i, row in enumerate(rows):
            cells = row.find_all(["td", "th"])
            cell_texts = [cell.get_text(strip=True) for cell in cells]

            if i == 0:  # считаем первую строку заголовком
                headers = cell_texts
            else:
                row_data = dict(zip(headers, cell_texts))
                for header, value in row_data.items():
                    essential_info += f"{header}: {value}\n"

    return essential_info.strip()


async def process_email(mail, email_id, mail_account, channel_layer, room_group_name):
    status, msg_data = mail.fetch(email_id, '(RFC822)')
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])

            subject, sender, date = extract_email_metadata(msg)

            exists = await sync_to_async(MailMessage.objects.filter(
                mail_account=mail_account,
                subject=subject, sender=sender,
                sent_date=date).exists)()
            if exists:
                continue

            text_body, html_body, attachments = extract_email_body(msg)
            message_body = text_body if text_body else html_body

            if html_body:
                essential_info = extract_essential_info_from_table(html_body)
                if essential_info:
                    message_body += f"\n\n{essential_info}"

            mail_message = await sync_to_async(MailMessage.objects.create)(
                mail_account=mail_account,
                subject=subject,
                sender=sender,
                sent_date=date,
                body=message_body,
                attachments=[os.path.basename(att) for att in attachments]
            )

            await channel_layer.group_send(
                room_group_name,
                {
                    'type': 'progress_update',
                    'new_email': {
                        'id': mail_message.id,
                        'sender': mail_message.sender,
                        'subject': mail_message.subject,
                        'sent_date': mail_message.sent_date.strftime('%Y-%m-%d %H:%M'),
                        'body': mail_message.body[:50] + '...',
                        'attachments': ', '.join(mail_message.attachments)
                    }
                }
            )


async def fetch_emails(email,   # noqa: C901
                       password,
                       mail_account,
                       channel_layer,
                       room_group_name):
    try:
        mail = connect_to_mail_server(email, password)
    except MailServerConnectionError as e:
        await channel_layer.group_send(
            room_group_name,
            {
                'type': 'progress_update',
                'error': f"Connection failed: {e}",
            }
        )
        return
    except MailAuthenticationError as e:
        await channel_layer.group_send(
            room_group_name,
            {
                'type': 'progress_update',
                'error': f"Authentication failed: {e}",
            }
        )
        return

    try:
        email_ids = fetch_email_ids(mail)
        total_emails = len(email_ids)

        for index, email_id in enumerate(email_ids):
            await process_email(mail, email_id, mail_account,
                                channel_layer, room_group_name)

            progress = int((index + 1) / total_emails * 100)
            await channel_layer.group_send(
                room_group_name,
                {
                    'type': 'progress_update',
                    'progress': progress,
                    'message': f'Processed {index + 1} of {total_emails} emails.'
                }
            )

            await asyncio.sleep(0.1)

    except Exception as e:
        await channel_layer.group_send(
            room_group_name,
            {
                'type': 'progress_update',
                'error': f"Failed to fetch emails: {str(e)}",
            }
        )
    finally:
        mail.logout()
