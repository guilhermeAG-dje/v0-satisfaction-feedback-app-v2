from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
import sqlite3
from datetime import datetime
from functools import wraps
import csv
import io

app = Flask(__name__)
app.secret_key = 'chave_secreta_muito_segura_2026'

# Credenciais admin
ADMIN_USER = 'admin'
ADMIN_PASS = 'admin123'

def init_db():
    conn = sqlite3.connect('satisfacao.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS avaliacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grau_satisfacao TEXT NOT NULL,
            data TEXT NOT NULL,
            hora TEXT NOT NULL,
            dia_semana TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect('satisfacao.db')
    conn.row_factory = sqlite3.Row
    return conn

# Decorator para proteger rotas admin
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ============ ROTAS PUBLICAS ============

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/registar', methods=['POST'])
def registar():
    data = request.get_json()
    grau = data.get('grau')
    
    if grau not in ['muito_satisfeito', 'satisfeito', 'insatisfeito']:
        return jsonify({'error': 'Grau invalido'}), 400
    
    now = datetime.now()
    dias_pt = ['Segunda', 'Terca', 'Quarta', 'Quinta', 'Sexta', 'Sabado', 'Domingo']
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO avaliacoes (grau_satisfacao, data, hora, dia_semana)
        VALUES (?, ?, ?, ?)
    ''', (grau, now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), dias_pt[now.weekday()]))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

# ============ ROTAS ADMIN ============

@app.route('/admin_2026')
def admin_redirect():
    return redirect(url_for('login'))

@app.route('/admin_2026/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USER and request.form['password'] == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        return render_template('login.html', error='Credenciais invalidas')
    return render_template('login.html')

@app.route('/admin_2026/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/admin_2026/dashboard')
@login_required
def admin():
    conn = get_db()
    c = conn.cursor()
    
    # Estatisticas totais
    c.execute('SELECT grau_satisfacao, COUNT(*) FROM avaliacoes GROUP BY grau_satisfacao')
    stats = dict(c.fetchall())
    
    total = sum(stats.values()) if stats else 0
    
    # Data para filtro
    filtro_data = request.args.get('data', datetime.now().strftime('%Y-%m-%d'))
    
    # Registos filtrados
    c.execute('SELECT * FROM avaliacoes WHERE data = ? ORDER BY hora DESC', (filtro_data,))
    registos = c.fetchall()
    
    # Todas as datas disponiveis
    c.execute('SELECT DISTINCT data FROM avaliacoes ORDER BY data DESC')
    datas = [row[0] for row in c.fetchall()]
    
    conn.close()
    
    return render_template('admin.html', 
                         stats=stats, 
                         total=total,
                         registos=registos,
                         datas=datas,
                         filtro_data=filtro_data)

@app.route('/admin_2026/exportar/<formato>')
@login_required
def exportar(formato):
    filtro_data = request.args.get('data', '')
    
    conn = get_db()
    c = conn.cursor()
    
    if filtro_data:
        c.execute('SELECT * FROM avaliacoes WHERE data = ?', (filtro_data,))
    else:
        c.execute('SELECT * FROM avaliacoes')
    
    registos = c.fetchall()
    conn.close()
    
    if formato == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Grau Satisfacao', 'Data', 'Hora', 'Dia Semana'])
        for r in registos:
            writer.writerow([r['id'], r['grau_satisfacao'], r['data'], r['hora'], r['dia_semana']])
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment;filename=avaliacoes_{filtro_data or "todas"}.csv'}
        )
    
    elif formato == 'txt':
        output = io.StringIO()
        output.write('RELATORIO DE AVALIACOES\n')
        output.write('=' * 50 + '\n\n')
        for r in registos:
            output.write(f'ID: {r["id"]}\n')
            output.write(f'Satisfacao: {r["grau_satisfacao"]}\n')
            output.write(f'Data: {r["data"]} {r["hora"]}\n')
            output.write(f'Dia: {r["dia_semana"]}\n')
            output.write('-' * 30 + '\n')
        
        return Response(
            output.getvalue(),
            mimetype='text/plain',
            headers={'Content-Disposition': f'attachment;filename=avaliacoes_{filtro_data or "todas"}.txt'}
        )

@app.route('/admin_2026/api/stats')
@login_required
def api_stats():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT grau_satisfacao, COUNT(*) FROM avaliacoes GROUP BY grau_satisfacao')
    stats = dict(c.fetchall())
    conn.close()
    return jsonify(stats)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
