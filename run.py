from app import create_app, db
from app.models.user import User
from app.models.customer import Customer
from app.models.project import Project
from app.models.timesheet import TimesheetEntry

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Customer': Customer, 'Project': Project, 'TimesheetEntry': TimesheetEntry}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
