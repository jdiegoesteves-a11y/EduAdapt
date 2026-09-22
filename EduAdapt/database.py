import sqlite3
import json
import os

# En Vercel, el sistema de archivos es de solo lectura excepto /tmp
if os.environ.get("VERCEL"):
    DB_NAME = "/tmp/eduadapt.db"
else:
    DB_NAME = "eduadapt.db"

class Database:
    def __init__(self):
        # Conecta o crea la base de datos local
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        """Crea las tablas necesarias si no existen."""
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
                aprobado INTEGER DEFAULT 0
            )
        ''')
        
        # Tabla de resultados para almacenar el progreso y porcentaje por temas
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
        
        # Insertar ADMIN por defecto
        cursor.execute("SELECT id FROM usuarios WHERE username = 'ADMIN'")
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO usuarios (nombre, curso, username, password, rol, aprobado) 
                VALUES ('Administrador', '', 'ADMIN', 'ADMIN', 'ADMIN', 1)
            ''')
            
        self.conn.commit()

    def register_user(self, nombre, curso, username, password, rol):
        """Registra un nuevo usuario."""
        cursor = self.conn.cursor()
        try:
            aprobado = 1 if rol == 'PROFESOR' else 0 # Profesores pre-aprobados, estudiantes no.
            cursor.execute('''
                INSERT INTO usuarios (nombre, curso, username, password, rol, aprobado) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (nombre, curso, username, password, rol, aprobado))
            self.conn.commit()
            return True, "Registro exitoso."
        except sqlite3.IntegrityError:
            return False, "El nombre de usuario ya existe."

    def verify_login(self, username, password):
        """Verifica las credenciales y devuelve el usuario si es correcto."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, nombre, rol, aprobado FROM usuarios WHERE username = ? AND password = ?', (username, password))
        row = cursor.fetchone()
        if row:
            return {"id": row[0], "nombre": row[1], "rol": row[2], "aprobado": row[3]}
        return None

    def get_pending_students(self):
        """Obtiene estudiantes pendientes de aprobación."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, nombre, curso, username FROM usuarios WHERE rol = 'ESTUDIANTE' AND aprobado = 0")
        rows = cursor.fetchall()
        return [{"id": r[0], "nombre": r[1], "curso": r[2], "username": r[3]} for r in rows]

    def approve_student(self, user_id):
        """Aprueba a un estudiante."""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE usuarios SET aprobado = 1 WHERE id = ?", (user_id,))
        self.conn.commit()
        
    def save_result(self, usuario_id, materia, porcentaje_general, resultados_tema):
        """Guarda los resultados del diagnostico en la base de datos."""
        cursor = self.conn.cursor()
        
        # Convertimos el diccionario de resultados_tema a JSON para guardarlo como texto
        resultados_json = json.dumps(resultados_tema)
        
        cursor.execute('''
            INSERT INTO resultados (usuario_id, materia, porcentaje_general, resultados_tema)
            VALUES (?, ?, ?, ?)
        ''', (usuario_id, materia, porcentaje_general, resultados_json))
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

    def get_all_student_results(self):
        """Obtiene todos los resultados de todos los estudiantes."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT u.nombre, u.curso, r.materia, r.porcentaje_general, r.fecha
            FROM resultados r
            JOIN usuarios u ON r.usuario_id = u.id
            ORDER BY r.fecha DESC
        ''')
        return cursor.fetchall()

    def get_general_statistics(self):
        """Calcula estadísticas generales de la plataforma."""
        cursor = self.conn.cursor()
        
        # Promedio general de todas las materias
        cursor.execute('SELECT AVG(porcentaje_general) FROM resultados')
        promedio_global = cursor.fetchone()[0] or 0
        
        # Total de evaluaciones realizadas
        cursor.execute('SELECT COUNT(id) FROM resultados')
        total_evaluaciones = cursor.fetchone()[0] or 0
        
        # Evaluaciones por materia
        cursor.execute('''
            SELECT materia, COUNT(id), AVG(porcentaje_general) 
            FROM resultados 
            GROUP BY materia
        ''')
        materias_stats = cursor.fetchall()
        
        return {
            "promedio_global": round(promedio_global, 2),
            "total_evaluaciones": total_evaluaciones,
            "materias_stats": materias_stats
        }
