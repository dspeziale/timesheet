from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.models.timesheet import TimesheetEntry, Activity
from app.models.project import Project
from app.forms.timesheet_forms import TimesheetForm
from datetime import datetime, date
import calendar

timesheets_bp = Blueprint('timesheets', __name__, url_prefix='/timesheets')

def _popola_attivita(form):
    """Riempie il menu delle attivita' gia' a catalogo.

    Va chiamata PRIMA di validate_on_submit(): con le choices ancora vuote
    SelectField rifiuta qualunque voce scelta dall'utente e il salvataggio
    fallisce senza mostrare alcun errore.
    """
    attivita = Activity.query.filter_by(active=True).order_by(Activity.name).all()
    form.activity_select.choices = (
        [('', '--- Scegli una precedente ---')]
        + [(a.name, a.name[:50] + ('...' if len(a.name) > 50 else ''))
           for a in attivita]
    )


def _segnala_errori(form):
    """Porta a galla gli errori di validazione del form.

    Senza questo un campo che non passa la validazione ricarica la pagina
    senza spiegazioni: si vede solo che il salvataggio non e' avvenuto.
    """
    for campo, errori in form.errors.items():
        etichetta = getattr(form, campo).label.text
        for errore in errori:
            flash('%s: %s' % (etichetta, errore), 'danger')


def _project_trasferta_rates(projects):
    """Spese di trasferta configurate su ogni commessa, per la proposta nel form."""
    return {
        p.id: {
            'transport': float(p.trasferta_transport or 0),
            'meal': float(p.trasferta_meal or 0),
            'extra': float(p.trasferta_extra or 0),
        }
        for p in projects
    }


@timesheets_bp.route('/')
@login_required
def index():
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    timesheets = TimesheetEntry.query.filter(
        db.extract('year', TimesheetEntry.work_date) == year,
        db.extract('month', TimesheetEntry.work_date) == month
    ).order_by(TimesheetEntry.work_date.desc()).all()
    
    return render_template('timesheets/index.html', title='Timesheet',
                           timesheets=timesheets, year=year, month=month)


@timesheets_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    form = TimesheetForm()
    active_projects = Project.query.filter_by(status='Attivo').all()
    form.project_id.choices = [(p.id, p.name) for p in active_projects]
    trasferta_rates = _project_trasferta_rates(active_projects)
    _popola_attivita(form)

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
            return render_template('timesheets/form.html', title='Nuovo Timesheet', form=form, trasferta_rates=trasferta_rates)

        # Se ferie: azzera tutti gli altri campi. Altrimenti progetto e attività sono obbligatori.
        activity_id = None
        project_id = None
        if not is_ferie:
            if not form.project_id.data:
                flash('Seleziona un progetto oppure spunta Ferie.', 'danger')
                return render_template('timesheets/form.html', title='Nuovo Timesheet', form=form, trasferta_rates=trasferta_rates)
            activity_name_input = (form.activity_name.data or '').strip()
            if not activity_name_input:
                flash("L'attività è obbligatoria per le giornate lavorate.", 'danger')
                return render_template('timesheets/form.html', title='Nuovo Timesheet', form=form, trasferta_rates=trasferta_rates)
            project_id = form.project_id.data
            activity = Activity.query.filter_by(name=activity_name_input).first()
            if not activity:
                activity = Activity(name=activity_name_input)
                db.session.add(activity)
                db.session.flush() # Get the ID before committing
            activity_id = activity.id

        is_trasferta = False if is_ferie else form.is_trasferta.data
        entry = TimesheetEntry(
            work_date=work_date,
            project_id=project_id,
            days_worked=days_value,
            activity_id=activity_id,
            is_smartworking=False if is_ferie else form.is_smartworking.data,
            is_trasferta=is_trasferta,
            is_ferie=is_ferie,
            # Le spese si conservano solo sulle giornate di trasferta
            trasferta_transport=form.trasferta_transport.data if is_trasferta else 0,
            trasferta_meal=form.trasferta_meal.data if is_trasferta else 0,
            trasferta_extra=form.trasferta_extra.data if is_trasferta else 0,
            notes=form.notes.data
        )
        db.session.add(entry)
        db.session.commit()
        flash('Timesheet registrato con successo!', 'success')
        return redirect(url_for('timesheets.index'))

    if request.method == 'POST':
        _segnala_errori(form)

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


    return render_template('timesheets/form.html', title='Nuovo Timesheet', form=form, trasferta_rates=trasferta_rates)


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
    active_projects = Project.query.filter_by(status='Attivo').all()
    form.project_id.choices = [(p.id, p.name) for p in active_projects]
    trasferta_rates = _project_trasferta_rates(active_projects)
    _popola_attivita(form)

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
            return render_template('timesheets/form.html', title='Modifica Timesheet', form=form, trasferta_rates=trasferta_rates)

        # Se ferie: azzera tutti gli altri campi. Altrimenti progetto e attività sono obbligatori.
        activity_id = None
        project_id = None
        if not is_ferie:
            if not form.project_id.data:
                flash('Seleziona un progetto oppure spunta Ferie.', 'danger')
                return render_template('timesheets/form.html', title='Modifica Timesheet', form=form, trasferta_rates=trasferta_rates)
            activity_name_input = (form.activity_name.data or '').strip()
            if not activity_name_input:
                flash("L'attività è obbligatoria per le giornate lavorate.", 'danger')
                return render_template('timesheets/form.html', title='Modifica Timesheet', form=form, trasferta_rates=trasferta_rates)
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
        # Le spese si conservano solo sulle giornate di trasferta
        entry.trasferta_transport = form.trasferta_transport.data if entry.is_trasferta else 0
        entry.trasferta_meal = form.trasferta_meal.data if entry.is_trasferta else 0
        entry.trasferta_extra = form.trasferta_extra.data if entry.is_trasferta else 0
        entry.notes = form.notes.data

        db.session.commit()
        flash('Timesheet aggiornato con successo!', 'success')
        return redirect(url_for('timesheets.index'))

    elif request.method == 'POST':
        _segnala_errori(form)

    if request.method == 'GET':
        form.work_date.data = entry.work_date
        form.project_id.data = entry.project_id
        form.days_worked.data = str(entry.days_worked)
        form.activity_name.data = entry.activity.name if entry.activity else ''
        form.is_smartworking.data = entry.is_smartworking
        form.is_trasferta.data = entry.is_trasferta
        form.is_ferie.data = entry.is_ferie
        form.trasferta_transport.data = entry.trasferta_transport
        form.trasferta_meal.data = entry.trasferta_meal
        form.trasferta_extra.data = entry.trasferta_extra
        form.notes.data = entry.notes

        
    return render_template('timesheets/form.html', title='Modifica Timesheet', form=form, trasferta_rates=trasferta_rates)

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
