import json

from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

from email_integration.mail.models import MailAccount
from email_integration.mail.utils import fetch_emails


class MailConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'mail_progress'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        account_id = data.get('account_id')

        if account_id:
            try:
                mail_account = await sync_to_async(MailAccount.objects.get)(id=account_id)
                password = mail_account.decrypt_password()

                await fetch_emails(
                    mail_account.email,
                    password,
                    mail_account,
                    self.channel_layer,
                    self.room_group_name
                )
            except MailAccount.DoesNotExist:
                await self.send(text_data=json.dumps({'error': 'Account not found.'}))
            except Exception as e:
                await self.send(text_data=json.dumps({'error': str(e)}))
                await self.close(code=1011)

    async def progress_update(self, event):
        await self.send(text_data=json.dumps({
            'progress': event.get('progress', 0),
            'message': event.get('message', ''),
            'error': event.get('error', ''),
        }))
