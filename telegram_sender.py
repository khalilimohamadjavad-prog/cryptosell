import requests, os
class TelegramSender:
    def __init__(self):
        self.bot_token = os.environ.get('TELEGRAM_BOT_TOKEN','')
        self.chat_id = os.environ.get('TELEGRAM_CHAT_ID','')
    def set_credentials(self, bot_token, chat_id):
        self.bot_token = bot_token.strip(); self.chat_id = chat_id.strip()
    def is_configured(self):
        return bool(self.bot_token and self.chat_id)
    def send_message(self, text):
        if not self.is_configured():
            raise RuntimeError('Telegram not configured')
        url = f'https://api.telegram.org/bot{self.bot_token}/sendMessage'
        res = requests.post(url, json={'chat_id': self.chat_id, 'text': text, 'parse_mode':'Markdown'})
        data = res.json()
        if not data.get('ok'):
            raise RuntimeError('Telegram error: '+str(data))
        return data
