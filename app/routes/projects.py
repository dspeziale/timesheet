from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.models.project import Project
from app.models.customer import Customer
from app.forms.project_forms import ProjectForm

projects_bp = Blueprint('projects', __name__, url_prefix='/projects')

@projects_bp.route('/')
@login_required
def index():
    projects = Project.query.all()
    return render_template('projects/index.html', title='Progetti', projects=projects)

@projects_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    form = ProjectForm()
    form.customer_id.choices = [(c.id, c.company_name) for c in Customer.query.filter_by(active=True).all()]
    if form.validate_on_submit():
        project = Project(
            code=form.code.data,
            name=form.name.data,
            customer_id=form.customer_id.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            daily_rate=form.daily_rate.data,
            status=form.status.data,
            notes=form.notes.data
        )
        db.session.add(project)
        db.session.commit()
        flash('Progetto aggiunto con successo!', 'success')
        return redirect(url_for('projects.index'))
    return render_template('projects/form.html', title='Nuovo Progetto', form=form)

@projects_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    project = Project.query.get_or_404(id)
    form = ProjectForm(obj=project)
    form.customer_id.choices = [(c.id, c.company_name) for c in Customer.query.filter_by(active=True).all()]
    if form.validate_on_submit():
        form.populate_obj(project)
        db.session.commit()
        flash('Progetto aggiornato con successo!', 'success')
        return redirect(url_for('projects.index'))
    return render_template('projects/form.html', title='Modifica Progetto', form=form)

@projects_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    project = Project.query.get_or_404(id)
    db.session.delete(project)
    db.session.commit()
    flash('Progetto eliminato.', 'success')
    return redirect(url_for('projects.index'))
