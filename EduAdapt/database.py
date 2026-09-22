import sqlite3
import json
import os
from datetime import datetime

# En Vercel, el sistema de archivos es de solo lectura excepto /tmp
if os.environ.get("VERCEL"):
    DB_NAME = "/tmp/eduadapt.db"
else:
    DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eduadapt.db")

class Database:
    def __init__(self):
        # Conecta o crea la base de datos local
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        """Crea las tablas necesarias y realiza migraciones automáticas."""
        cursor = self.conn.cursor()
        
        # Tabla de usuarios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                curso TEXT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                rol TEXT NOT NULL,
                aprobado INTEGER DEFAULT 0,
                ultimo_login DATETIME,
                ultima_actividad DATETIME
            )
        ''')
        
        # Migración: Verificar si columnas de login/actividad existen
        cursor.execute("PRAGMA table_info(usuarios)")
        columnas_usuarios = [col[1] for col in cursor.fetchall()]
        if 'ultimo_login' not in columnas_usuarios:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN ultimo_login DATETIME")
        if 'ultima_actividad' not in columnas_usuarios:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN ultima_actividad DATETIME")
        
        # Tabla de resultados diagnósticos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resultados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                materia TEXT,
                fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                porcentaje_general REAL,
                resultados_tema TEXT,
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
            )
        ''')
        
        # Tabla de detalle de respuestas (Diagnóstico y Práctica)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS respuestas_detalle (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                origen TEXT DEFAULT 'PRACTICA',
                materia TEXT,
                tema TEXT,
                correcta INTEGER NOT NULL,
                fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
            )
        ''')
        
        # Tabla de tareas asignadas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tareas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                descripcion TEXT,
                materia TEXT,
                fecha_entrega TEXT,
                creado_por INTEGER
            )
        ''')
        
        # Tabla de entregas y estado de tareas por estudiante
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entregas_tareas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarea_id INTEGER,
                estudiante_id INTEGER,
                estado TEXT DEFAULT 'PENDIENTE',
                fecha_envio DATETIME,
                calificacion REAL,
                respuesta TEXT,
                FOREIGN KEY(tarea_id) REFERENCES tareas(id),
                FOREIGN KEY(estudiante_id) REFERENCES usuarios(id)
            )
        ''')
        
        # Insertar ADMIN por defecto
        cursor.execute("SELECT id FROM usuarios WHERE username = 'ADMIN'")
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO usuarios (nombre, curso, username, password, rol, aprobado) 
                VALUES ('Administrador', '', 'ADMIN', 'ADMIN', 'ADMIN', 1)
            ''')
            
        # Precargar tareas base si la tabla está vacía
        cursor.execute("SELECT COUNT(*) FROM tareas")
        if cursor.fetchone()[0] == 0:
            tareas_iniciales = [
                ("Taller Práctico: Ecuaciones Cuadráticas", "Resolver los 5 ejercicios de ecuaciones cuadráticas y calcular el discriminante.", "Matemáticas", "2026-09-30"),
                ("Guía de Cinemática y Leyes de Newton", "Resolver problemas de movimiento rectilíneo y diagramas de cuerpo libre.", "Física", "2026-09-28"),
                ("Informe: Teoría Celular y Genética", "Completar la comparación entre células procariotas y eucariotas.", "Biología", "2026-10-02"),
                ("Ejercicios de Cálculo: Derivadas", "Calcular derivadas de polinomios y determinar la pendiente de la recta tangente.", "📚 Temas avanzados", "2026-10-05")
            ]
            for tit, desc, mat, f_ent in tareas_iniciales:
                cursor.execute('''
                    INSERT INTO tareas (titulo, descripcion, materia, fecha_entrega)
                    VALUES (?, ?, ?, ?)
                ''', (tit, desc, mat, f_ent))
                
        # Sincronizar asignaciones de tareas para estudiantes existentes
        cursor.execute("SELECT id FROM usuarios WHERE rol = 'ESTUDIANTE'")
        estudiantes = cursor.fetchall()
        cursor.execute("SELECT id FROM tareas")
        tareas_ids = [t[0] for t in cursor.fetchall()]
        
        for est in estudiantes:
            est_id = est[0]
            for t_id in tareas_ids:
                cursor.execute("SELECT id FROM entregas_tareas WHERE tarea_id = ? AND estudiante_id = ?", (t_id, est_id))
                if not cursor.fetchone():
                    cursor.execute('''
                        INSERT INTO entregas_tareas (tarea_id, estudiante_id, estado)
                        VALUES (?, ?, 'PENDIENTE')
                    ''', (t_id, est_id))
                    
        self.conn.commit()

    def register_user(self, nombre, curso, username, password, rol):
        """Registra un nuevo usuario y autoasigna tareas si es estudiante."""
        cursor = self.conn.cursor()
        try:
            aprobado = 0 # Todos los nuevos registros requieren aprobación.
            ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute('''
                INSERT INTO usuarios (nombre, curso, username, password, rol, aprobado, ultimo_login, ultima_actividad) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (nombre, curso, username, password, rol, aprobado, ahora, ahora))
            user_id = cursor.lastrowid
            
            if rol == 'ESTUDIANTE':
                cursor.execute("SELECT id FROM tareas")
                tareas = cursor.fetchall()
                for t in tareas:
                    cursor.execute('''
                        INSERT INTO entregas_tareas (tarea_id, estudiante_id, estado)
                        VALUES (?, ?, 'PENDIENTE')
                    ''', (t[0], user_id))
                    
            self.conn.commit()
            return True, "Registro exitoso."
        except sqlite3.IntegrityError:
            return False, "El nombre de usuario ya existe."

    def verify_login(self, username, password):
        """Verifica las credenciales y actualiza último inicio de sesión y actividad."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, nombre, rol, aprobado FROM usuarios WHERE username = ? AND password = ?', (username, password))
        row = cursor.fetchone()
        if row:
            user_id = row[0]
            ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute('''
                UPDATE usuarios 
                SET ultimo_login = ?, ultima_actividad = ? 
                WHERE id = ?
            ''', (ahora, ahora, user_id))
            self.conn.commit()
            return {"id": row[0], "nombre": row[1], "rol": row[2], "aprobado": row[3]}
        return None

    def update_activity(self, user_id):
        """Actualiza la marca de tiempo de última actividad para monitoreo 'En línea'."""
        if not user_id:
            return
        cursor = self.conn.cursor()
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE usuarios SET ultima_actividad = ? WHERE id = ?", (ahora, user_id))
        self.conn.commit()

    def get_pending_users(self):
        """Obtiene usuarios pendientes de aprobación."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, nombre, curso, username, rol FROM usuarios WHERE aprobado = 0")
        rows = cursor.fetchall()
        return [{"id": r[0], "nombre": r[1], "curso": r[2], "username": r[3], "rol": r[4]} for r in rows]

    def approve_student(self, user_id):
        """Aprueba a un estudiante (o usuario general)."""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE usuarios SET aprobado = 1 WHERE id = ?", (user_id,))
        self.conn.commit()

    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, nombre, curso, username, rol, aprobado FROM usuarios WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return {"id": row[0], "nombre": row[1], "curso": row[2], "username": row[3], "rol": row[4], "aprobado": row[5]}
        return None
        
    def save_result(self, usuario_id, materia, porcentaje_general, resultados_tema, respuestas_detalle=None):
        """Guarda los resultados del diagnóstico y registra las respuestas individuales."""
        cursor = self.conn.cursor()
        resultados_json = json.dumps(resultados_tema)
        cursor.execute('''
            INSERT INTO resultados (usuario_id, materia, porcentaje_general, resultados_tema)
            VALUES (?, ?, ?, ?)
        ''', (usuario_id, materia, porcentaje_general, resultados_json))
        
        # Registrar en respuestas_detalle si se proporcionan
        if respuestas_detalle:
            for item in respuestas_detalle:
                # item: (tema, fue_correcta)
                tema = item[0]
                correcta = 1 if item[1] else 0
                cursor.execute('''
                    INSERT INTO respuestas_detalle (usuario_id, origen, materia, tema, correcta)
                    VALUES (?, 'DIAGNOSTICO', ?, ?, ?)
                ''', (usuario_id, materia, tema, correcta))
                
        self.conn.commit()

    def record_practice_session(self, usuario_id, materia, tema, respuestas_detalle):
        """
        Registra una sesión del Modo de Práctica:
        respuestas_detalle: lista de tuplas o dicts con (fue_correcta, ...)
        """
        cursor = self.conn.cursor()
        total = len(respuestas_detalle)
        if total == 0:
            return
            
        correctas = 0
        for item in respuestas_detalle:
            es_correcta = 1 if item.get('correcta') or item.get('fue_correcta') else 0
            if es_correcta:
                correctas += 1
            cursor.execute('''
                INSERT INTO respuestas_detalle (usuario_id, origen, materia, tema, correcta)
                VALUES (?, 'PRACTICA', ?, ?, ?)
            ''', (usuario_id, materia, tema, es_correcta))
            
        porcentaje = (correctas / total) * 100
        resultados_tema = {tema: porcentaje}
        cursor.execute('''
            INSERT INTO resultados (usuario_id, materia, porcentaje_general, resultados_tema)
            VALUES (?, ?, ?, ?)
        ''', (usuario_id, materia, porcentaje, json.dumps(resultados_tema)))
        
        self.conn.commit()

    def get_last_results(self, usuario_id):
        """Obtiene los últimos 5 resultados de un usuario."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT materia, fecha, porcentaje_general, resultados_tema 
            FROM resultados 
            WHERE usuario_id = ? 
            ORDER BY fecha DESC LIMIT 5
        ''', (usuario_id,))
        return cursor.fetchall()

    def get_student_full_progress(self, usuario_id):
        """
        Devuelve el objeto consolidado y sincronizado de progreso del estudiante.
        Utilizado tanto en 'Mi progreso' (estudiante) como en el panel del profesor.
        """
        cursor = self.conn.cursor()
        
        # 1. Datos del estudiante y estado En Línea
        cursor.execute('''
            SELECT id, nombre, curso, username, ultimo_login, ultima_actividad
            FROM usuarios WHERE id = ?
        ''', (usuario_id,))
        est_row = cursor.fetchone()
        if not est_row:
            return None
            
        # Calcular si está En Línea (actividad en los últimos 5 minutos / 300 seg)
        ultimo_login = est_row[4] or "Sin registro"
        ultima_actividad = est_row[5] or "Sin registro"
        en_linea = False
        if est_row[5]:
            try:
                dt_act = datetime.strptime(est_row[5], "%Y-%m-%d %H:%M:%S")
                segundos_inactivo = (datetime.now() - dt_act).total_seconds()
                if segundos_inactivo <= 300:
                    en_linea = True
            except Exception:
                pass
                
        estudiante_info = {
            "id": est_row[0],
            "nombre": est_row[1],
            "curso": est_row[2],
            "username": est_row[3],
            "ultimo_login": ultimo_login,
            "ultima_actividad": ultima_actividad,
            "en_linea": en_linea
        }
        
        # 2. Rendimiento por temas a partir de todas las evaluaciones y prácticas
        cursor.execute('''
            SELECT materia, resultados_tema, porcentaje_general, fecha 
            FROM resultados 
            WHERE usuario_id = ? 
            ORDER BY fecha ASC
        ''', (usuario_id,))
        res_rows = cursor.fetchall()
        
        temas_rendimiento = {} # {tema: [lista de porcentajes]}
        areas_rendimiento = {} # {materia: [lista de porcentajes]}
        
        for row in res_rows:
            materia = row[0]
            pct_gen = row[2]
            try:
                t_dict = json.loads(row[1])
                for t_nombre, t_val in t_dict.items():
                    if t_nombre not in temas_rendimiento:
                        temas_rendimiento[t_nombre] = []
                    temas_rendimiento[t_nombre].append(float(t_val))
            except Exception:
                pass
                
            if materia not in areas_rendimiento:
                areas_rendimiento[materia] = []
            areas_rendimiento[materia].append(float(pct_gen))
            
        # Clasificación de temas
        temas_dominados = []
        temas_aprendidos = []
        temas_pendientes = []
        
        for tema, pcts in temas_rendimiento.items():
            prom = sum(pcts) / len(pcts)
            item = {"tema": tema, "promedio": round(prom, 1)}
            if prom >= 80:
                temas_dominados.append(item)
            elif prom >= 60:
                temas_aprendidos.append(item)
            else:
                temas_pendientes.append(item)
                
        # Promedio por áreas o categorías
        progreso_areas = []
        for area, pcts in areas_rendimiento.items():
            prom = sum(pcts) / len(pcts)
            progreso_areas.append({"area": area, "promedio": round(prom, 1)})
            
        # Progreso total acumulado
        if res_rows:
            progreso_total = round(sum(r[2] for r in res_rows) / len(res_rows), 1)
        else:
            progreso_total = 0.0
            
        # Últimos temas practicados (los últimos 5 resultados)
        cursor.execute('''
            SELECT materia, resultados_tema, porcentaje_general, fecha
            FROM resultados
            WHERE usuario_id = ?
            ORDER BY fecha DESC LIMIT 5
        ''', (usuario_id,))
        ultimos_practicados = []
        for r in cursor.fetchall():
            temas_nom = []
            try:
                temas_nom = list(json.loads(r[1]).keys())
            except Exception:
                pass
            ultimos_practicados.append({
                "materia": r[0],
                "temas": ", ".join(temas_nom) if temas_nom else r[0],
                "porcentaje": round(r[2], 1),
                "fecha": r[3][:16] if r[3] else ""
            })
            
        # 3. Estadísticas de respuestas
        cursor.execute('''
            SELECT COUNT(*), SUM(correcta)
            FROM respuestas_detalle
            WHERE usuario_id = ?
        ''', (usuario_id,))
        r_stats = cursor.fetchone()
        total_resp = r_stats[0] or 0
        correctas = r_stats[1] or 0
        incorrectas = total_resp - correctas
        precision = round((correctas / total_resp * 100), 1) if total_resp > 0 else 0.0
        porcentaje_incorrectas = round((incorrectas / total_resp * 100), 1) if total_resp > 0 else 0.0
        
        # Evolución histórica de respuestas (agrupada por fecha)
        cursor.execute('''
            SELECT substr(fecha, 1, 10) as dia, COUNT(*) as total, SUM(correcta) as aciertos
            FROM respuestas_detalle
            WHERE usuario_id = ?
            GROUP BY dia
            ORDER BY dia ASC
            LIMIT 10
        ''', (usuario_id,))
        evolucion = []
        for dia, tot, aci in cursor.fetchall():
            prec_dia = round((aci / tot * 100), 1) if tot > 0 else 0
            evolucion.append({"fecha": dia, "precision": prec_dia, "total": tot})
            
        stats_respuestas = {
            "total_respondidas": total_resp,
            "correctas": correctas,
            "incorrectas": incorrectas,
            "precision": precision,
            "porcentaje_incorrectas": porcentaje_incorrectas,
            "evolucion": evolucion
        }
        
        # 4. Estadísticas de tareas
        cursor.execute('''
            SELECT t.id, t.titulo, t.descripcion, t.materia, t.fecha_entrega, et.estado, et.calificacion, et.fecha_envio
            FROM tareas t
            JOIN entregas_tareas et ON t.id = et.tarea_id
            WHERE et.estudiante_id = ?
            ORDER BY t.fecha_entrega ASC
        ''', (usuario_id,))
        tareas_rows = cursor.fetchall()
        
        total_tareas = len(tareas_rows)
        enviadas = sum(1 for t in tareas_rows if t[5] in ['ENVIADA', 'RESUELTA_CORRECTA', 'RESUELTA_INCORRECTA'])
        no_enviadas = total_tareas - enviadas
        resueltas_correctas = sum(1 for t in tareas_rows if t[5] == 'RESUELTA_CORRECTA' or (t[6] is not None and t[6] >= 7.0))
        pendientes = sum(1 for t in tareas_rows if t[5] == 'PENDIENTE')
        porcentaje_completadas = round((enviadas / total_tareas * 100), 1) if total_tareas > 0 else 0.0
        
        lista_tareas = []
        for t in tareas_rows:
            lista_tareas.append({
                "id": t[0],
                "titulo": t[1],
                "descripcion": t[2],
                "materia": t[3],
                "fecha_entrega": t[4],
                "estado": t[5],
                "calificacion": t[6],
                "fecha_envio": t[7]
            })
            
        stats_tareas = {
            "total_asignadas": total_tareas,
            "enviadas": enviadas,
            "no_enviadas": no_enviadas,
            "resueltas_correctas": resueltas_correctas,
            "pendientes": pendientes,
            "porcentaje_completadas": porcentaje_completadas,
            "lista": lista_tareas
        }
        
        tiene_datos = bool(res_rows or total_resp > 0 or ultimos_practicados)
        
        return {
            "estudiante": estudiante_info,
            "progreso_total": progreso_total,
            "tiene_datos": tiene_datos,
            "temas_dominados": temas_dominados,
            "temas_aprendidos": temas_aprendidos,
            "temas_pendientes": temas_pendientes,
            "progreso_areas": progreso_areas,
            "ultimos_practicados": ultimos_practicados,
            "stats_respuestas": stats_respuestas,
            "stats_tareas": stats_tareas
        }

    def get_all_students_summary(self):
        """Obtiene la lista resumida de todos los estudiantes aprobados para el panel del profesor."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, nombre, curso, username, ultimo_login, ultima_actividad
            FROM usuarios
            WHERE rol = 'ESTUDIANTE' AND aprobado = 1
            ORDER BY nombre ASC
        ''')
        estudiantes = cursor.fetchall()
        
        resumen = []
        for est in estudiantes:
            est_id = est[0]
            prog = self.get_student_full_progress(est_id)
            if prog:
                resumen.append({
                    "id": est[0],
                    "nombre": est[1],
                    "curso": est[2],
                    "username": est[3],
                    "ultimo_login": prog["estudiante"]["ultimo_login"],
                    "ultima_actividad": prog["estudiante"]["ultima_actividad"],
                    "en_linea": prog["estudiante"]["en_linea"],
                    "progreso_total": prog["progreso_total"],
                    "precision": prog["stats_respuestas"]["precision"],
                    "tareas_completadas": f"{prog['stats_tareas']['enviadas']}/{prog['stats_tareas']['total_asignadas']}",
                    "porcentaje_tareas": prog["stats_tareas"]["porcentaje_completadas"]
                })
        return resumen

    def get_teacher_global_stats(self):
        """Estadísticas globales para el encabezado del panel del profesor."""
        cursor = self.conn.cursor()
        
        # Evaluaciones realizadas
        cursor.execute('SELECT COUNT(id), AVG(porcentaje_general) FROM resultados')
        eval_row = cursor.fetchone()
        total_eval = eval_row[0] or 0
        prom_global = round(eval_row[1] or 0, 1)
        
        # Total de estudiantes activos
        cursor.execute("SELECT COUNT(id) FROM usuarios WHERE rol = 'ESTUDIANTE' AND aprobado = 1")
        total_alumnos = cursor.fetchone()[0] or 0
        
        # Rendimiento por materia
        cursor.execute('''
            SELECT materia, COUNT(id), AVG(porcentaje_general) 
            FROM resultados 
            GROUP BY materia
        ''')
        materias_stats = cursor.fetchall()
        
        # Tareas globales
        cursor.execute('''
            SELECT 
                COUNT(*),
                SUM(CASE WHEN estado != 'PENDIENTE' THEN 1 ELSE 0 END),
                SUM(CASE WHEN estado = 'PENDIENTE' THEN 1 ELSE 0 END),
                SUM(CASE WHEN estado = 'RESUELTA_CORRECTA' THEN 1 ELSE 0 END)
            FROM entregas_tareas
        ''')
        t_row = cursor.fetchone()
        tareas_tot = t_row[0] or 0
        tareas_env = t_row[1] or 0
        tareas_pen = t_row[2] or 0
        tareas_res = t_row[3] or 0
        
        return {
            "total_evaluaciones": total_eval,
            "promedio_global": prom_global,
            "total_alumnos": total_alumnos,
            "materias_stats": materias_stats,
            "tareas": {
                "total": tareas_tot,
                "enviadas": tareas_env,
                "pendientes": tareas_pen,
                "resueltas": tareas_res,
                "porcentaje": round((tareas_env / tareas_tot * 100), 1) if tareas_tot > 0 else 0
            }
        }

    def submit_tarea(self, tarea_id, estudiante_id, respuesta_texto):
        """Permite a un estudiante entregar una tarea."""
        cursor = self.conn.cursor()
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            UPDATE entregas_tareas
            SET estado = 'ENVIADA', fecha_envio = ?, respuesta = ?
            WHERE tarea_id = ? AND estudiante_id = ?
        ''', (ahora, respuesta_texto, tarea_id, estudiante_id))
        self.conn.commit()

    def grade_tarea(self, entrega_id, estado, calificacion):
        """Permite al profesor calificar una tarea."""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE entregas_tareas
            SET estado = ?, calificacion = ?
            WHERE id = ?
        ''', (estado, calificacion, entrega_id))
        self.conn.commit()
