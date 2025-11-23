from ui import AppUI
from database import Database
from scanner import Scanner
from telegram_sender import TelegramSender
import os, json

def main():
    cfg_path = os.path.join(os.path.dirname(__file__),'config.json')
    cfg = {}
    if os.path.exists(cfg_path):
        with open(cfg_path,'r') as f:
            cfg = json.load(f)
    db = Database(os.path.join(os.path.dirname(__file__),'data','scanner.db'))
    scanner = Scanner(db, cfg)
    telegram = TelegramSender()
    app = AppUI(scanner, db, telegram)
    app.run()

if __name__ == '__main__':
    main()
