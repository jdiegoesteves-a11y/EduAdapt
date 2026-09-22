=============================================
EduAdapt - Tutor de estudio adaptativo (VERSIÓN WEB)
=============================================

1. ¿Qué es EduAdapt?
EduAdapt es una aplicación educativa diseñada en Python con Flask que permite evaluar los conocimientos de los estudiantes, detectar sus fortalezas y debilidades de forma automática y generar una ruta de estudio personalizada. Todo accesible desde cualquier navegador.

2. Problema que resuelve
Muchos estudiantes dedican horas a estudiar sin un enfoque claro. EduAdapt optimiza este proceso enfocando el esfuerzo en los temas más débiles (identificados tras un quiz diagnóstico).

3. Requisitos
- Python 3.x
- Flask (servidor web)
- SQLite, JSON, JS, HTML y CSS.

4. Cómo instalar dependencias
Abre una terminal, navega a la carpeta de este proyecto (EduAdapt) y ejecuta:
pip install -r requirements.txt

5. Cómo ejecutar el programa
Ejecuta el archivo principal:
python app.py

Abre tu navegador y entra a: http://127.0.0.1:5000/

6. Estructura de Archivos
- app.py: Servidor web con Flask (Controlador principal).
- database.py: Manejador de base de datos SQLite.
- quiz.py: Controlador del banco de preguntas.
- analyzer.py: Algoritmo adaptativo.
- preguntas.json: Banco de preguntas estático.
- templates/: Archivos HTML del frontend (Vistas).
- static/: Archivos CSS y librerías estáticas.
