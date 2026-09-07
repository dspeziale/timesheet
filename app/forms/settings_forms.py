from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, BooleanField, DecimalField,
                     IntegerField, SelectField, SubmitField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange, Email


def zero_if_empty(value):
    return 0 if value is None else value


class SettingsForm(FlaskForm):
    # --- Cedente / prestatore ---
    denominazione = StringField('Denominazione / Ragione Sociale', validators=[Optional(), Length(max=128)])
    nome = StringField('Nome', validators=[Optional(), Length(max=64)])
    cognome = StringField('Cognome', validators=[Optional(), Length(max=64)])
    partita_iva = StringField('Partita IVA', validators=[Optional(), Length(max=16)])
    codice_fiscale = StringField('Codice Fiscale', validators=[Optional(), Length(max=16)])
    regime_fiscale = SelectField('Regime Fiscale', choices=[
        ('RF19', 'RF19 - Regime forfettario'),
        ('RF01', 'RF01 - Ordinario'),
        ('RF02', 'RF02 - Contribuenti minimi'),
    ], default='RF19')

    indirizzo = StringField('Indirizzo', validators=[Optional(), Length(max=256)])
    numero_civico = StringField('Numero Civico', validators=[Optional(), Length(max=16)])
    cap = StringField('CAP', validators=[Optional(), Length(max=8)])
    comune = StringField('Comune', validators=[Optional(), Length(max=128)])
    provincia = StringField('Provincia (sigla)', validators=[Optional(), Length(max=4)])
    nazione = StringField('Nazione', validators=[Optional(), Length(max=4)], default='IT')

    telefono = StringField('Telefono', validators=[Optional(), Length(max=32)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    rea_ufficio = StringField('REA - Ufficio (sigla provincia)', validators=[Optional(), Length(max=8)])
    rea_numero = StringField('REA - Numero', validators=[Optional(), Length(max=32)])

    # --- Documento ---
    tipo_documento = SelectField('Tipo Documento', choices=[
        ('TD01', 'TD01 - Fattura'),
        ('TD06', 'TD06 - Parcella'),
    ], default='TD01')
    invoice_prefix = StringField('Prefisso Numerazione', validators=[Optional(), Length(max=16)])
    invoice_next_number = IntegerField('Prossimo Numero Fattura',
                                       validators=[Optional(), NumberRange(min=1)], default=1)
    descrizione_riga = StringField('Descrizione riga prestazione',
                                   validators=[Optional(), Length(max=256)])
    descrizione_spese = StringField('Descrizione riga rimborso spese',
                                    validators=[Optional(), Length(max=256)])

    # --- Regime forfettario ---
    natura_iva = SelectField('Natura IVA', choices=[
        ('N2.2', 'N2.2 - Non soggette, altri casi'),
        ('N2.1', 'N2.1 - Non soggette ex artt. da 7 a 7-septies'),
    ], default='N2.2')
    riferimento_normativo = TextAreaField('Riferimento Normativo',
                                          validators=[Optional(), Length(max=1000)])

    # --- Bollo ---
    bollo_enabled = BooleanField('Applica imposta di bollo', default=True)
    bollo_importo = DecimalField('Importo bollo', places=2, filters=[zero_if_empty],
                                 validators=[Optional(), NumberRange(min=0)])
    bollo_soglia = DecimalField('Soglia oltre la quale si applica', places=2,
                                filters=[zero_if_empty],
                                validators=[Optional(), NumberRange(min=0)])
    bollo_a_carico_cliente = BooleanField('Bollo addebitato al cliente', default=False)

    # --- Rivalsa INPS ---
    rivalsa_inps_percent = DecimalField('Rivalsa INPS (%)', places=2, filters=[zero_if_empty],
                                        validators=[Optional(), NumberRange(min=0, max=100)])

    # --- Pagamento ---
    modalita_pagamento = SelectField('Modalità di Pagamento', choices=[
        ('MP05', 'MP05 - Bonifico'),
        ('MP01', 'MP01 - Contanti'),
        ('MP08', 'MP08 - Carta di pagamento'),
        ('MP12', 'MP12 - RIBA'),
    ], default='MP05')
    condizioni_pagamento = SelectField('Condizioni di Pagamento', choices=[
        ('TP02', 'TP02 - Pagamento completo'),
        ('TP01', 'TP01 - Pagamento a rate'),
        ('TP03', 'TP03 - Anticipo'),
    ], default='TP02')
    iban = StringField('IBAN', validators=[Optional(), Length(max=34)])
    banca = StringField('Istituto Bancario', validators=[Optional(), Length(max=128)])
    giorni_scadenza = IntegerField('Giorni di scadenza pagamento',
                                   validators=[Optional(), NumberRange(min=0, max=365)], default=30)

    submit = SubmitField('Salva Impostazioni')
