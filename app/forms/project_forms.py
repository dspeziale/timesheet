from flask_wtf import FlaskForm
from wtforms import StringField, DateField, DecimalField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Optional, Length

class ProjectForm(FlaskForm):
    code = StringField('Codice Commessa', validators=[DataRequired(), Length(max=32)])
    name = StringField('Nome Progetto', validators=[DataRequired(), Length(max=128)])
    customer_id = SelectField('Cliente', coerce=int, validators=[DataRequired()])
    start_date = DateField('Data Inizio', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('Data Fine', format='%Y-%m-%d', validators=[Optional()])
    daily_rate = DecimalField('Tariffa Giornaliera', places=2, validators=[DataRequired()])
    status = SelectField('Stato', choices=[('Attivo', 'Attivo'), ('Chiuso', 'Chiuso')], default='Attivo')
    notes = TextAreaField('Note', validators=[Optional()])
    submit = SubmitField('Salva Progetto')
