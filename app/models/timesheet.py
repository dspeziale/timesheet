from app import db
from datetime import datetime

class Activity(db.Model):
    __tablename__ = 'activities'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False, unique=True)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    timesheets = db.relationship('TimesheetEntry', backref='activity', lazy='dynamic')

    def __repr__(self):
        return f'<Activity {self.name}>'

class TimesheetEntry(db.Model):
    __tablename__ = 'timesheets'
    id = db.Column(db.Integer, primary_key=True)
    work_date = db.Column(db.Date, nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    days_worked = db.Column(db.Numeric(3, 1), nullable=False) # 0.5 or 1.0
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'), nullable=True)
    is_smartworking = db.Column(db.Boolean, default=False)
    is_trasferta = db.Column(db.Boolean, default=False)
    is_ferie = db.Column(db.Boolean, default=False)

    # Spese della giornata di trasferta: proposte dalla commessa al momento
    # dell'inserimento e confermabili/modificabili voce per voce.
    trasferta_transport = db.Column(db.Numeric(10, 2), nullable=False, default=0, server_default='0')
    trasferta_meal = db.Column(db.Numeric(10, 2), nullable=False, default=0, server_default='0')
    trasferta_extra = db.Column(db.Numeric(10, 2), nullable=False, default=0, server_default='0')

    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def trasferta_total(self):
        """Spese della giornata; zero se non e' una trasferta."""
        if not self.is_trasferta:
            return 0.0
        return (float(self.trasferta_transport or 0)
                + float(self.trasferta_meal or 0)
                + float(self.trasferta_extra or 0))

    def __repr__(self):
        return f'<TimesheetEntry {self.work_date} - Project {self.project_id}: {self.days_worked} days>'
