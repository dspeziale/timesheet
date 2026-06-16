import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    SQLALCHEMY_DATABASE_URI = db_url or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    APP_NAME = os.environ.get('APP_NAME') or 'RoxySheet'
    APP_VERSION = os.environ.get('APP_VERSION') or '1.1.5'
    
    # Regime Forfettario Tax Variables
    TAX_COEFF_REDDITIVITA = float(os.environ.get('TAX_COEFF_REDDITIVITA', 0.67))
    TAX_ALIQUOTA_INPS = float(os.environ.get('TAX_ALIQUOTA_INPS', 0.2607))
    TAX_ALIQUOTA_IMPOSTA = float(os.environ.get('TAX_ALIQUOTA_IMPOSTA', 0.15))

    # Notifications Configuration
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 465)
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    MAIL_DEFAULT_RECIPIENT = os.environ.get('MAIL_DEFAULT_RECIPIENT')

