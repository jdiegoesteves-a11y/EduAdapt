from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from database import Database
from quiz import Quiz
from analyzer import ResultsAnalyzer
import json

app = Flask(__name__)
app.secret_key = 'eduadapt_secret_2026'

db = Database()
quiz = Quiz("preguntas.json")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        curso = request.form.get('curso')
        if not nombre or not curso:
            flash("Por favor completa todos los campos.")
            return redirect(url_for('index'))
            
        usuario_id = db.get_or_create_user(nombre, curso)
        session['usuario_id'] = usuario_id
        session['nombre'] = nombre
        return redirect(url_for('menu'))
    return render_template('index.html')

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
    
    preguntas = quiz.get_preguntas(materia, cantidad=10)
    if not preguntas:
        flash(f"No hay preguntas suficientes para {materia}.")
        return redirect(url_for('seleccion'))
        
    session['materia_actual'] = materia
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
    temas = quiz.get_temas(materia)
    return jsonify(temas)

@app.route('/api/practicar/<materia>/<tema>')
def api_practicar(materia, tema):
    preguntas = quiz.get_preguntas(materia, tema, cantidad=5)
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
    # Obtener los datos de todos los estudiantes
    resultados = db.get_all_student_results()
    stats = db.get_general_statistics()
    return render_template('profesor.html', resultados=resultados, stats=stats)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
