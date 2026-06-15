from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, TextAreaField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Optional, Length

class TimesheetForm(FlaskForm):
    work_date = DateField('Data', format='%Y-%m-%d', validators=[DataRequired()])
    project_id = SelectField('Progetto', coerce=int, validators=[DataRequired()])
    days_worked = SelectField('Giornate', choices=[('0.5', 'Mezza Giornata (0.5)'), ('1.0', 'Giornata Intera (1.0)')], validators=[DataRequired()])
    activity_select = SelectField('Attività Precedenti (Opzionale)', choices=[], validators=[Optional()])
    activity_name = TextAreaField('Attività (Nuova o Modificata)', validators=[DataRequired(), Length(max=2000)])
    is_smartworking = BooleanField('Smartworking', default=False)
    is_trasferta = BooleanField('Trasferta', default=False)
    notes = TextAreaField('Note', validators=[Optional()])
    submit = SubmitField('Salva Timesheet')
