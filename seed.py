from app import create_app, db
from app.models.user import User

app = create_app()

with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', role='Admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully.")
    else:
        print("Admin user already exists.")
