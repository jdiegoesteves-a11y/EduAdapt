import json
import random
import urllib.parse
import unicodedata

def normalize_text(text):
    """
    Decodifica secuencias URL y elimina tildes/acentos y mayúsculas
    para permitir comparaciones insensibles a codificación y acentuación.
    Ej: 'Biolog%C3%ADa' -> 'biologia'
        'Biología'       -> 'biologia'
    """
    if not text:
        return ""
    text = urllib.parse.unquote(str(text))
    # Normalizar a NFD para descomponer acentos y removerlos
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    ).strip().lower()

class Quiz:
    def __init__(self, json_path="preguntas.json"):
        """Inicializa el banco de preguntas leyendo el archivo JSON."""
        self.json_path = json_path
        self.preguntas_banco = self.load_preguntas()
        
    def load_preguntas(self):
        """Carga y devuelve la lista de preguntas desde JSON."""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error cargando preguntas: {e}")
            return []
            
    def get_materias(self):
        """Devuelve una lista ordenada de todas las materias disponibles."""
        materias = set(p['materia'] for p in self.preguntas_banco)
        return sorted(list(materias))

    def get_canonical_materia(self, materia):
        """
        Retorna el nombre oficial de la materia con su grafía y tilde original.
        Por ejemplo, si recibe 'Biolog%C3%ADa' o 'biologia', retorna 'Biología'.
        """
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
        temas = set(p['tema'] for p in self.preguntas_banco if normalize_text(p['materia']) == norm_canonical)
        return sorted(list(temas))
        
    def get_preguntas(self, materia, tema=None, cantidad=10):
        """
        Devuelve preguntas aleatorias filtradas por materia y (opcionalmente) por tema.
        Soporta materias y temas decodificados o codificados en URL.
        """
        norm_materia = normalize_text(materia)
        filtradas = [p for p in self.preguntas_banco if normalize_text(p['materia']) == norm_materia]
        
        if tema:
            norm_tema = normalize_text(tema)
            filtradas = [p for p in filtradas if normalize_text(p['tema']) == norm_tema]
            
        random.shuffle(filtradas)
        return filtradas[:cantidad]
