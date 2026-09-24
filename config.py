import os

basedir = os.path.abspath(os.path.dirname(__file__))


def _database_uri():
    """URL del database, obbligatoriamente PostgreSQL.

    Non esiste un ripiego: senza DATABASE_URL l'applicazione non parte. Un
    fallback silenzioso su un file locale sembrerebbe funzionare, ma i dati
    verrebbero scritti dentro il container e andrebbero persi a ogni riavvio,
    facendo sembrare che sia il database a svuotarsi.
    """
    url = (os.environ.get('DATABASE_URL') or '').strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL non e' impostata. Serve l'URL del database "
            "PostgreSQL, per esempio "
            "postgresql://utente:password@host:5432/nomedb"
        )

    # Coolify, Heroku e altri usano ancora lo schema postgres://,
    # che SQLAlchemy 2 non accetta.
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)

    if not url.startswith('postgresql'):
        raise RuntimeError(
            "DATABASE_URL deve puntare a un database PostgreSQL, "
            "ricevuto invece: %s" % url.split('://')[0]
        )
    return url


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'

    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Robustezza connessione DB su ambienti serverless (Vercel + Neon/Postgres):
    # verifica la connessione prima dell'uso e ricicla quelle vecchie, evitando
    # "SSL connection has been closed unexpectedly" su connessioni chiuse per inattivita'.
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
    }
    
    APP_NAME = os.environ.get('APP_NAME') or 'Timesheet'
    APP_VERSION = os.environ.get('APP_VERSION') or '1.2.0'
    
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

