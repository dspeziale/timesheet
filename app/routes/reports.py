from flask import Blueprint, render_template, request, Response, send_file, current_app
from flask_login import login_required
from app import db
from app.models.timesheet import TimesheetEntry
from app.models.project import Project
from app.models.customer import Customer
from datetime import datetime
import pandas as pd
import io

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/monthly', methods=['GET'])
@login_required
def monthly():
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    timesheets = TimesheetEntry.query.filter(
        db.extract('year', TimesheetEntry.work_date) == year,
        db.extract('month', TimesheetEntry.work_date) == month
    ).all()

    # Aggrega per progetto
    summary = {}
    total_general = 0
    for t in timesheets:
        pid = t.project_id
        if pid not in summary:
            summary[pid] = {
                'project': t.project,
                'customer': t.project.customer,
                'days': 0,
                'rate': t.project.daily_rate,
                'total': 0
            }
        days = float(t.days_worked)
        summary[pid]['days'] += days
        summary[pid]['total'] += days * float(t.project.daily_rate)
        total_general += days * float(t.project.daily_rate)

    total_net = total_general * 0.73

    # Simulatore Fiscale - Regime Forfettario
    coeff_redditivita = current_app.config.get('TAX_COEFF_REDDITIVITA', 0.67)
    aliquota_inps = current_app.config.get('TAX_ALIQUOTA_INPS', 0.2623)
    aliquota_imposta = current_app.config.get('TAX_ALIQUOTA_IMPOSTA', 0.15)

    reddito_imponibile_lordo = total_general * coeff_redditivita
    contributi_inps = reddito_imponibile_lordo * aliquota_inps
    reddito_imponibile_fiscale = reddito_imponibile_lordo - contributi_inps
    imposta_sostitutiva = reddito_imponibile_fiscale * aliquota_imposta
    totale_da_pagare = contributi_inps + imposta_sostitutiva
    netto_in_tasca = total_general - contributi_inps - imposta_sostitutiva

    tax_simulator = {
        'coeff_redditivita': coeff_redditivita,
        'aliquota_inps': aliquota_inps,
        'aliquota_imposta': aliquota_imposta,
        'reddito_imponibile_lordo': reddito_imponibile_lordo,
        'contributi_inps': contributi_inps,
        'reddito_imponibile_fiscale': reddito_imponibile_fiscale,
        'imposta_sostitutiva': imposta_sostitutiva,
        'totale_da_pagare': totale_da_pagare,
        'netto_in_tasca': netto_in_tasca
    }

    return render_template('reports/monthly.html', 
                           title='Riepilogo Mensile', 
                           summary=summary.values(), 
                           year=year, 
                           month=month,
                           total_general=total_general,
                           total_net=total_net,
                           tax_simulator=tax_simulator)

@reports_bp.route('/export_excel', methods=['GET'])
@login_required
def export_excel():
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    timesheets = TimesheetEntry.query.filter(
        db.extract('year', TimesheetEntry.work_date) == year,
        db.extract('month', TimesheetEntry.work_date) == month
    ).all()

    data = []
    for t in timesheets:
        data.append({
            'Data': t.work_date.strftime('%Y-%m-%d'),
            'Cliente': t.project.customer.company_name,
            'Progetto': t.project.name,
            'Commessa': t.project.code,
            'Giornate': float(t.days_worked),
            'Tariffa': float(t.project.daily_rate),
            'Totale': float(t.days_worked) * float(t.project.daily_rate),
            'Attività': t.activity.name if t.activity else '',
            'Luogo': 'Smartworking' if t.is_smartworking else ('Trasferta' if t.is_trasferta else 'Sede')
        })

    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Timesheet')
    output.seek(0)
    
    filename = f'timesheet_{year}_{month:02d}.xlsx'
    return send_file(output, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@reports_bp.route('/export_pdf', methods=['GET'])
@login_required
def export_pdf():
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    timesheets = TimesheetEntry.query.filter(
        db.extract('year', TimesheetEntry.work_date) == year,
        db.extract('month', TimesheetEntry.work_date) == month
    ).order_by(TimesheetEntry.work_date).all()

    summary = {}
    total_general = 0
    for t in timesheets:
        pid = t.project_id
        if pid not in summary:
            summary[pid] = {
                'project': t.project,
                'customer': t.project.customer,
                'days': 0,
                'rate': t.project.daily_rate,
                'total': 0
            }
        days = float(t.days_worked)
        summary[pid]['days'] += days
        summary[pid]['total'] += days * float(t.project.daily_rate)
        total_general += days * float(t.project.daily_rate)

    total_net = total_general * 0.73

    # Invece di generare il PDF lato server (che richiede pycairo non compatibile con Vercel),
    # restituiamo un template HTML minimale con window.print()
    return render_template('reports/pdf_template.html', 
                           timesheets=timesheets,
                           summary=summary.values(), 
                           year=year, 
                           month=month,
                           total_general=total_general,
                           total_net=total_net)
