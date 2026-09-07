from app import db


class Settings(db.Model):
    """Dati dell'azienda e preferenze di fatturazione.

    Tabella a riga singola (id=1): l'app e' monoutente, quindi non serve
    associare le impostazioni a un utente.
    """
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)

    # --- Cedente / prestatore (chi emette la fattura) ---
    denominazione = db.Column(db.String(128), default='', server_default='')
    nome = db.Column(db.String(64), default='', server_default='')
    cognome = db.Column(db.String(64), default='', server_default='')
    partita_iva = db.Column(db.String(16), default='', server_default='')
    codice_fiscale = db.Column(db.String(16), default='', server_default='')
    regime_fiscale = db.Column(db.String(8), default='RF19', server_default='RF19')

    indirizzo = db.Column(db.String(256), default='', server_default='')
    numero_civico = db.Column(db.String(16), default='', server_default='')
    cap = db.Column(db.String(8), default='', server_default='')
    comune = db.Column(db.String(128), default='', server_default='')
    provincia = db.Column(db.String(4), default='', server_default='')
    nazione = db.Column(db.String(4), default='IT', server_default='IT')

    telefono = db.Column(db.String(32), default='', server_default='')
    email = db.Column(db.String(120), default='', server_default='')
    rea_ufficio = db.Column(db.String(8), default='', server_default='')
    rea_numero = db.Column(db.String(32), default='', server_default='')

    # --- Impostazioni del documento ---
    tipo_documento = db.Column(db.String(8), default='TD01', server_default='TD01')
    invoice_prefix = db.Column(db.String(16), default='', server_default='')
    invoice_next_number = db.Column(db.Integer, default=1, server_default='1')
    descrizione_riga = db.Column(
        db.String(256),
        default='Prestazione di servizi di consulenza informatica',
        server_default='Prestazione di servizi di consulenza informatica')
    descrizione_spese = db.Column(
        db.String(256),
        default='Rimborso spese di trasferta',
        server_default='Rimborso spese di trasferta')

    # --- Regime forfettario: natura IVA e riferimento normativo ---
    natura_iva = db.Column(db.String(8), default='N2.2', server_default='N2.2')
    riferimento_normativo = db.Column(
        db.Text,
        default=("Operazione senza applicazione dell'IVA ai sensi dell'articolo 1, "
                 "commi da 54 a 89, della Legge n. 190/2014 e successive "
                 "modificazioni/integrazioni - Regime forfettario"))

    # --- Imposta di bollo (dovuta sulle fatture esenti oltre la soglia) ---
    bollo_enabled = db.Column(db.Boolean, default=True, server_default='1')
    bollo_importo = db.Column(db.Numeric(10, 2), default=2.00, server_default='2.00')
    bollo_soglia = db.Column(db.Numeric(10, 2), default=77.47, server_default='77.47')
    bollo_a_carico_cliente = db.Column(db.Boolean, default=False, server_default='0')

    # --- Rivalsa INPS (facoltativa, 0 = non addebitata) ---
    rivalsa_inps_percent = db.Column(db.Numeric(5, 2), default=0, server_default='0')

    # --- Pagamento ---
    modalita_pagamento = db.Column(db.String(8), default='MP05', server_default='MP05')
    condizioni_pagamento = db.Column(db.String(8), default='TP02', server_default='TP02')
    iban = db.Column(db.String(34), default='', server_default='')
    banca = db.Column(db.String(128), default='', server_default='')
    giorni_scadenza = db.Column(db.Integer, default=30, server_default='30')

    @classmethod
    def get(cls):
        """Restituisce l'unica riga di impostazioni, creandola se manca."""
        settings = db.session.get(cls, 1)
        if settings is None:
            settings = cls(id=1)
            db.session.add(settings)
            db.session.commit()
        return settings

    @property
    def intestazione(self):
        """Denominazione se presente, altrimenti nome e cognome."""
        if self.denominazione:
            return self.denominazione
        return ' '.join(p for p in (self.nome, self.cognome) if p)

    @property
    def indirizzo_completo(self):
        via = ' '.join(p for p in (self.indirizzo, self.numero_civico) if p)
        citta = ' '.join(p for p in (self.cap, self.comune) if p)
        if self.provincia:
            citta += ' (%s)' % self.provincia
        return ', '.join(p for p in (via, citta) if p)

    def __repr__(self):
        return f'<Settings {self.intestazione or "(vuote)"}>'
