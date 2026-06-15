from flask import Blueprint, render_template, jsonify
import psutil
from flask_login import login_required
from app.models.customer import Customer
from app.models.project import Project
from app.models.timesheet import TimesheetEntry
from datetime import datetime
import calendar
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
    
    days_worked = sum(float(t.days_worked) for t in timesheets_this_month)
    
    # Calculate working days in current month (Mon-Fri)
    cal = calendar.monthcalendar(now.year, now.month)
    working_days_in_month = sum(1 for week in cal for day in week[:5] if day != 0)

    # Max daily rate from active projects
    active_projects_list = Project.query.filter_by(status='Attivo').all()
    max_rate = max((float(p.daily_rate) for p in active_projects_list), default=0.0)

    # Expected Revenue this month
    expected_revenue = working_days_in_month * max_rate

    # Actual Billable this month
    actual_revenue = sum(float(t.days_worked) * float(t.project.daily_rate) for t in timesheets_this_month)

    return render_template('dashboard/index.html', 
                           title='Dashboard',
                           active_customers=active_customers,
                           active_projects=active_projects,
                           days_worked=days_worked,
                           working_days_in_month=working_days_in_month,
                           expected_revenue=expected_revenue,
                           actual_revenue=actual_revenue)

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

        return jsonify({
            'cpu': {'usage': cpu_usage, 'cores': cpu_cores},
            'memory': {'total_gb': mem_total, 'used_gb': mem_used, 'percent': mem_percent},
            'network': {'sent_mb': net_sent, 'recv_mb': net_recv},
            'temperatures': temps
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
