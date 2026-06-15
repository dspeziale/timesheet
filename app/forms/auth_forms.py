from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Ricordami')
    submit = SubmitField('Accedi')

class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Nuova Password (lascia vuoto per non cambiare)')
    submit = SubmitField('Salva Profilo')
