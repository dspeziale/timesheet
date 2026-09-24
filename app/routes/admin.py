from datetime import date, datetime
import calendar

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required

from app import db
from app.models.project import Project
from app.models.timesheet import TimesheetEntry, Activity, CATEGORIE_ATTIVITA
from app.forms.admin_forms import ActivityForm, FillMonthForm

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ---------------------------------------------------------------- Catalogo

@admin_bp.route('/activities')
@login_required
def activities():
    """Catalogo delle attività, raggruppato per area."""
    tutte = Activity.query.order_by(Activity.categoria, Activity.name).all()

    gruppi = [(c, [a for a in tutte if (a.categoria or '') == c])
              for c in CATEGORIE_ATTIVITA]
    senza_categoria = [a for a in tutte
                       if (a.categoria or '') not in CATEGORIE_ATTIVITA]

    return render_template('admin/activities.html', title='Attività',
                           gruppi=gruppi, senza_categoria=senza_categoria,
                           totale=len(tutte))


@admin_bp.route('/activities/add', methods=['GET', 'POST'])
@login_required
def activity_add():
    form = ActivityForm()
    if form.validate_on_submit():
        descrizione = (form.name.data or '').strip()
        if Activity.query.filter_by(name=descrizione).first():
            flash('Esiste già un\'attività con questa descrizione.', 'danger')
            return render_template('admin/activity_form.html',
                                   title='Nuova attività', form=form)
        db.session.add(Activity(name=descrizione,
                                categoria=form.categoria.data or '',
                                active=form.active.data))
        db.session.commit()
        flash('Attività aggiunta.', 'success')
        return redirect(url_for('admin.activities'))
    return render_template('admin/activity_form.html',
                           title='Nuova attività', form=form)


@admin_bp.route('/activities/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def activity_edit(id):
    attivita = Activity.query.get_or_404(id)
    form = ActivityForm(obj=attivita)
    if form.validate_on_submit():
        descrizione = (form.name.data or '').strip()
        duplicata = Activity.query.filter(Activity.name == descrizione,
                                          Activity.id != id).first()
        if duplicata:
            flash('Esiste già un\'altra attività con questa descrizione.', 'danger')
            return render_template('admin/activity_form.html',
                                   title='Modifica attività', form=form,
                                   attivita=attivita)
        attivita.name = descrizione
        attivita.categoria = form.categoria.data or ''
        attivita.active = form.active.data
        db.session.commit()
        flash('Attività aggiornata.', 'success')
        return redirect(url_for('admin.activities'))
    return render_template('admin/activity_form.html',
                           title='Modifica attività', form=form,
                           attivita=attivita)


@admin_bp.route('/activities/toggle/<int:id>', methods=['POST'])
@login_required
def activity_toggle(id):
    attivita = Activity.query.get_or_404(id)
    attivita.active = not attivita.active
    db.session.commit()
    flash('Attività %s.' % ('riattivata' if attivita.active else 'disattivata'),
          'success')
    return redirect(url_for('admin.activities'))


@admin_bp.route('/activities/delete/<int:id>', methods=['POST'])
@login_required
def activity_delete(id):
    attivita = Activity.query.get_or_404(id)
    usata = attivita.timesheets.count()
    if usata:
        # Cancellarla lascerebbe le giornate senza descrizione: si disattiva.
        attivita.active = False
        db.session.commit()
        flash('L\'attività è usata da %d giornate, quindi è stata disattivata '
              'invece che eliminata.' % usata, 'warning')
    else:
        db.session.delete(attivita)
        db.session.commit()
        flash('Attività eliminata.', 'success')
    return redirect(url_for('admin.activities'))


# -------------------------------------------------------- Compilazione mese

@admin_bp.route('/fill-month', methods=['GET', 'POST'])
@login_required
def fill_month():
    """Registra una giornata su ogni giorno feriale del mese, distribuendo a
    rotazione le attività del catalogo nelle aree selezionate.

    I giorni già registrati non vengono toccati: si riempie solo la quota
    residua fino a 1.0, così il vincolo di una giornata al giorno regge.
    """
    form = FillMonthForm()
    progetti = Project.query.filter_by(status='Attivo').order_by(Project.name).all()
    form.project_id.choices = [(p.id, '%s - %s' % (p.code, p.name)) for p in progetti]

    if request.method == 'GET':
        form.year.data = request.args.get('year', datetime.now().year, type=int)
        form.month.data = request.args.get('month', datetime.now().month, type=int)

    # Quante attività sono disponibili per ogni area, per mostrarlo nel form
    disponibili = {
        c: Activity.query.filter_by(categoria=c, active=True).count()
        for c in CATEGORIE_ATTIVITA
    }

    if form.validate_on_submit():
        year, month = form.year.data, form.month.data
        categorie = form.categorie.data or []

        if not categorie:
            flash('Seleziona almeno un\'area di attività.', 'danger')
            return render_template('admin/fill_month.html', title='Compila Mese',
                                   form=form, disponibili=disponibili)

        catalogo = (Activity.query
                    .filter(Activity.active.is_(True),
                            Activity.categoria.in_(categorie))
                    .order_by(Activity.categoria, Activity.name)
                    .all())
        if not catalogo:
            flash('Nessuna attività attiva nelle aree selezionate: aggiungile '
                  'dal catalogo.', 'danger')
            return render_template('admin/fill_month.html', title='Compila Mese',
                                   form=form, disponibili=disponibili)

        progetto = db.session.get(Project, form.project_id.data)
        if progetto is None:
            flash('Progetto non valido.', 'danger')
            return render_template('admin/fill_month.html', title='Compila Mese',
                                   form=form, disponibili=disponibili)

        # Giornate già registrate nel mese, per non superare 1.0 al giorno
        prenotate = {}
        for e in TimesheetEntry.query.filter(
                db.extract('year', TimesheetEntry.work_date) == year,
                db.extract('month', TimesheetEntry.work_date) == month).all():
            prenotate[e.work_date] = prenotate.get(e.work_date, 0.0) + float(e.days_worked)

        create = 0
        for giorno in range(1, calendar.monthrange(year, month)[1] + 1):
            work_date = date(year, month, giorno)
            if work_date.weekday() >= 5:
                continue

            residuo = 1.0 - prenotate.get(work_date, 0.0)
            if residuo <= 0:
                continue

            attivita = catalogo[create % len(catalogo)]
            db.session.add(TimesheetEntry(
                work_date=work_date,
                project_id=progetto.id,
                days_worked='1.0' if residuo >= 1.0 else '0.5',
                activity_id=attivita.id,
                is_smartworking=form.is_smartworking.data
            ))
            create += 1

        if create:
            db.session.commit()
            flash('Compilate %d giornate su %s per %02d/%d, distribuendo %d '
                  'attività.' % (create, progetto.name, month, year, len(catalogo)),
                  'success')
            return redirect(url_for('timesheets.index', year=year, month=month))

        flash('Nessuna giornata da compilare: il mese %02d/%d risulta già '
              'completo.' % (month, year), 'info')

    return render_template('admin/fill_month.html', title='Compila Mese',
                           form=form, disponibili=disponibili)
