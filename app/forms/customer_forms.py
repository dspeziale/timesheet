from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Optional, Length

class CustomerForm(FlaskForm):
    company_name = StringField('Ragione Sociale', validators=[DataRequired(), Length(max=128)])
    vat_number = StringField('Partita IVA', validators=[Optional(), Length(max=32)])
    tax_code = StringField('Codice Fiscale', validators=[Optional(), Length(max=32)])
    address = StringField('Indirizzo', validators=[Optional(), Length(max=256)])
    city = StringField('Città', validators=[Optional(), Length(max=128)])
    zip_code = StringField('CAP', validators=[Optional(), Length(max=16)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    phone = StringField('Telefono', validators=[Optional(), Length(max=32)])
    active = BooleanField('Attivo', default=True)
    submit = SubmitField('Salva Cliente')
