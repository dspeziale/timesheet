from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_user, logout_user, login_required
from urllib.parse import urlsplit
from app import db
from app.models.user import User
from app.forms.auth_forms import LoginForm, ProfileForm

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Username o password non validi', 'danger')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('dashboard.index')
        return redirect(next_page)
    return render_template('auth/login.html', title='Sign In', form=form)

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/init-admin')
def init_admin():
    user = User.query.filter_by(username='admin').first()
    if user is None:
        user = User(username='admin', role='admin')
        user.set_password('admin123')
        db.session.add(user)
        db.session.commit()
        return "Utente admin creato con successo! Username: admin | Password: admin123"
    return "L'utente admin esiste già."

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        if form.password.data:
            current_user.set_password(form.password.data)
        db.session.commit()
        flash('Profilo aggiornato con successo.', 'success')
        return redirect(url_for('auth.profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
    return render_template('auth/profile.html', title='Profilo Utente', form=form)
