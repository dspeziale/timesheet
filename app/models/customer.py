from app import db
from datetime import datetime

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(128), nullable=False)
    vat_number = db.Column(db.String(32))
    tax_code = db.Column(db.String(32))
    address = db.Column(db.String(256))
    city = db.Column(db.String(128))
    zip_code = db.Column(db.String(16))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(32))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    projects = db.relationship('Project', backref='customer', lazy='dynamic')

    def __repr__(self):
        return f'<Customer {self.company_name}>'
