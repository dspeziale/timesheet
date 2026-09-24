from flask import Blueprint, render_template, jsonify
import psutil
from flask_login import login_required
from app.models.customer import Customer
from app.models.project import Project
from app.models.timesheet import TimesheetEntry
from datetime import datetime
import calendar
from sqlalchemy import text, inspect
from sqlalchemy.engine.url import make_url
from app import db

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    now = datetime.now()
    # Number of active customers
    active_customers = Customer.query.filter_by(active=True).count()
    # Number of active projects
    active_projects = Project.query.filter_by(status='Attivo').count()

    # Days worked this month
    timesheets_this_month = TimesheetEntry.query.filter(
        db.extract('year', TimesheetEntry.work_date) == now.year,
        db.extract('month', TimesheetEntry.work_date) == now.month
    ).all()
    
    days_worked = sum(float(t.days_worked) for t in timesheets_this_month if not t.is_ferie)
    
    # Calculate working days in current month (Mon-Fri)
    cal = calendar.monthcalendar(now.year, now.month)
    working_days_in_month = sum(1 for week in cal for day in week[:5] if day != 0)

    # Max daily rate from active projects
    active_projects_list = Project.query.filter_by(status='Attivo').all()
    max_rate = max((float(p.daily_rate) for p in active_projects_list), default=0.0)

    # Expected Revenue this month
    expected_revenue = working_days_in_month * max_rate

    # Actual Billable this month
    actual_revenue = sum(float(t.days_worked) * float(t.project.daily_rate) for t in timesheets_this_month if not t.is_ferie and t.project)

    return render_template('dashboard/index.html', 
                           title='Dashboard',
                           active_customers=active_customers,
                           active_projects=active_projects,
                           days_worked=days_worked,
                           working_days_in_month=working_days_in_month,
                           expected_revenue=expected_revenue,
                           actual_revenue=actual_revenue)

@dashboard_bp.route('/healthz')
def healthz():
    """Sonda per l'healthcheck del container: non richiede login e verifica
    che il database risponda, cosi' un deploy con DB irraggiungibile non viene
    dichiarato sano."""
    try:
        db.session.execute(text('SELECT 1'))
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'detail': str(e)}), 503


def _database_info():
    """Stato e contenuto del database, per la finestra Info di Sistema.

    La password non viene mai esposta: dalla stringa di connessione si
    prendono solo host, porta, nome e utente. Ogni interrogazione e' isolata,
    cosi' un permesso mancante non fa fallire l'intero blocco.
    """
    info = {}

    url = make_url(db.engine.url)
    info['motore'] = url.get_backend_name()
    info['host'] = url.host
    info['porta'] = url.port or 5432
    info['nome'] = url.database
    info['utente'] = url.username

    def _scalare(sql, default=None):
        try:
            return db.session.execute(text(sql)).scalar()
        except Exception:
            db.session.rollback()
            return default

    versione = _scalare('SELECT version()')
    if versione:
        # "PostgreSQL 16.4 (Debian ...) on x86_64..." -> "PostgreSQL 16.4"
        info['versione'] = ' '.join(str(versione).split()[:2])
    info['dimensione'] = _scalare(
        'SELECT pg_size_pretty(pg_database_size(current_database()))')
    info['connessioni'] = _scalare(
        'SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()')
    info['schema'] = _scalare('SELECT version_num FROM alembic_version')

    # Conteggio esatto per tabella: i dati sono pochi e n_live_tup sarebbe
    # una stima, a zero finche' non passa autovacuum.
    tabelle = []
    try:
        esistenti = set(inspect(db.engine).get_table_names())
        for tabella in db.metadata.sorted_tables:
            if tabella.name not in esistenti:
                continue
            righe = _scalare('SELECT count(*) FROM "%s"' % tabella.name)
            tabelle.append({'nome': tabella.name, 'righe': righe})
    except Exception:
        db.session.rollback()
    info['tabelle'] = tabelle
    info['righe_totali'] = sum(t['righe'] or 0 for t in tabelle)

    pool = db.engine.pool
    try:
        info['pool'] = {'in_uso': pool.checkedout(), 'disponibili': pool.checkedin()}
    except Exception:
        info['pool'] = None

    return info


@dashboard_bp.route('/sysinfo')
@login_required
def sysinfo():
    try:
        cpu_usage = psutil.cpu_percent(interval=0.1)
        cpu_cores = psutil.cpu_count(logical=True)
        memory = psutil.virtual_memory()
        mem_total = round(memory.total / (1024**3), 2)
        mem_used = round(memory.used / (1024**3), 2)
        mem_percent = memory.percent
        
        # Network
        net_io = psutil.net_io_counters()
        net_sent = round(net_io.bytes_sent / (1024**2), 2) # MB
        net_recv = round(net_io.bytes_recv / (1024**2), 2) # MB
        
        # Temperatures (might not be available on all systems, especially Windows without admin rights)
        temps = {}
        try:
            if hasattr(psutil, "sensors_temperatures"):
                st = psutil.sensors_temperatures()
                for name, entries in st.items():
                    temps[name] = [entry.current for entry in entries]
        except Exception:
            pass

        try:
            database = _database_info()
        except Exception as e:
            database = {'errore': str(e)}

        return jsonify({
            'cpu': {'usage': cpu_usage, 'cores': cpu_cores},
            'memory': {'total_gb': mem_total, 'used_gb': mem_used, 'percent': mem_percent},
            'network': {'sent_mb': net_sent, 'recv_mb': net_recv},
            'temperatures': temps,
            'database': database
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
