from flask_wtf import FlaskForm
from wtforms import StringField, DateField, DecimalField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Optional, Length, NumberRange

def _zero_if_empty(value):
    return 0 if value is None else value


class ProjectForm(FlaskForm):
    code = StringField('Codice Commessa', validators=[DataRequired(), Length(max=32)])
    name = StringField('Nome Progetto', validators=[DataRequired(), Length(max=128)])
    customer_id = SelectField('Cliente', coerce=int, validators=[DataRequired()])
    start_date = DateField('Data Inizio', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('Data Fine', format='%Y-%m-%d', validators=[Optional()])
    daily_rate = DecimalField('Tariffa Giornaliera', places=2, validators=[DataRequired()])
    status = SelectField('Stato', choices=[('Attivo', 'Attivo'), ('Chiuso', 'Chiuso')], default='Attivo')
    notes = TextAreaField('Note', validators=[Optional()])

    # Spese giornaliere di trasferta. Il filtro riporta a 0 i campi lasciati
    # vuoti: DataRequired non e' utilizzabile perche' scarterebbe anche lo zero.
    trasferta_transport = DecimalField('Trasporto (al giorno)', places=2,
                                       filters=[_zero_if_empty],
                                       validators=[Optional(), NumberRange(min=0)])
    trasferta_meal = DecimalField('Pranzo / Cena (al giorno)', places=2,
                                  filters=[_zero_if_empty],
                                  validators=[Optional(), NumberRange(min=0)])
    trasferta_extra = DecimalField('Extra diaria (al giorno)', places=2,
                                   filters=[_zero_if_empty],
                                   validators=[Optional(), NumberRange(min=0)])

    submit = SubmitField('Salva Progetto')
