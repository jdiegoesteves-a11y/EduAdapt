# 🎓 EduAdapt – Tutor de Estudio Adaptativo

> **Proyecto desarrollado para la competencia:** *Code Battle 2026 – Master Expo*  
> **Alineación:** Objetivo de Desarrollo Sostenible (ODS) 4: **Educación de Calidad**  
> **Tecnologías:** Python 3, Flask, SQLite, HTML5, CSS3, JavaScript, Chart.js

---

## 📌 1. ¿Qué es EduAdapt?
**EduAdapt** es una plataforma web educativa diseñada para personalizar el aprendizaje de estudiantes de bachillerato y secundaria. A través de un test diagnóstico interactivo, el sistema evalúa los conocimientos del estudiante, detecta automáticamente sus fortalezas y debilidades por área temática, y genera una **ruta de estudio personalizada** con recursos y ejercicios enfocados en sus áreas de oportunidad.

---

## 🎯 2. Problema que Resuelve
Muchos estudiantes invierten horas estudiando sin un método claro, repasando lo que ya dominan y descuidando los conceptos donde tienen mayores deficiencias. **EduAdapt** optimiza el tiempo de estudio:
- 📊 **Diagnóstico preciso e inmediato**: Evaluación por materias y temas específicos.
- 🎯 **Ruta adaptativa de aprendizaje**: Sugerencias claras de qué estudiar primero.
- 🧠 **Práctica dirigida**: Preguntas de refuerzo en los temas con menor puntaje.

---

## 🏗️ 3. Estructura del Proyecto

```text
EduAdapt/
├── app.py              # Servidor web Flask y controlador principal de rutas
├── database.py         # Gestión de SQLite (usuarios, diagnósticos e historial)
├── quiz.py             # Lógica de carga y filtrado de preguntas
├── analyzer.py         # Algoritmo de diagnóstico y cálculo adaptativo
├── preguntas.json      # Banco estructurado de preguntas por materia y tema
├── requirements.txt    # Dependencias del proyecto
├── templates/          # Vistas HTML (Jinja2)
│   ├── base.html       # Plantilla base con diseño responsivo y navbar
│   ├── index.html      # Registro e inicio de sesión del estudiante
│   ├── select.html     # Selección de materia y modo (Diagnóstico / Práctica)
│   ├── quiz.html       # Interfaz interactiva de evaluación
│   └── results.html    # Gráficos de rendimiento (Chart.js) y ruta de estudio
└── static/
    └── style.css       # Estilos modernos con paleta visual y animaciones
```

---

## 🚀 4. Instalación y Ejecución

### Prerrequisitos
- **Python 3.8** o superior instalado en el sistema.
- Navegador web moderno (Chrome, Edge, Firefox, etc.).

### Pasos de Instalación

1. **Clonar el repositorio:**
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd EduAdapt
   ```

2. **Crear y activar un entorno virtual (recomendado):**
   - **Windows:**
     ```bash
     python -m venv .venv
     .venv\Scripts\activate
     ```
   - **Linux / Mac:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar la aplicación:**
   ```bash
   python app.py
   ```

5. **Abrir en el navegador:**
   Ingresa a: [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 🛡️ 5. Características Clave
- **100% Funcional Offline / Localhost**: No depende de APIs externas de pago; la base de datos SQLite y el banco de preguntas funcionan de forma local.
- **Gráficos en tiempo real**: Visualización dinámica de fortalezas y debilidades con `Chart.js`.
- **Código limpio y modular**: Separación clara entre modelo de datos, lógica de negocio y presentación visual.
- **Diseño Responsivo**: Adaptado para computadoras, tablets y teléfonos móviles.
