from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, BooleanField, SelectField,
                     SelectMultipleField, IntegerField, SubmitField, widgets)
from wtforms.validators import DataRequired, Optional, Length, NumberRange

from app.models.timesheet import CATEGORIE_ATTIVITA


class ActivityForm(FlaskForm):
    """Una voce del catalogo usato dalla compilazione automatica."""
    name = TextAreaField('Descrizione attività',
                         validators=[DataRequired(), Length(max=2000)])
    categoria = SelectField(
        'Area',
        choices=[('', '— Nessuna (non usata nella compilazione automatica) —')]
                + [(c, c) for c in CATEGORIE_ATTIVITA],
        validators=[Optional()])
    active = BooleanField('Attiva', default=True)
    submit = SubmitField('Salva attività')


class CheckboxListField(SelectMultipleField):
    """Lista di checkbox invece del solito select multiplo."""
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class FillMonthForm(FlaskForm):
    """Compilazione automatica delle giornate di un mese."""
    year = IntegerField('Anno', validators=[DataRequired(),
                                            NumberRange(min=2000, max=2100)])
    month = SelectField('Mese', coerce=int,
                        choices=[(m, '%02d' % m) for m in range(1, 13)],
                        validators=[DataRequired()])
    project_id = SelectField('Progetto', coerce=int, validators=[DataRequired()])
    categorie = CheckboxListField(
        'Aree da usare',
        choices=[(c, c) for c in CATEGORIE_ATTIVITA],
        default=list(CATEGORIE_ATTIVITA))
    is_smartworking = BooleanField('Segna le giornate come Smartworking',
                                   default=False)
    submit = SubmitField('Compila il mese')
