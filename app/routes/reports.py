from flask import Blueprint, render_template, request, Response, send_file, current_app
from flask_login import login_required
from app import db
from app.models.timesheet import TimesheetEntry
from app.models.project import Project
from app.models.customer import Customer
from datetime import datetime, timedelta
import calendar
import pandas as pd
import io

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


def _weekdays_between(start, end):
    """Numero di giorni feriali (Lun-Ven) tra due date, estremi inclusi."""
    if not start or not end or end < start:
        return 0
    count = 0
    d = start
    while d <= end:
        if d.weekday() < 5:
            count += 1
        d += timedelta(days=1)
    return count


def _billable_days_span(last_worked, project, month_start, month_end, ferie_entries=None):
    """Giorni fatturabili come giorni feriali (Lun-Ven) continuativi dall'inizio
    della commessa (o inizio mese) fino all'ultimo giorno effettivamente registrato
    nel mese. Non serve registrare ogni giorno: si fattura l'intero periodo lavorato.
    Il range e' ritagliato sull'inizio/fine commessa e sui confini del mese.
    I giorni di ferie che cadono nel periodo vengono sottratti."""
    eff_start = max(month_start, project.start_date) if project.start_date else month_start
    eff_end = min(last_worked, month_end)
    if project.end_date and project.end_date < eff_end:
        eff_end = project.end_date
    days = _weekdays_between(eff_start, eff_end)
    if ferie_entries:
        for fdate, fdays in ferie_entries:
            if eff_start <= fdate <= eff_end and fdate.weekday() < 5:
                days -= fdays
    return max(days, 0)


def _group_by_customer(projects, month_start, month_end, ferie_entries):
    """Raggruppa le voci per progetto in una riga per cliente. I giorni e le
    settimane NON vengono sommati commessa per commessa (creerebbe doppio
    conteggio): si calcola un unico periodo per cliente, dall'inizio della prima
    commessa fino all'ultimo giorno registrato, meno le ferie del periodo."""
    by_customer = {}
    for it in projects:
        cid = it['customer'].id
        if cid not in by_customer:
            by_customer[cid] = {
                'customer': it['customer'],
                'projects': [],
                'mondays': set(),
                'codes': [],
                'names': [],
                'rates': set(),
            }
        g = by_customer[cid]
        g['projects'].append(it)
        g['mondays'] |= it['mondays']
        g['codes'].append(it['project'].code)
        g['names'].append(it['project'].name)
        g['rates'].add(float(it['rate']))

    rows = []
    for g in by_customer.values():
        # Periodo unico del cliente (nessun doppio conteggio tra le commesse)
        eff_start = min(
            (max(month_start, it['project'].start_date) if it['project'].start_date else month_start)
            for it in g['projects']
        )
        eff_end = min(month_end, max(it['last_worked'] for it in g['projects']))
        days = _weekdays_between(eff_start, eff_end)
        for fdate, fdays in ferie_entries:
            if eff_start <= fdate <= eff_end and fdate.weekday() < 5:
                days -= fdays
        days = max(days, 0)

        single_rate = next(iter(g['rates'])) if len(g['rates']) == 1 else None
        if single_rate is not None:
            total = days * single_rate
        else:
            # Tariffe diverse tra commesse: ripiego sulla somma per progetto
            total = sum(it['total'] for it in g['projects'])

        rows.append({
            'customer': g['customer'],
            'code': ', '.join(g['codes']),
            'name': ', '.join(g['names']),
            'weeks_worked': len(g['mondays']),
            'days': days,
            'total': total,
            'rate': single_rate,
        })
    rows.sort(key=lambda x: x['customer'].company_name)
    return rows

@reports_bp.route('/monthly', methods=['GET'])
@login_required
def monthly():
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    timesheets = TimesheetEntry.query.filter(
        db.extract('year', TimesheetEntry.work_date) == year,
        db.extract('month', TimesheetEntry.work_date) == month
    ).all()

    # Aggrega per progetto: si fatturano i giorni feriali continuativi dall'inizio
    # della commessa fino all'ultimo giorno registrato nel mese (non serve
    # registrare ogni giorno). Importo = giorni fatturabili x tariffa giornaliera.
    summary = {}
    for t in timesheets:
        if t.is_ferie or not t.project:
            continue
        pid = t.project_id
        monday = t.work_date - timedelta(days=t.work_date.weekday())
        if pid not in summary:
            summary[pid] = {
                'project': t.project,
                'customer': t.project.customer,
                'rate': t.project.daily_rate,
                'mondays': set(),
                'last_worked': t.work_date
            }
        summary[pid]['mondays'].add(monday)
        if t.work_date > summary[pid]['last_worked']:
            summary[pid]['last_worked'] = t.work_date

    month_start = datetime(year, month, 1).date()
    month_end = datetime(year, month, calendar.monthrange(year, month)[1]).date()
    ferie_entries = [(t.work_date, float(t.days_worked)) for t in timesheets if t.is_ferie]
    projects = list(summary.values())
    for item in projects:
        item['days'] = _billable_days_span(item['last_worked'], item['project'], month_start, month_end, ferie_entries)
        item['total'] = item['days'] * float(item['rate'])

    summary = _group_by_customer(projects, month_start, month_end, ferie_entries)
    total_general = sum(item['total'] for item in summary)

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
                           summary=summary,
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
        if t.is_ferie or not t.project:
            data.append({
                'Data': t.work_date.strftime('%Y-%m-%d'),
                'Cliente': '',
                'Progetto': '',
                'Commessa': '',
                'Giornate': float(t.days_worked),
                'Tariffa': 0,
                'Totale': 0,
                'Attività': '',
                'Luogo': 'Ferie'
            })
            continue
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

    # Riepilogo per progetto (coerente con /monthly): giorni feriali continuativi
    # dall'inizio commessa fino all'ultimo giorno registrato nel mese,
    # importo = giorni fatturabili x tariffa giornaliera.
    summary = {}
    for t in timesheets:
        if t.is_ferie or not t.project:
            continue
        pid = t.project_id
        monday = t.work_date - timedelta(days=t.work_date.weekday())
        if pid not in summary:
            summary[pid] = {
                'project': t.project,
                'customer': t.project.customer,
                'rate': t.project.daily_rate,
                'mondays': set(),
                'last_worked': t.work_date
            }
        summary[pid]['mondays'].add(monday)
        if t.work_date > summary[pid]['last_worked']:
            summary[pid]['last_worked'] = t.work_date

    month_start = datetime(year, month, 1).date()
    month_end = datetime(year, month, calendar.monthrange(year, month)[1]).date()
    ferie_entries = [(t.work_date, float(t.days_worked)) for t in timesheets if t.is_ferie]
    projects = list(summary.values())
    for item in projects:
        item['days'] = _billable_days_span(item['last_worked'], item['project'], month_start, month_end, ferie_entries)
        item['total'] = item['days'] * float(item['rate'])

    summary = _group_by_customer(projects, month_start, month_end, ferie_entries)
    total_general = sum(item['total'] for item in summary)

    total_net = total_general * 0.73

    # Invece di generare il PDF lato server (che richiede pycairo non compatibile con Vercel),
    # restituiamo un template HTML minimale con window.print()
    return render_template('reports/pdf_template.html',
                           timesheets=timesheets,
                           summary=summary,
                           year=year,
                           month=month,
                           total_general=total_general,
                           total_net=total_net)

@reports_bp.route('/export_pdf_week', methods=['GET'])
@login_required
def export_pdf_week():
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)

    timesheets = TimesheetEntry.query.filter(
        db.extract('year', TimesheetEntry.work_date) == year,
        db.extract('month', TimesheetEntry.work_date) == month
    ).order_by(TimesheetEntry.work_date).all()

    def flag_label(entry):
        if entry.is_ferie:
            return 'Ferie'
        if entry.is_smartworking:
            return 'Smartworking'
        if entry.is_trasferta:
            return 'Trasferta'
        return 'Sede'

    # Aggrega per settimana (ISO): una riga per settimana con le attività distinte
    weeks = {}
    for t in timesheets:
        iso_year, iso_week, _ = t.work_date.isocalendar()
        key = (iso_year, iso_week)
        if key not in weeks:
            monday = t.work_date - timedelta(days=t.work_date.weekday())
            sunday = monday + timedelta(days=6)
            weeks[key] = {
                'week_num': iso_week,
                'start': monday,
                'end': sunday,
                'days': 0,
                'activities': [],  # mantiene l'ordine, distinte
                'flags': []        # dettaglio distinto sede/smartworking/trasferta/ferie
            }
        w = weeks[key]
        w['days'] += float(t.days_worked)
        if t.activity and t.activity.name:
            name = t.activity.name.strip()
            if name and name not in w['activities']:
                w['activities'].append(name)
        label = flag_label(t)
        if label not in w['flags']:
            w['flags'].append(label)

    weeks_list = []
    for key in sorted(weeks.keys()):
        w = weeks[key]
        w['activities_str'] = ', '.join(w['activities'])
        w['flags_str'] = ', '.join(w['flags'])
        weeks_list.append(w)

    total_weeks = len(weeks_list)

    month_start = datetime(year, month, 1).date()
    month_end = datetime(year, month, calendar.monthrange(year, month)[1]).date()

    # Riepilogo per progetto conteggiando le settimane lavorate
    # (una settimana conta se lavorata almeno un giorno; le ferie sono escluse)
    project_summary = {}
    for t in timesheets:
        if t.is_ferie or not t.project:
            continue
        pid = t.project_id
        iso_week_key = t.work_date.isocalendar()[:2]  # (iso_year, iso_week)
        if pid not in project_summary:
            project_summary[pid] = {
                'project': t.project,
                'customer': t.project.customer,
                'weeks': set(),
                'last_worked': t.work_date
            }
        project_summary[pid]['weeks'].add(iso_week_key)
        if t.work_date > project_summary[pid]['last_worked']:
            project_summary[pid]['last_worked'] = t.work_date

    project_list = []
    for item in project_summary.values():
        project_list.append({
            'project': item['project'],
            'customer': item['customer'],
            'weeks_worked': len(item['weeks'])
        })
    project_list.sort(key=lambda x: x['project'].name)

    # Giorni lavorati: giorni feriali (Lun-Ven) tenendo conto dell'inizio commessa,
    # dallo start della commessa (o inizio mese) fino all'ultimo giorno registrato,
    # meno le ferie che cadono nel periodo.
    ferie_all = [(t.work_date, float(t.days_worked)) for t in timesheets if t.is_ferie]
    if project_summary:
        eff_start = min(
            (max(month_start, it['project'].start_date) if it['project'].start_date else month_start)
            for it in project_summary.values()
        )
        eff_end = min(month_end, max(it['last_worked'] for it in project_summary.values()))
    else:
        # Nessuna commessa lavorata: fallback all'intero mese
        eff_start, eff_end = month_start, month_end
    working_days_in_month = _weekdays_between(eff_start, eff_end)
    ferie_days = sum(d for fd, d in ferie_all if eff_start <= fd <= eff_end and fd.weekday() < 5)
    giorni_lavorati = working_days_in_month - ferie_days

    return render_template('reports/pdf_week_template.html',
                           weeks=weeks_list,
                           year=year,
                           month=month,
                           project_summary=project_list,
                           total_weeks=total_weeks,
                           working_days_in_month=working_days_in_month,
                           ferie_days=ferie_days,
                           giorni_lavorati=giorni_lavorati)
