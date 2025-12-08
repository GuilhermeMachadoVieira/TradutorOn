"""Agrupa textos OCR próximos."""
from typing import List, Dict, Tuple
from loguru import logger


class TextGrouper:
    """Agrupa resultados OCR que estão próximos."""
    
    def __init__(self, max_distance: int = 50):
        self.max_distance = max_distance
        logger.info(f"TextGrouper inicializado - distância: {max_distance}px")
        
    def group_results(self, results: List[Dict]) -> List[Dict]:
        """
        Agrupa resultados OCR próximos em um único resultado.
        
        Args:
            results: Lista de resultados OCR com bbox
            
        Returns:
            Lista de resultados agrupados
        """
        if not results or len(results) <= 1:
            return results
            
        grouped = []
        used = set()
        
        for i, result in enumerate(results):
            if i in used:
                continue
                
            # Iniciar grupo com este resultado
            group = [result]
            bbox1 = result.get('bbox')
            
            if not bbox1:
                grouped.append(result)
                used.add(i)
                continue
                
            # Procurar resultados próximos
            for j, other in enumerate(results):
                if j <= i or j in used:
                    continue
                    
                bbox2 = other.get('bbox')
                if not bbox2:
                    continue
                    
                # Calcular distância
                distance = self._bbox_distance(bbox1, bbox2)
                
                if distance <= self.max_distance:
                    group.append(other)
                    used.add(j)
                    
            # Combinar grupo
            if len(group) == 1:
                grouped.append(result)
            else:
                combined = self._combine_group(group)
                grouped.append(combined)
                
            used.add(i)
            
        logger.debug(f"Agrupamento: {len(results)} → {len(grouped)} resultados")
        return grouped
        
    def _bbox_distance(self, bbox1: Tuple, bbox2: Tuple) -> float:
        """Calcula distância entre dois bboxes."""
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        # Centro dos bboxes
        cx1 = x1 + w1 / 2
        cy1 = y1 + h1 / 2
        cx2 = x2 + w2 / 2
        cy2 = y2 + h2 / 2
        
        # Distância euclidiana
        distance = ((cx2 - cx1) ** 2 + (cy2 - cy1) ** 2) ** 0.5
        return distance
        
    def _combine_group(self, group: List[Dict]) -> Dict:
        """Combina múltiplos resultados em um."""
        # Ordenar por posição Y (top to bottom)
        group_sorted = sorted(group, key=lambda r: r.get('bbox', (0, 0, 0, 0))[1])
        
        # Combinar textos
        original_texts = [r.get('original', '') for r in group_sorted if r.get('original')]
        combined_original = ' '.join(original_texts)
        
        # Usar primeira tradução disponível
        translated = group_sorted[0].get('translated', '')
        
        # Calcular bbox combinado (envelope)
        bboxes = [r.get('bbox') for r in group_sorted if r.get('bbox')]
        if bboxes:
            x_min = min(b[0] for b in bboxes)
            y_min = min(b[1] for b in bboxes)
            x_max = max(b[0] + b[2] for b in bboxes)
            y_max = max(b[1] + b[3] for b in bboxes)
            combined_bbox = (x_min, y_min, x_max - x_min, y_max - y_min)
        else:
            combined_bbox = group_sorted[0].get('bbox')
            
        return {
            'original': combined_original,
            'translated': translated,
            'bbox': combined_bbox,
            'confidence': group_sorted[0].get('confidence', 1.0),
            'language': group_sorted[0].get('language', 'unknown'),
            'grouped': True,
            'group_count': len(group)
        }
