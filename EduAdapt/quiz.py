import json
import random

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
        
    def get_temas(self, materia):
        """Devuelve los temas disponibles para una materia específica."""
        temas = set(p['tema'] for p in self.preguntas_banco if p['materia'] == materia)
        return sorted(list(temas))
        
    def get_preguntas(self, materia, tema=None, cantidad=10):
        """
        Devuelve preguntas aleatorias filtradas por materia y (opcionalmente) por tema.
        Si no hay suficientes preguntas en el banco, devuelve las que haya.
        """
        filtradas = [p for p in self.preguntas_banco if p['materia'] == materia]
        
        if tema:
            filtradas = [p for p in filtradas if p['tema'] == tema]
            
        random.shuffle(filtradas)
        return filtradas[:cantidad]
