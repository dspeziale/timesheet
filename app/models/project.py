from app import db
from datetime import datetime

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    daily_rate = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(32), default='Attivo') # Attivo, Chiuso
    notes = db.Column(db.Text)

    # Spese giornaliere rimborsate per ogni giorno di trasferta
    trasferta_transport = db.Column(db.Numeric(10, 2), nullable=False, default=0, server_default='0')
    trasferta_meal = db.Column(db.Numeric(10, 2), nullable=False, default=0, server_default='0')
    trasferta_extra = db.Column(db.Numeric(10, 2), nullable=False, default=0, server_default='0')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    timesheets = db.relationship('TimesheetEntry', backref='project', lazy='dynamic')

    @property
    def trasferta_daily_total(self):
        """Rimborso spese complessivo per una giornata di trasferta."""
        return (float(self.trasferta_transport or 0)
                + float(self.trasferta_meal or 0)
                + float(self.trasferta_extra or 0))

    def __repr__(self):
        return f'<Project {self.code} - {self.name}>'
