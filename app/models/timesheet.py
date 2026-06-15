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
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    days_worked = db.Column(db.Numeric(3, 1), nullable=False) # 0.5 or 1.0
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'), nullable=True)
    is_smartworking = db.Column(db.Boolean, default=False)
    is_trasferta = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<TimesheetEntry {self.work_date} - Project {self.project_id}: {self.days_worked} days>'
