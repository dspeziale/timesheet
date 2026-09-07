from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, TextAreaField, SubmitField, BooleanField, DecimalField
from wtforms.validators import DataRequired, Optional, Length, NumberRange


def coerce_int_or_none(value):
    if value in (None, '', 'None'):
        return None
    return int(value)


def zero_if_empty(value):
    return 0 if value is None else value


class TimesheetForm(FlaskForm):
    work_date = DateField('Data', format='%Y-%m-%d', validators=[DataRequired()])
    project_id = SelectField('Progetto', coerce=coerce_int_or_none, validators=[Optional()], validate_choice=False)
    days_worked = SelectField('Giornate', choices=[('0.5', 'Mezza Giornata (0.5)'), ('1.0', 'Giornata Intera (1.0)')], default='1.0', validators=[DataRequired()])
    activity_select = SelectField('Attività Precedenti (Opzionale)', choices=[], validators=[Optional()])
    activity_name = TextAreaField('Attività (Nuova o Modificata)', validators=[Optional(), Length(max=2000)])
    is_smartworking = BooleanField('Smartworking', default=False)
    is_trasferta = BooleanField('Trasferta', default=False)
    is_ferie = BooleanField('Ferie', default=False)

    # Spese della trasferta: precompilate dalla commessa via JavaScript e
    # confermate (o corrette) dall'utente prima del salvataggio.
    trasferta_transport = DecimalField('Trasporto', places=2, filters=[zero_if_empty],
                                       validators=[Optional(), NumberRange(min=0)])
    trasferta_meal = DecimalField('Pranzo / Cena', places=2, filters=[zero_if_empty],
                                  validators=[Optional(), NumberRange(min=0)])
    trasferta_extra = DecimalField('Extra diaria', places=2, filters=[zero_if_empty],
                                   validators=[Optional(), NumberRange(min=0)])

    notes = TextAreaField('Note', validators=[Optional()])
    submit = SubmitField('Salva Timesheet')
