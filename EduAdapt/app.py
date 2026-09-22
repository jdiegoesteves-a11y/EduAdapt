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
quiz = Quiz()

@app.before_request
def track_user_activity():
    """Registra la actividad continua del usuario para el estado 'En línea'."""
    if 'usuario_id' in session:
        db.update_activity(session['usuario_id'])

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
            
        success, msg = db.register_user(nombre, curso, username, password, rol)
        if success:
            if rol == 'ESTUDIANTE':
                flash("Registro completado. Tu cuenta debe ser aprobada por un profesor o administrador antes de acceder.")
            else:
                flash("Registro exitoso. Ahora puedes iniciar sesión.")
            return redirect(url_for('index'))
        else:
            flash(msg)
            return redirect(url_for('register'))
            
    return render_template('register.html')

@app.route('/admin')
def admin_dashboard():
    if session.get('rol') not in ['ADMIN', 'PROFESOR']:
        return redirect(url_for('index'))
    pending_students = db.get_pending_students()
    return render_template('admin.html', students=pending_students)

@app.route('/approve/<int:user_id>')
def approve_student(user_id):
    if session.get('rol') not in ['ADMIN', 'PROFESOR']:
        return redirect(url_for('index'))
    db.approve_student(user_id)
    flash("Estudiante aprobado exitosamente.")
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
    
    # Guarda el resultado y además desglosa cada respuesta en respuestas_detalle
    db.save_result(session['usuario_id'], materia, porcentaje, rendimiento_tema, respuestas_detalle=respuestas)
    
    correctas = sum(1 for r in respuestas if r[1])
    incorrectas = len(respuestas) - correctas
    
    session['prioridades_actuales'] = prioridades
    
    preguntas_refuerzo = []
    for tema, rend, clasif in prioridades:
        if clasif == "NECESITA REFUERZO":
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

# --- MODO DE PRÁCTICA Y TEMAS AVANZADOS DE 2.º BGU ---
@app.route('/practica')
def practica():
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
    materias = quiz.get_materias()
    categorias_avanzadas = quiz.get_categorias_avanzadas()
    return render_template('practica.html', materias=materias, categorias_avanzadas=categorias_avanzadas)

@app.route('/api/temas/<materia>')
def get_temas(materia):
    materia_canon = quiz.get_canonical_materia(materia)
    temas = quiz.get_temas(materia_canon)
    return jsonify(temas)

@app.route('/api/temas_avanzados/<categoria>')
def get_temas_avanzados(categoria):
    categoria_clean = urllib.parse.unquote(categoria)
    temas = quiz.get_temas_por_categoria(categoria_clean)
    return jsonify(temas)

@app.route('/api/practicar/<materia>/<tema>')
def api_practicar(materia, tema):
    materia_canon = quiz.get_canonical_materia(materia)
    tema_clean = urllib.parse.unquote(tema)
    preguntas = quiz.get_preguntas(materia_canon, tema_clean, cantidad=5)
    return jsonify(preguntas)

@app.route('/api/guardar_practica', methods=['POST'])
def api_guardar_practica():
    """Guarda las respuestas de práctica y actualiza el progreso en tiempo real."""
    if 'usuario_id' not in session:
        return jsonify({"status": "error", "message": "No autenticado"}), 401
        
    data = request.get_json() or {}
    materia = data.get('materia', 'Práctica')
    tema = data.get('tema', 'General')
    respuestas = data.get('respuestas', [])
    
    if not respuestas:
        return jsonify({"status": "error", "message": "Sin respuestas"}), 400
        
    db.record_practice_session(session['usuario_id'], materia, tema, respuestas)
    return jsonify({"status": "ok", "message": "Sesión de práctica registrada correctamente."})

# --- MÓDULO DE MATERIALES EDUCATIVOS ---
@app.route('/materiales')
def materiales():
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
        
    materia_req = request.args.get('materia')
    tema_req = request.args.get('tema')
    
    materias = quiz.get_materiales_materias()
    material_actual = None
    
    if materia_req and tema_req:
        material_actual = quiz.get_material(materia_req, tema_req)
    elif materias:
        # Material por defecto (el primero)
        primer_mat = materias[0]
        temas_prim = quiz.get_materiales_temas(primer_mat)
        if temas_prim:
            material_actual = quiz.get_material(primer_mat, temas_prim[0])
            materia_req = primer_mat
            tema_req = temas_prim[0]
            
    return render_template('materiales.html', 
                           materias=materias, 
                           material_actual=material_actual, 
                           materia_req=materia_req, 
                           tema_req=tema_req)

@app.route('/api/materiales/temas')
def api_materiales_temas():
    materia = request.args.get('materia', '')
    materia_clean = urllib.parse.unquote(materia)
    temas = quiz.get_materiales_temas(materia_clean)
    return jsonify(temas)

@app.route('/api/materiales/detalle')
def api_materiales_detalle():
    materia = request.args.get('materia', '')
    tema = request.args.get('tema', '')
    materia_clean = urllib.parse.unquote(materia)
    tema_clean = urllib.parse.unquote(tema)
    mat = quiz.get_material(materia_clean, tema_clean)
    if mat:
        return jsonify(mat)
    return jsonify({"error": "Material no encontrado"}), 404

# --- MI PROGRESO (SINCRONIZADO CON VISTA DEL PROFESOR) ---
@app.route('/progreso')
def progreso():
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
        
    progreso_data = db.get_student_full_progress(session['usuario_id'])
    return render_template('progreso.html', progreso=progreso_data)

@app.route('/api/tarea/entregar', methods=['POST'])
def api_tarea_entregar():
    """Permite al estudiante enviar la respuesta de una tarea."""
    if 'usuario_id' not in session:
        return redirect(url_for('index'))
        
    tarea_id = request.form.get('tarea_id')
    respuesta = request.form.get('respuesta', '')
    if tarea_id:
        db.submit_tarea(int(tarea_id), session['usuario_id'], respuesta)
        flash("Tarea enviada con éxito al profesor.")
    return redirect(url_for('progreso'))

# --- MÓDULO DEL PROFESOR ---
@app.route('/profesor')
def profesor():
    if session.get('rol') not in ['PROFESOR', 'ADMIN']:
        return redirect(url_for('index'))
        
    stats = db.get_teacher_global_stats()
    estudiantes = db.get_all_students_summary()
    return render_template('profesor.html', stats=stats, estudiantes=estudiantes)

@app.route('/profesor/estudiante/<int:estudiante_id>')
def profesor_estudiante(estudiante_id):
    if session.get('rol') not in ['PROFESOR', 'ADMIN']:
        return redirect(url_for('index'))
        
    progreso_data = db.get_student_full_progress(estudiante_id)
    if not progreso_data:
        flash("Estudiante no encontrado.")
        return redirect(url_for('profesor'))
        
    return render_template('profesor_estudiante.html', progreso=progreso_data)

@app.route('/profesor/tarea/calificar', methods=['POST'])
def profesor_tarea_calificar():
    if session.get('rol') not in ['PROFESOR', 'ADMIN']:
        return redirect(url_for('index'))
        
    entrega_id = request.form.get('entrega_id')
    estudiante_id = request.form.get('estudiante_id')
    calificacion = request.form.get('calificacion', 10.0)
    estado = request.form.get('estado', 'RESUELTA_CORRECTA')
    
    if entrega_id:
        db.grade_tarea(int(entrega_id), estado, float(calificacion))
        flash("Tarea calificada correctamente.")
        
    return redirect(url_for('profesor_estudiante', estudiante_id=estudiante_id))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
