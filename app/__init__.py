from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config

convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = 'Please log in to access this page.'


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    login.init_app(app)

    # Register blueprints
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)
    
    from app.routes.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)
    
    from app.routes.customers import customers_bp
    app.register_blueprint(customers_bp)
    
    from app.routes.projects import projects_bp
    app.register_blueprint(projects_bp)
    
    from app.routes.timesheets import timesheets_bp
    app.register_blueprint(timesheets_bp)

    from app.routes.reports import reports_bp
    app.register_blueprint(reports_bp)

    from app.routes.settings import settings_bp
    app.register_blueprint(settings_bp)

    @app.template_filter('ita_day')
    def ita_day(date):
        giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
        return giorni[date.weekday()]

    @app.template_filter('format_currency')
    def format_currency(value):
        if value is None:
            return "0,00"
        try:
            formatted = "{:,.2f}".format(float(value))
            return formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
        except (ValueError, TypeError):
            return "0,00"

    @app.context_processor
    def inject_global_vars():
        return dict(
            APP_NAME=app.config.get('APP_NAME', 'Timesheet'),
            APP_VERSION=app.config.get('APP_VERSION', '1.0')
        )

    # I modelli vanno importati perche' Alembic li veda in autogenerate
    from app import models

    # Lo schema e' gestito da Alembic: `flask db upgrade` gira all'avvio del
    # container (docker-entrypoint.sh), prima che i worker accettino traffico.
    # Niente db.create_all() qui: creerebbe le tabelle alle spalle di Alembic,
    # facendo fallire le migration su un database vuoto.

    return app
