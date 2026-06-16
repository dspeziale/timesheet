from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.models.timesheet import TimesheetEntry, Activity
from app.models.project import Project
from app.forms.timesheet_forms import TimesheetForm
from datetime import datetime

timesheets_bp = Blueprint('timesheets', __name__, url_prefix='/timesheets')

@timesheets_bp.route('/')
@login_required
def index():
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    timesheets = TimesheetEntry.query.filter(
        db.extract('year', TimesheetEntry.work_date) == year,
        db.extract('month', TimesheetEntry.work_date) == month
    ).order_by(TimesheetEntry.work_date.desc()).all()
    
    return render_template('timesheets/index.html', title='Timesheet', timesheets=timesheets, year=year, month=month)

@timesheets_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    form = TimesheetForm()
    form.project_id.choices = [(p.id, p.name) for p in Project.query.filter_by(status='Attivo').all()]
    if form.validate_on_submit():
        # Check max 1.0 day per date
        work_date = form.work_date.data
        days_to_add = float(form.days_worked.data)
        
        existing_entries = TimesheetEntry.query.filter_by(work_date=work_date).all()
        current_total = sum(float(e.days_worked) for e in existing_entries)
        
        if current_total + days_to_add > 1.0:
            flash(f'Errore: per il {work_date.strftime("%d/%m/%Y")} risultano già {current_total} giornate registrate. Non è possibile superare 1.0.', 'danger')
            return render_template('timesheets/form.html', title='Nuovo Timesheet', form=form)

        activity_name_input = form.activity_name.data.strip()
        activity = Activity.query.filter_by(name=activity_name_input).first()
        if not activity:
            activity = Activity(name=activity_name_input)
            db.session.add(activity)
            db.session.flush() # Get the ID before committing

        entry = TimesheetEntry(
            work_date=work_date,
            project_id=form.project_id.data,
            days_worked=form.days_worked.data,
            activity_id=activity.id,
            is_smartworking=form.is_smartworking.data,
            is_trasferta=form.is_trasferta.data,
            notes=form.notes.data
        )
        db.session.add(entry)
        db.session.commit()
        flash('Timesheet registrato con successo!', 'success')
        return redirect(url_for('timesheets.index'))
    
    if request.method == 'GET':
        form.work_date.data = datetime.today().date()
        
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
        days_to_add = float(form.days_worked.data)
        
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

        activity_name_input = form.activity_name.data.strip()
        activity = Activity.query.filter_by(name=activity_name_input).first()
        if not activity:
            activity = Activity(name=activity_name_input)
            db.session.add(activity)
            db.session.flush()

        entry.work_date = work_date
        entry.project_id = form.project_id.data
        entry.days_worked = form.days_worked.data
        entry.activity_id = activity.id
        entry.is_smartworking = form.is_smartworking.data
        entry.is_trasferta = form.is_trasferta.data
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
        form.notes.data = entry.notes

    activities = Activity.query.filter_by(active=True).order_by(Activity.name).all()
    form.activity_select.choices = [('', '--- Scegli una precedente ---')] + [(a.name, a.name[:50] + ('...' if len(a.name)>50 else '')) for a in activities]
        
    return render_template('timesheets/form.html', title='Modifica Timesheet', form=form)
