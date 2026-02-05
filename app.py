# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, session, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None
from datetime import datetime, timedelta
import csv
import io

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')
if load_dotenv:
    load_dotenv()

# --- Configuração Database ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

ADMIN_USER = os.getenv('ADMIN_USER', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

# --- Modelos ---
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    grau_satisfacao = db.Column(db.String(20), nullable=False)
    data = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    hora = db.Column(db.String(8), nullable=False)   # HH:MM:SS
    dia_semana = db.Column(db.String(20), nullable=False)

with app.app_context():
    db.create_all()


def admin_logged_in():
    return session.get('admin_logged_in') is True


def admin_required(fn):
    def wrapper(*args, **kwargs):
        if not admin_logged_in():
            return redirect(url_for('admin_login'))
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


def parse_date_ymd(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


def count_by_grau(query):
    muito = query.filter_by(grau_satisfacao='muito_satisfeito').count()
    satis = query.filter_by(grau_satisfacao='satisfeito').count()
    insatis = query.filter_by(grau_satisfacao='insatisfeito').count()
    total = muito + satis + insatis
    pct_muito = round((muito / total * 100), 1) if total else 0
    pct_satis = round((satis / total * 100), 1) if total else 0
    pct_insatis = round((insatis / total * 100), 1) if total else 0
    return {
        'muito': muito,
        'satis': satis,
        'insatis': insatis,
        'total': total,
        'pct_muito': pct_muito,
        'pct_satis': pct_satis,
        'pct_insatis': pct_insatis
    }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    grau = request.form.get('grau') or (request.get_json(silent=True) or {}).get('grau')
    if grau not in ('muito_satisfeito', 'satisfeito', 'insatisfeito'):
        return jsonify({'ok': False, 'message': 'Grau inválido'}), 400
    now = datetime.now()
    feedback = Feedback(
        grau_satisfacao=grau,
        data=now.strftime("%Y-%m-%d"),
        hora=now.strftime("%H:%M:%S"),
        dia_semana=now.strftime("%A")
    )
    db.session.add(feedback)
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/admin_2026/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user = (request.form.get('user') or '').strip()
        password = request.form.get('password') or ''
        if user == ADMIN_USER and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template('admin_login.html', error='Credenciais inválidas')
    return render_template('admin_login.html', error=None)


@app.route('/admin_2026/logout')
@admin_required
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))


@app.route('/admin_2026')
@admin_required
def admin_dashboard():
    today = datetime.now().strftime("%Y-%m-%d")
    day = request.args.get('day') or today
    day_date = parse_date_ymd(day) or datetime.now().date()
    day = day_date.strftime("%Y-%m-%d")

    compare_a = request.args.get('compare_a') or ''
    compare_b = request.args.get('compare_b') or ''

    page = max(int(request.args.get('page', 1)), 1)
    limit = max(int(request.args.get('limit', 50)), 10)
    offset = (page - 1) * limit

    q_day = Feedback.query.filter(Feedback.data == day)
    stats = count_by_grau(q_day)

    # Temporal (últimos 7 dias)
    labels = []
    values = []
    for i in range(6, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        labels.append(d)
        values.append(Feedback.query.filter(Feedback.data == d).count())

    # Comparação entre dias
    compare_data = None
    if compare_a and compare_b:
        a_date = parse_date_ymd(compare_a)
        b_date = parse_date_ymd(compare_b)
        if a_date and b_date:
            a_str = a_date.strftime("%Y-%m-%d")
            b_str = b_date.strftime("%Y-%m-%d")
            compare_data = {
                'a': a_str,
                'b': b_str,
                'a_stats': count_by_grau(Feedback.query.filter(Feedback.data == a_str)),
                'b_stats': count_by_grau(Feedback.query.filter(Feedback.data == b_str))
            }

    total_records = q_day.count()
    records = q_day.order_by(Feedback.data.desc(), Feedback.hora.desc()).offset(offset).limit(limit).all()

    return render_template(
        'admin.html',
        day=day,
        stats=stats,
        labels=labels,
        values=values,
        records=records,
        page=page,
        limit=limit,
        total_records=total_records,
        compare_data=compare_data,
        today=today
    )


@app.route('/admin_2026/export')
@admin_required
def export_data():
    fmt = request.args.get('format', 'csv').lower()
    start = request.args.get('start') or ''
    end = request.args.get('end') or ''

    q = Feedback.query
    if start:
        q = q.filter(Feedback.data >= start)
    if end:
        q = q.filter(Feedback.data <= end)

    rows = q.order_by(Feedback.data.desc(), Feedback.hora.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter='\t' if fmt == 'txt' else ',')
    writer.writerow(['ID', 'Grau', 'Data', 'Hora', 'Dia Semana'])
    for r in rows:
        writer.writerow([r.id, r.grau_satisfacao, r.data, r.hora, r.dia_semana])

    output.seek(0)
    mimetype = 'text/plain' if fmt == 'txt' else 'text/csv'
    filename = 'feedback.txt' if fmt == 'txt' else 'feedback.csv'
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype=mimetype, download_name=filename, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
