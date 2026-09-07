from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.models.settings import Settings
from app.forms.settings_forms import SettingsForm

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    settings = Settings.get()
    form = SettingsForm(obj=settings)

    if form.validate_on_submit():
        # populate_obj scriverebbe anche il campo submit: si assegnano solo
        # i campi che esistono davvero sul modello.
        for name, field in form._fields.items():
            if name in ('submit', 'csrf_token'):
                continue
            if hasattr(settings, name):
                setattr(settings, name, field.data)
        db.session.commit()
        flash('Impostazioni salvate con successo.', 'success')
        return redirect(url_for('settings.index'))

    return render_template('settings/index.html', title='Impostazioni',
                           form=form, settings=settings)
