import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

def send_telegram_message(message: str) -> bool:
    """
    Invia un messaggio testuale tramite il bot Telegram configurato.
    """
    bot_token = current_app.config.get('TELEGRAM_BOT_TOKEN')
    chat_id = current_app.config.get('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        current_app.logger.warning("Telegram non configurato. Salto l'invio della notifica.")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        return True
    except Exception as e:
        current_app.logger.error(f"Errore nell'invio del messaggio Telegram: {e}")
        return False


def send_email(subject: str, text_body: str, html_body: str = None, recipient: str = None) -> bool:
    """
    Invia un'email utilizzando il server SMTP configurato (es. Gmail).
    """
    server = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
    port = current_app.config.get('MAIL_PORT', 465)
    username = current_app.config.get('MAIL_USERNAME')
    password = current_app.config.get('MAIL_PASSWORD')
    sender = current_app.config.get('MAIL_DEFAULT_SENDER') or username
    
    # Se non è specificato un destinatario, proviamo ad usare quello di default
    if not recipient:
        recipient = current_app.config.get('MAIL_DEFAULT_RECIPIENT')
        
    if not username or not password or not sender or not recipient:
        current_app.logger.warning("Credenziali o destinatari email non configurati. Salto l'invio.")
        return False
        
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient
    
    msg.attach(MIMEText(text_body, 'plain'))
    if html_body:
        msg.attach(MIMEText(html_body, 'html'))
        
    try:
        if port == 465:
            # Connessione SSL
            with smtplib.SMTP_SSL(server, port, timeout=10) as smtp:
                smtp.login(username, password)
                smtp.send_message(msg)
        else:
            # Connessione TLS (es. porta 587)
            with smtplib.SMTP(server, port, timeout=10) as smtp:
                smtp.starttls()
                smtp.login(username, password)
                smtp.send_message(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Errore nell'invio dell'email: {e}")
        return False
