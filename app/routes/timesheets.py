from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.models.timesheet import TimesheetEntry, Activity
from app.models.project import Project
from app.forms.timesheet_forms import TimesheetForm
from datetime import datetime, date
import calendar

timesheets_bp = Blueprint('timesheets', __name__, url_prefix='/timesheets')

# Descrizioni usate dalla compilazione automatica del mese: si alternano in
# sequenza cosi' che i giorni consecutivi non riportino la stessa attività.
IT_ACTIVITIES = [
    'Sviluppo e manutenzione evolutiva dei moduli applicativi',
    'Analisi funzionale e stesura della documentazione tecnica',
    'Correzione anomalie e attività di bug fixing',
    'Refactoring del codice e ottimizzazione delle performance',
    'Sviluppo di API REST e integrazione con servizi esterni',
    'Esecuzione di test unitari e di integrazione',
    'Ottimizzazione delle query e manutenzione della base dati',
    'Code review e supporto tecnico al team di sviluppo',
    'Deploy in ambiente di collaudo e verifica del rilascio',
    'Riunione di allineamento e pianificazione delle attività',
    'Manutenzione correttiva e monitoraggio dei sistemi',
    'Configurazione della pipeline CI/CD e automazione dei rilasci',
    'Analisi dei requisiti con il cliente e stima delle attività',
    'Supporto specialistico e troubleshooting in produzione',
    'Aggiornamento delle librerie e gestione delle dipendenze',
]

@timesheets_bp.route('/')
@login_required
def index():
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    timesheets = TimesheetEntry.query.filter(
        db.extract('year', TimesheetEntry.work_date) == year,
        db.extract('month', TimesheetEntry.work_date) == month
    ).order_by(TimesheetEntry.work_date.desc()).all()
    
    projects = Project.query.filter_by(status='Attivo').all()

    return render_template('timesheets/index.html', title='Timesheet', timesheets=timesheets, year=year, month=month, projects=projects)


@timesheets_bp.route('/fill_month', methods=['POST'])
@login_required
def fill_month():
    """Compila in un colpo solo tutti i giorni feriali (Lun-Ven) del mese
    visualizzato, assegnando al progetto scelto una descrizione di attivita'
    informatica diversa per ogni giornata. I giorni gia' registrati non vengono
    toccati: si riempie solo la quota residua fino a 1.0."""
    year = request.form.get('year', datetime.now().year, type=int)
    month = request.form.get('month', datetime.now().month, type=int)
    project_id = request.form.get('project_id', type=int)

    project = db.session.get(Project, project_id) if project_id else None
    if project is None:
        flash('Seleziona un progetto valido per compilare il mese.', 'danger')
        return redirect(url_for('timesheets.index', year=year, month=month))

    # Giornate gia' presenti nel mese, per non superare il limite di 1.0 al giorno
    booked = {}
    existing = TimesheetEntry.query.filter(
        db.extract('year', TimesheetEntry.work_date) == year,
        db.extract('month', TimesheetEntry.work_date) == month
    ).all()
    for e in existing:
        booked[e.work_date] = booked.get(e.work_date, 0.0) + float(e.days_worked)

    # Riusa le attivita' gia' a catalogo invece di duplicarle
    activities = {a.name: a for a in Activity.query.all()}

    created = 0
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        work_date = date(year, month, day)
        if work_date.weekday() >= 5:
            continue

        remaining = 1.0 - booked.get(work_date, 0.0)
        if remaining <= 0:
            continue
        days_value = '1.0' if remaining >= 1.0 else '0.5'

        name = IT_ACTIVITIES[created % len(IT_ACTIVITIES)]
        activity = activities.get(name)
        if not activity:
            activity = Activity(name=name)
            db.session.add(activity)
            db.session.flush()  # serve l'id prima del commit
            activities[name] = activity

        db.session.add(TimesheetEntry(
            work_date=work_date,
            project_id=project.id,
            days_worked=days_value,
            activity_id=activity.id
        ))
        created += 1

    if created:
        db.session.commit()
        flash(f'Compilate {created} giornate su {project.name} per {month:02d}/{year}.', 'success')
    else:
        flash(f'Nessuna giornata da compilare: il mese {month:02d}/{year} risulta già completo.', 'info')

    return redirect(url_for('timesheets.index', year=year, month=month))

@timesheets_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    form = TimesheetForm()
    form.project_id.choices = [(p.id, p.name) for p in Project.query.filter_by(status='Attivo').all()]
    if form.validate_on_submit():
        # Check max 1.0 day per date
        work_date = form.work_date.data
        is_ferie = form.is_ferie.data
        days_value = '1.0' if is_ferie else form.days_worked.data  # le ferie sono sempre 1 giornata
        days_to_add = float(days_value)

        existing_entries = TimesheetEntry.query.filter_by(work_date=work_date).all()
        current_total = sum(float(e.days_worked) for e in existing_entries)

        if current_total + days_to_add > 1.0:
            flash(f'Errore: per il {work_date.strftime("%d/%m/%Y")} risultano già {current_total} giornate registrate. Non è possibile superare 1.0.', 'danger')
            return render_template('timesheets/form.html', title='Nuovo Timesheet', form=form)

        # Se ferie: azzera tutti gli altri campi. Altrimenti progetto e attività sono obbligatori.
        activity_id = None
        project_id = None
        if not is_ferie:
            if not form.project_id.data:
                flash('Seleziona un progetto oppure spunta Ferie.', 'danger')
                return render_template('timesheets/form.html', title='Nuovo Timesheet', form=form)
            activity_name_input = (form.activity_name.data or '').strip()
            if not activity_name_input:
                flash("L'attività è obbligatoria per le giornate lavorate.", 'danger')
                return render_template('timesheets/form.html', title='Nuovo Timesheet', form=form)
            project_id = form.project_id.data
            activity = Activity.query.filter_by(name=activity_name_input).first()
            if not activity:
                activity = Activity(name=activity_name_input)
                db.session.add(activity)
                db.session.flush() # Get the ID before committing
            activity_id = activity.id

        entry = TimesheetEntry(
            work_date=work_date,
            project_id=project_id,
            days_worked=days_value,
            activity_id=activity_id,
            is_smartworking=False if is_ferie else form.is_smartworking.data,
            is_trasferta=False if is_ferie else form.is_trasferta.data,
            is_ferie=is_ferie,
            notes=form.notes.data
        )
        db.session.add(entry)
        db.session.commit()
        flash('Timesheet registrato con successo!', 'success')
        return redirect(url_for('timesheets.index'))

    if request.method == 'GET':
        # Data preselezionata (es. clic su un giorno del calendario), fallback a oggi
        date_arg = request.args.get('date')
        preset = None
        if date_arg:
            try:
                preset = datetime.strptime(date_arg, '%Y-%m-%d').date()
            except ValueError:
                preset = None
        form.work_date.data = preset or datetime.today().date()

    activities = Activity.query.filter_by(active=True).order_by(Activity.name).all()
    form.activity_select.choices = [('', '--- Scegli una precedente ---')] + [(a.name, a.name[:50] + ('...' if len(a.name)>50 else '')) for a in activities]

    return render_template('timesheets/form.html', title='Nuovo Timesheet', form=form)

@timesheets_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    entry = TimesheetEntry.query.get_or_404(id)
    db.session.delete(entry)
    db.session.commit()
    flash('Timesheet eliminato.', 'success')
    return redirect(url_for('timesheets.index'))

@timesheets_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    entry = TimesheetEntry.query.get_or_404(id)
    form = TimesheetForm()
    form.project_id.choices = [(p.id, p.name) for p in Project.query.filter_by(status='Attivo').all()]
    
    if form.validate_on_submit():
        work_date = form.work_date.data
        is_ferie = form.is_ferie.data
        days_value = '1.0' if is_ferie else form.days_worked.data  # le ferie sono sempre 1 giornata
        days_to_add = float(days_value)

        # Check max 1.0 day per date excluding current entry
        existing_entries = TimesheetEntry.query.filter(
            TimesheetEntry.work_date == work_date,
            TimesheetEntry.id != id
        ).all()
        current_total = sum(float(e.days_worked) for e in existing_entries)

        if current_total + days_to_add > 1.0:
            flash(f'Errore: per il {work_date.strftime("%d/%m/%Y")} risultano già {current_total} giornate registrate da altre voci. Non è possibile superare 1.0.', 'danger')
            activities = Activity.query.filter_by(active=True).order_by(Activity.name).all()
            activity_names = [a.name for a in activities]
            return render_template('timesheets/form.html', title='Modifica Timesheet', form=form, activity_names=activity_names)

        # Se ferie: azzera tutti gli altri campi. Altrimenti progetto e attività sono obbligatori.
        activity_id = None
        project_id = None
        if not is_ferie:
            if not form.project_id.data:
                flash('Seleziona un progetto oppure spunta Ferie.', 'danger')
                return render_template('timesheets/form.html', title='Modifica Timesheet', form=form)
            activity_name_input = (form.activity_name.data or '').strip()
            if not activity_name_input:
                flash("L'attività è obbligatoria per le giornate lavorate.", 'danger')
                return render_template('timesheets/form.html', title='Modifica Timesheet', form=form)
            project_id = form.project_id.data
            activity = Activity.query.filter_by(name=activity_name_input).first()
            if not activity:
                activity = Activity(name=activity_name_input)
                db.session.add(activity)
                db.session.flush()
            activity_id = activity.id

        entry.work_date = work_date
        entry.project_id = project_id
        entry.days_worked = days_value
        entry.activity_id = activity_id
        entry.is_smartworking = False if is_ferie else form.is_smartworking.data
        entry.is_trasferta = False if is_ferie else form.is_trasferta.data
        entry.is_ferie = is_ferie
        entry.notes = form.notes.data

        db.session.commit()
        flash('Timesheet aggiornato con successo!', 'success')
        return redirect(url_for('timesheets.index'))

    elif request.method == 'GET':
        form.work_date.data = entry.work_date
        form.project_id.data = entry.project_id
        form.days_worked.data = str(entry.days_worked)
        form.activity_name.data = entry.activity.name if entry.activity else ''
        form.is_smartworking.data = entry.is_smartworking
        form.is_trasferta.data = entry.is_trasferta
        form.is_ferie.data = entry.is_ferie
        form.notes.data = entry.notes

    activities = Activity.query.filter_by(active=True).order_by(Activity.name).all()
    form.activity_select.choices = [('', '--- Scegli una precedente ---')] + [(a.name, a.name[:50] + ('...' if len(a.name)>50 else '')) for a in activities]
        
    return render_template('timesheets/form.html', title='Modifica Timesheet', form=form)

@timesheets_bp.route('/calendar', methods=['GET'])
@login_required
def calendar_view():
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    # Get a matrix representing the calendar month
    # Each row is a week, each cell is a day number (0 means outside month)
    # calendar.setfirstweekday(calendar.MONDAY) is the default
    cal_matrix = calendar.monthcalendar(year, month)

    # Fetch entries for this month
    timesheets = TimesheetEntry.query.filter(
        db.extract('year', TimesheetEntry.work_date) == year,
        db.extract('month', TimesheetEntry.work_date) == month
    ).order_by(TimesheetEntry.work_date).all()

    # Group entries by day
    entries_by_day = {}
    for t in timesheets:
        day = t.work_date.day
        if day not in entries_by_day:
            entries_by_day[day] = []
        entries_by_day[day].append(t)

    return render_template('timesheets/calendar.html', 
                           title='Calendario Mensile', 
                           year=year, 
                           month=month, 
                           cal_matrix=cal_matrix, 
                           entries_by_day=entries_by_day)
