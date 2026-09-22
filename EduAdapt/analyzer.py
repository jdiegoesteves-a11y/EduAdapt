class ResultsAnalyzer:
    @staticmethod
    def analizar_rendimiento(respuestas):
        """
        Analiza el rendimiento por tema basado en las respuestas del diagnóstico.
        
        respuestas: lista de tuplas (tema, fue_correcta_boolean)
        Retorna:
        - porcentaje_general: float
        - rendimiento_por_tema: dict {tema: porcentaje}
        - prioridades: lista de tuplas (tema, porcentaje, clasificacion) ordenada por prioridad (menor a mayor porcentaje)
        """
        if not respuestas:
            return 0.0, {}, []
            
        # 1. Calcular porcentaje general
        total_preguntas = len(respuestas)
        correctas_totales = sum(1 for r in respuestas if r[1])
        porcentaje_general = (correctas_totales / total_preguntas) * 100
        
        # 2. Agrupar aciertos y totales por cada tema
        temas_stats = {}
        for tema, correcta in respuestas:
            if tema not in temas_stats:
                temas_stats[tema] = {"total": 0, "correctas": 0}
            temas_stats[tema]["total"] += 1
            if correcta:
                temas_stats[tema]["correctas"] += 1
                
        # 3. Calcular porcentaje específico por tema
        rendimiento_por_tema = {}
        for tema, stats in temas_stats.items():
            rendimiento = (stats["correctas"] / stats["total"]) * 100
            rendimiento_por_tema[tema] = rendimiento
            
        # 4. Clasificar el rendimiento y establecer prioridades
        prioridades = []
        for tema, rendimiento in rendimiento_por_tema.items():
            if rendimiento >= 80:
                clasificacion = "DOMINADO"
            elif rendimiento >= 60:
                clasificacion = "EN PROGRESO"
            else:
                clasificacion = "NECESITA REFUERZO"
                
            prioridades.append((tema, rendimiento, clasificacion))
            
        # Ordenar desde el menor porcentaje al mayor.
        # Los temas con menor porcentaje tendrán mayor prioridad (aparecerán primero).
        prioridades.sort(key=lambda x: x[1])
        
        return porcentaje_general, rendimiento_por_tema, prioridades
