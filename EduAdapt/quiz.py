import json
import random
import urllib.parse
import unicodedata
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def normalize_text(text):
    """
    Decodifica secuencias URL y elimina tildes/acentos y mayúsculas
    para permitir comparaciones insensibles a codificación y acentuación.
    Ej: 'Biolog%C3%ADa' -> 'biologia'
    """
    if not text:
        return ""
    text = urllib.parse.unquote(str(text))
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    ).strip().lower()

class Quiz:
    def __init__(self, json_path=None, temas_avanzados_path=None, materiales_path=None):
        """Inicializa los bancos de preguntas, temas avanzados y materiales usando rutas relativas."""
        self.json_path = json_path or os.path.join(BASE_DIR, "preguntas.json")
        self.temas_avanzados_path = temas_avanzados_path or os.path.join(BASE_DIR, "temas_avanzados.json")
        self.materiales_path = materiales_path or os.path.join(BASE_DIR, "materiales.json")
        
        self.preguntas_banco = self.load_json(self.json_path)
        self.temas_avanzados_banco = self.load_json(self.temas_avanzados_path)
        self.materiales_banco = self.load_json(self.materiales_path)
        
    def load_json(self, path):
        """Carga un archivo JSON de forma segura con codificación UTF-8."""
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"Advertencia: Archivo no encontrado: {path}")
                return []
        except Exception as e:
            print(f"Error cargando archivo {path}: {e}")
            return []
            
    # --- MÉTODOS PARA MATERIAS BÁSICAS Y GENERALES ---
    def get_materias(self):
        """Devuelve una lista ordenada de todas las materias disponibles, incluyendo la categoría avanzada."""
        materias = set(p['materia'] for p in self.preguntas_banco)
        # Aseguramos inclusión de Temas avanzados
        materias.add("📚 Temas avanzados")
        return sorted(list(materias))

    def get_canonical_materia(self, materia):
        """Retorna el nombre oficial de la materia con su grafía y tilde original."""
        if not materia:
            return ""
        norm_input = normalize_text(materia)
        for m in self.get_materias():
            if normalize_text(m) == norm_input:
                return m
        return urllib.parse.unquote(str(materia))
        
    def get_temas(self, materia):
        """Devuelve los temas disponibles para una materia específica."""
        canonical = self.get_canonical_materia(materia)
        norm_canonical = normalize_text(canonical)
        
        if norm_canonical == normalize_text("📚 Temas avanzados") or norm_canonical == "temas avanzados":
            return [t['nombre'] for t in self.temas_avanzados_banco]
            
        temas = set(p['tema'] for p in self.preguntas_banco if normalize_text(p['materia']) == norm_canonical)
        return sorted(list(temas))
        
    def get_preguntas(self, materia, tema=None, cantidad=10):
        """Devuelve preguntas aleatorias filtradas por materia y opcionalmente por tema."""
        norm_materia = normalize_text(materia)
        
        # Si es materia avanzada de 2do BGU
        if norm_materia == normalize_text("📚 Temas avanzados") or norm_materia == "temas avanzados":
            return self.get_preguntas_avanzadas(tema, cantidad=cantidad)
            
        filtradas = [p for p in self.preguntas_banco if normalize_text(p['materia']) == norm_materia]
        
        if tema:
            norm_tema = normalize_text(tema)
            filtradas = [p for p in filtradas if normalize_text(p['tema']) == norm_tema]
            
        random.shuffle(filtradas)
        return filtradas[:cantidad]

    # --- MÉTODOS PARA TEMAS AVANZADOS DE 2.º BGU ---
    def get_categorias_avanzadas(self):
        """Devuelve las categorías de 2do BGU (Álgebra, Funciones, Trigonometría, etc.)."""
        categorias = []
        for t in self.temas_avanzados_banco:
            cat = t.get('categoria', 'General')
            if cat not in categorias:
                categorias.append(cat)
        return categorias

    def get_temas_por_categoria(self, categoria):
        """Devuelve la lista de temas para una categoría de 2do BGU."""
        norm_cat = normalize_text(categoria)
        temas = []
        for t in self.temas_avanzados_banco:
            if normalize_text(t.get('categoria', '')) == norm_cat:
                temas.append({
                    "id": t.get("id"),
                    "nombre": t.get("nombre"),
                    "nivel": t.get("nivel", "2do BGU"),
                    "categoria": t.get("categoria"),
                    "total_preguntas": len(t.get("preguntas", []))
                })
        return temas

    def get_preguntas_avanzadas(self, tema_nombre_o_id=None, cantidad=10):
        """Obtiene preguntas de temas avanzados de 2do BGU adaptadas al formato uniforme."""
        preguntas_formateadas = []
        norm_target = normalize_text(tema_nombre_o_id) if tema_nombre_o_id else None
        
        for t in self.temas_avanzados_banco:
            if not norm_target or normalize_text(t.get("nombre", "")) == norm_target or normalize_text(t.get("id", "")) == norm_target or normalize_text(t.get("categoria", "")) == norm_target:
                for p in t.get("preguntas", []):
                    preguntas_formateadas.append({
                        "materia": "📚 Temas avanzados",
                        "categoria": t.get("categoria"),
                        "tema": t.get("nombre"),
                        "nivel": t.get("nivel", "2do BGU"),
                        "pregunta": p.get("pregunta"),
                        "opciones": p.get("opciones"),
                        "respuesta": p.get("respuesta"),
                        "explicacion": p.get("explicacion")
                    })
                    
        random.shuffle(preguntas_formateadas)
        return preguntas_formateadas[:cantidad]

    # --- MÉTODOS PARA MATERIALES Y RECURSOS EDUCATIVOS ---
    def get_materiales_materias(self):
        """Devuelve las materias que tienen materiales disponibles."""
        materias = set(m.get('materia') for m in self.materiales_banco)
        return sorted(list(materias))

    def get_materiales_temas(self, materia):
        """Devuelve los temas con material para una materia específica."""
        norm_materia = normalize_text(materia)
        return [m.get('tema') for m in self.materiales_banco if normalize_text(m.get('materia', '')) == norm_materia]

    def get_material(self, materia, tema):
        """Obtiene un material educativo específico."""
        norm_materia = normalize_text(materia)
        norm_tema = normalize_text(tema)
        for m in self.materiales_banco:
            if normalize_text(m.get('materia', '')) == norm_materia and normalize_text(m.get('tema', '')) == norm_tema:
                return m
        # Si no coincide exactamente, buscar solo por tema
        for m in self.materiales_banco:
            if normalize_text(m.get('tema', '')) == norm_tema:
                return m
        return None

    def get_all_materiales(self):
        """Retorna todos los materiales disponibles."""
        return self.materiales_banco
