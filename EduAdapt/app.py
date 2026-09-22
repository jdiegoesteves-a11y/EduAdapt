from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from database import Database
from quiz import Quiz
from analyzer import ResultsAnalyzer
import os
import json
import urllib.parse

app = Flask(__name__)
app.secret_key = 'eduadapt_secret_2026'

db = Database()
# Usar ruta absoluta para leer el archivo en Vercel
json_path = os.path.join(os.path.dirname(__file__), 'preguntas.json')
quiz = Quiz(json_path)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash("Por favor completa todos los campos.")
            return redirect(url_for('index'))
            
        user = db.verify_login(username, password)
        if user:
            if user['rol'] == 'ESTUDIANTE' and user['aprobado'] == 0:
                flash("Tu cuenta de estudiante está pendiente de aprobación por un profesor/admin.")
                return redirect(url_for('index'))
                
            session['usuario_id'] = user['id']
            session['nombre'] = user['nombre']
            session['rol'] = user['rol']
            
            if user['rol'] == 'ADMIN':
                return redirect(url_for('admin_dashboard'))
            elif user['rol'] == 'PROFESOR':
                return redirect(url_for('profesor'))
            else:
                return redirect(url_for('menu'))
        else:
            flash("Usuario o contraseña incorrectos.")
            return redirect(url_for('index'))
            
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        curso = request.form.get('curso', '')
        username = request.form.get('username')
        password = request.form.get('password')
        rol = request.form.get('rol') # 'ESTUDIANTE' o 'PROFESOR'
        
        if not all([nombre, username, password, rol]):
            flash("Por favor completa los campos obligatorios.")
            return redirect(url_for('register'))
            
        if rol == 'ESTUDIANTE' and not curso:
            flash("Los estudiantes deben especificar un curso.")
            return redirect(url_for('register'))
            
        success, msg = db.register_user(nombre, curso, username, password, rol)
        if success:
            if rol == 'ESTUDIANTE':
                flash("Registro exitoso. Debes esperar a que un administrador apruebe tu cuenta.")
            else:
                flash("Registro exitoso. Ya puedes iniciar sesión.")
            return redirect(url_for('index'))
        else:
            flash(msg)
            return redirect(url_for('register'))
            
    return render_template('register.html')

@app.route('/admin')
def admin_dashboard():
    if session.get('rol') != 'ADMIN':
        return redirect(url_for('index'))
    pendientes = db.get_pending_students()
    return render_template('admin.html', pendientes=pendientes)

@app.route('/approve/<int:user_id>', methods=['POST'])
def approve(user_id):
    if session.get('rol') != 'ADMIN':
        return jsonify({"error": "No autorizado"}), 403
    db.approve_student(user_id)
    return redirect(url_for('admin_dashboard'))

@app.route('/menu')
def menu():
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
    return render_template('menu.html', nombre=session['nombre'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/seleccion')
def seleccion():
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
    materias = quiz.get_materias()
    return render_template('seleccion.html', materias=materias)

@app.route('/iniciar_diagnostico/<materia>')
def iniciar_diagnostico(materia):
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
    
    materia_canon = quiz.get_canonical_materia(materia)
    preguntas = quiz.get_preguntas(materia_canon, cantidad=10)
    if not preguntas:
        flash(f"No hay preguntas suficientes para {materia_canon}.")
        return redirect(url_for('seleccion'))
        
    session['materia_actual'] = materia_canon
    session['preguntas_actuales'] = preguntas
    session['indice_pregunta'] = 0
    session['respuestas_estudiante'] = []
    
    return redirect(url_for('quiz_view'))

@app.route('/quiz', methods=['GET', 'POST'])
def quiz_view():
    if 'usuario_id' not in session or 'preguntas_actuales' not in session:
        return redirect(url_for('index'))
        
    preguntas = session['preguntas_actuales']
    indice = session['indice_pregunta']
    
    if request.method == 'POST':
        respuesta = request.form.get('respuesta')
        if respuesta is not None:
            pregunta_actual = preguntas[indice]
            fue_correcta = (int(respuesta) == pregunta_actual['respuesta'])
            tema = pregunta_actual['tema']
            
            respuestas_est = session['respuestas_estudiante']
            respuestas_est.append((tema, fue_correcta))
            session['respuestas_estudiante'] = respuestas_est
            
            session['indice_pregunta'] += 1
            if session['indice_pregunta'] >= len(preguntas):
                return redirect(url_for('finalizar_diagnostico'))
            
            return redirect(url_for('quiz_view'))
            
    if indice >= len(preguntas):
         return redirect(url_for('finalizar_diagnostico'))
         
    pregunta = preguntas[indice]
    progreso = ((indice) / len(preguntas)) * 100
    
    return render_template('quiz.html', 
                           pregunta=pregunta, 
                           indice=indice+1, 
                           total=len(preguntas), 
                           progreso=progreso)

@app.route('/finalizar_diagnostico')
def finalizar_diagnostico():
    if 'respuestas_estudiante' not in session:
        return redirect(url_for('menu'))
        
    respuestas = session['respuestas_estudiante']
    materia = session['materia_actual']
    
    porcentaje, rendimiento_tema, prioridades = ResultsAnalyzer.analizar_rendimiento(respuestas)
    
    db.save_result(session['usuario_id'], materia, porcentaje, rendimiento_tema)
    
    correctas = sum(1 for r in respuestas if r[1])
    incorrectas = len(respuestas) - correctas
    
    session['prioridades_actuales'] = prioridades
    
    # Obtener preguntas de refuerzo para los temas que necesitan refuerzo
    preguntas_refuerzo = []
    for tema, rend, clasif in prioridades:
        if clasif == "NECESITA REFUERZO":
            # Obtener 1 o 2 preguntas de ese tema para repasar
            preguntas_tema = quiz.get_preguntas(materia, tema, cantidad=2)
            preguntas_refuerzo.extend(preguntas_tema)
    
    return render_template('resultados.html', 
                           porcentaje=porcentaje,
                           correctas=correctas,
                           incorrectas=incorrectas,
                           prioridades=prioridades,
                           materia=materia,
                           preguntas_refuerzo=preguntas_refuerzo)

@app.route('/plan')
def plan():
    if 'prioridades_actuales' not in session:
        return redirect(url_for('menu'))
    prioridades = session['prioridades_actuales']
    return render_template('plan.html', prioridades=prioridades, materia=session.get('materia_actual'))

@app.route('/practica')
def practica():
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
    materias = quiz.get_materias()
    return render_template('practica.html', materias=materias)

@app.route('/api/temas/<materia>')
def get_temas(materia):
    materia_canon = quiz.get_canonical_materia(materia)
    temas = quiz.get_temas(materia_canon)
    return jsonify(temas)

@app.route('/api/practicar/<materia>/<tema>')
def api_practicar(materia, tema):
    materia_canon = quiz.get_canonical_materia(materia)
    tema_clean = urllib.parse.unquote(tema)
    preguntas = quiz.get_preguntas(materia_canon, tema_clean, cantidad=5)
    return jsonify(preguntas)

@app.route('/progreso')
def progreso():
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
        
    resultados = db.get_last_results(session['usuario_id'])
    
    grafico_data = None
    if resultados:
        ultimo = resultados[0]
        temas_dict = json.loads(ultimo[3])
        grafico_data = {
            "materia": ultimo[0],
            "fecha": ultimo[1][:10],
            "labels": list(temas_dict.keys()),
            "data": list(temas_dict.values())
        }
        
    return render_template('progreso.html', resultados=resultados, grafico=grafico_data)

@app.route('/profesor')
def profesor():
    if session.get('rol') not in ['PROFESOR', 'ADMIN']:
        return redirect(url_for('index'))
    # Obtener los datos de todos los estudiantes
    resultados = db.get_all_student_results()
    stats = db.get_general_statistics()
    return render_template('profesor.html', resultados=resultados, stats=stats)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
