from flask import Blueprint, render_template, request, jsonify, current_app, url_for, flash, redirect
from flask_login import login_required, current_user
from app import db
from app.models.badge import BadgeEvent
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import time

badge_bp = Blueprint('badge', __name__, url_prefix='/badge')

def get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

@badge_bp.route('/')
@login_required
def index():
    """Mostra la pagina del QR Code sul PC"""
    return render_template('badge/qr_display.html', title='Timbratura QR')

@badge_bp.route('/token', methods=['GET'])
@login_required
def get_token():
    """Endpoint chiamato via AJAX dalla pagina PC per avere un nuovo token fresco"""
    s = get_serializer()
    # Il token contiene l'id utente e scade in 60 secondi
    token = s.dumps({'user_id': current_user.id})
    scan_url = url_for('badge.scan', token=token, _external=True)
    return jsonify({'token': token, 'url': scan_url})

@badge_bp.route('/scan/<token>', methods=['GET'])
def scan(token):
    """Pagina mobile che l'utente apre inquadrando il QR Code"""
    s = get_serializer()
    try:
        # Verifica se il token è valido e non scaduto (es. 60 secondi)
        data = s.loads(token, max_age=60)
    except SignatureExpired:
        return render_template('badge/scan_error.html', message='Il QR Code è scaduto. Ricarica la pagina sul PC e riprova.')
    except BadSignature:
        return render_template('badge/scan_error.html', message='QR Code non valido.')

    return render_template('badge/scan_action.html', token=token, title='Timbratura')

@badge_bp.route('/record', methods=['POST'])
def record():
    """Endpoint chiamato dal telefono per registrare l'evento IN o OUT"""
    token = request.form.get('token')
    action = request.form.get('action') # 'IN' o 'OUT'

    if not token or action not in ['IN', 'OUT']:
        return render_template('badge/scan_error.html', message='Dati non validi.')

    s = get_serializer()
    try:
        # Verifica anche qui, per sicurezza, che il token non sia scaduto
        data = s.loads(token, max_age=60)
        user_id = data['user_id']
    except Exception:
        return render_template('badge/scan_error.html', message='Il QR Code è scaduto.')

    # Registra nel database
    event = BadgeEvent(user_id=user_id, event_type=action)
    db.session.add(event)
    db.session.commit()

    return render_template('badge/scan_success.html', action=action, title='Successo')

@badge_bp.route('/history')
@login_required
def history():
    events = BadgeEvent.query.filter_by(user_id=current_user.id).order_by(BadgeEvent.timestamp.desc()).limit(50).all()
    return render_template('badge/history.html', events=events, title='Storico Timbrature')
