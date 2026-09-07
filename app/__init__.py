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


def _sql_default(column):
    """Rende il server_default di una colonna come letterale SQL.

    Il tipo della colonna decide la forma del letterale: senza quotatura un
    default testuale produce SQL invalido (o viene letto come numero, e
    '0000000' diventerebbe 0), mentre un booleano scritto come 1/0 viene
    rifiutato da PostgreSQL.
    """
    from sqlalchemy import Boolean, Integer, Numeric, Float

    raw = column.server_default.arg
    value = str(getattr(raw, 'text', raw)).strip()

    if isinstance(column.type, Boolean):
        return 'TRUE' if value.lower() in ('1', 'true', 't', 'yes') else 'FALSE'
    if isinstance(column.type, (Integer, Numeric, Float)):
        return value
    if value.startswith("'") and value.endswith("'"):
        return value  # gia' un letterale SQL
    return "'" + value.replace("'", "''") + "'"


def _sync_missing_columns():
    """Aggiunge al database le colonne dichiarate nei modelli ma non ancora
    presenti nelle tabelle esistenti.

    Su Vercel non c'e' modo di lanciare `flask db upgrade` a mano e
    db.create_all() crea soltanto le tabelle mancanti, non le colonne nuove:
    senza questo passaggio un deploy che aggiunge un campo fa fallire ogni
    query su quella tabella. Vengono aggiunte solo colonne nullable oppure
    con un server_default, cosi' l'ALTER e' sempre applicabile.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    existing_tables = set(inspector.get_table_names())

    for table in db.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue  # ci pensa db.create_all()
        present = {c['name'] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in present:
                continue
            if column.server_default is None and not column.nullable:
                # Non si puo' aggiungere una colonna NOT NULL senza default:
                # serve una migration scritta a mano.
                print("Colonna %s.%s non aggiunta automaticamente: NOT NULL senza default."
                      % (table.name, column.name))
                continue

            ddl = 'ALTER TABLE %s ADD COLUMN %s %s' % (
                table.name, column.name, column.type.compile(db.engine.dialect)
            )
            if column.server_default is not None:
                ddl += ' DEFAULT %s' % _sql_default(column)
                if not column.nullable:
                    ddl += ' NOT NULL'

            try:
                db.session.execute(text(ddl))
                db.session.commit()
                print("Colonna aggiunta: %s.%s" % (table.name, column.name))
            except Exception as e:
                db.session.rollback()
                print("Errore aggiungendo %s.%s: %s" % (table.name, column.name, e))


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
            APP_NAME=app.config.get('APP_NAME', 'RoxySheet'),
            APP_VERSION=app.config.get('APP_VERSION', '1.0')
        )

    from app import models

    # Auto-creazione delle tabelle (comodo per Vercel/NeonDB)
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print("Errore nella creazione tabelle:", e)
        try:
            _sync_missing_columns()
        except Exception as e:
            print("Errore nell'allineamento delle colonne:", e)

    return app
