from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app import db
from app.models.customer import Customer
from app.forms.customer_forms import CustomerForm

customers_bp = Blueprint('customers', __name__, url_prefix='/customers')

@customers_bp.route('/')
@login_required
def index():
    customers = Customer.query.filter_by(active=True).all()
    return render_template('customers/index.html', title='Clienti', customers=customers)

@customers_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    form = CustomerForm()
    if form.validate_on_submit():
        customer = Customer(
            company_name=form.company_name.data,
            vat_number=form.vat_number.data,
            tax_code=form.tax_code.data,
            address=form.address.data,
            city=form.city.data,
            zip_code=form.zip_code.data,
            email=form.email.data,
            phone=form.phone.data,
            active=form.active.data
        )
        db.session.add(customer)
        db.session.commit()
        flash('Cliente aggiunto con successo!', 'success')
        return redirect(url_for('customers.index'))
    return render_template('customers/form.html', title='Nuovo Cliente', form=form)

@customers_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    customer = Customer.query.get_or_404(id)
    form = CustomerForm(obj=customer)
    if form.validate_on_submit():
        form.populate_obj(customer)
        db.session.commit()
        flash('Cliente aggiornato con successo!', 'success')
        return redirect(url_for('customers.index'))
    return render_template('customers/form.html', title='Modifica Cliente', form=form)

@customers_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    customer = Customer.query.get_or_404(id)
    customer.active = False
    db.session.commit()
    flash('Cliente eliminato logicamente.', 'success')
    return redirect(url_for('customers.index'))
