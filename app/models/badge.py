from app import db
from datetime import datetime

class BadgeEvent(db.Model):
    __tablename__ = 'badge_events'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    event_type = db.Column(db.String(10), nullable=False) # 'IN' or 'OUT'
    
    # Optional: we can track the exact token used or IP, but it's not strictly necessary.
    # We will just record the event.

    user = db.relationship('User', backref=db.backref('badge_events', lazy='dynamic'))

    def __repr__(self):
        return f'<BadgeEvent {self.user_id} - {self.event_type} at {self.timestamp}>'
