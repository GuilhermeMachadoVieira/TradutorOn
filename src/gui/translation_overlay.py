"""Overlay de tradução flutuante sobre a tela."""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from loguru import logger
from typing import List, Dict, Tuple
from datetime import datetime


class TranslationBox(QWidget):
    """Caixa individual de tradução."""
    
    def __init__(self, original: str, translated: str, position: Tuple[int, int], 
                 bbox: Tuple[int, int, int, int], parent=None):
        super().__init__(parent)
        self.original = original
        self.translated = translated
        self.bbox = bbox
        self._opacity = 1.0
        self.created_at = datetime.now()
        
        self.init_ui()
        self.move(int(position[0]), int(position[1]))
        
        # Auto-hide após 8 segundos
        self.hide_timer = QTimer()
        self.hide_timer.timeout.connect(self.start_fade_out)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.start(8000)
        
    def init_ui(self):
        """Inicializa UI."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(5)
        
        # Label de tradução
        self.translation_label = QLabel(self.translated)
        self.translation_label.setWordWrap(True)
        self.translation_label.setStyleSheet(
            "color: white; font-size: 13px; font-weight: bold; "
            "background: transparent; padding: 0px; line-height: 1.3;"
        )
        self.translation_label.setMaximumWidth(350)
        
        # Label de texto original (menor)
        original_short = self.original[:80] + '...' if len(self.original) > 80 else self.original
        self.original_label = QLabel(f"'{original_short}'")
        self.original_label.setStyleSheet(
            "color: rgba(255, 255, 255, 160); font-size: 9px; "
            "background: transparent; font-style: italic; padding: 0px;"
        )
        self.original_label.setMaximumWidth(350)
        
        layout.addWidget(self.translation_label)
        layout.addWidget(self.original_label)
        
        # Ajustar tamanho
        self.adjustSize()
        
    def paintEvent(self, event):
        """Desenha fundo e borda."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fundo semi-transparente
        bg_color = QColor(33, 33, 33, int(220 * self._opacity))
        border_color = QColor(33, 150, 243, int(255 * self._opacity))
        
        # Desenhar retângulo arredondado
        painter.setBrush(bg_color)
        pen = QPen(border_color, 2)
        painter.setPen(pen)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)
        
    def start_fade_out(self):
        """Inicia animação de fade out."""
        self.fade_animation = QPropertyAnimation(self, b"opacity")
        self.fade_animation.setDuration(500)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_animation.finished.connect(self.deleteLater)
        self.fade_animation.start()
        
    @pyqtProperty(float)
    def opacity(self):
        return self._opacity
        
    @opacity.setter
    def opacity(self, value):
        self._opacity = value
        self.update()
        
    def mousePressEvent(self, event):
        """Ao clicar, remove imediatamente."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.hide_timer.stop()
            self.deleteLater()


class TranslationOverlay(QWidget):
    """Gerenciador de overlays de tradução com clustering inteligente."""
    
    def __init__(self, screen_area: Tuple[int, int, int, int]):
        super().__init__()
        self.screen_area = screen_area
        self.active_boxes = []
        
        # Sistema de buffer para agrupar linhas
        self.pending_results = []
        self.buffer_timer = QTimer()
        self.buffer_timer.timeout.connect(self._process_buffer)
        self.buffer_timer.setSingleShot(True)
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Posicionar sobre toda a tela
        x, y, w, h = screen_area
        self.setGeometry(x, y, w, h)
        
        logger.info(f"TranslationOverlay criado na área: {screen_area}")
        
    def show_translation(self, result: Dict):
        """Adiciona tradução ao buffer para agrupamento."""
        try:
            original = result.get('original', '')
            translated = result.get('translated', '')
            bbox = result.get('bbox')
            
            if not bbox or not translated:
                return
                
            # Converter bbox
            abs_bbox = self._convert_bbox_to_absolute(bbox)
            if not abs_bbox:
                return
                
            # Adicionar ao buffer
            buffered_result = {
                'original': original,
                'translated': translated,
                'bbox': abs_bbox,
                'timestamp': datetime.now()
            }
            
            self.pending_results.append(buffered_result)
            
            # Reiniciar timer (espera 1.5 segundo após última chegada)
            self.buffer_timer.stop()
            self.buffer_timer.start(1500)
            
            logger.debug(f"📥 Buffer: '{translated[:30]}' | Total: {len(self.pending_results)}")
                
        except Exception as e:
            logger.error(f"Erro ao adicionar tradução: {e}")
            
    def _process_buffer(self):
        """Processa buffer e cria overlays agrupados."""
        if not self.pending_results:
            return
            
        logger.info(f"🔄 Processando buffer com {len(self.pending_results)} resultado(s)")
        
        # Clustering inteligente por posição E alinhamento
        groups = self._smart_clustering(self.pending_results)
        
        logger.info(f"📦 Detectados {len(groups)} balão(ões) de fala")
        
        # Criar overlay para cada grupo
        for i, group in enumerate(groups):
            self._create_grouped_overlay(group, i+1)
            
        # Limpar buffer
        self.pending_results.clear()
        
    def _smart_clustering(self, results: List[Dict]) -> List[List[Dict]]:
        """
        Clustering inteligente baseado em:
        1. Alinhamento horizontal (mesmo X)
        2. Proximidade vertical
        3. Sobreposição horizontal
        """
        if not results:
            return []
            
        if len(results) == 1:
            return [results]
            
        # Ordenar por posição Y (de cima para baixo)
        sorted_results = sorted(results, key=lambda r: r['bbox'][1])
        
        groups = []
        visited = set()
        
        for i, result in enumerate(sorted_results):
            if i in visited:
                continue
                
            # Iniciar novo grupo
            current_group = [result]
            visited.add(i)
            
            bbox1 = result['bbox']
            x1, y1, w1, h1 = bbox1
            
            # Procurar candidatos para agrupar
            for j in range(i+1, len(sorted_results)):
                if j in visited:
                    continue
                    
                candidate = sorted_results[j]
                bbox2 = candidate['bbox']
                x2, y2, w2, h2 = bbox2
                
                # Critérios para agrupar (linhas do mesmo balão):
                # 1. Alinhamento X similar (±30px)
                x_aligned = abs(x1 - x2) < 30
                
                # 2. Sobreposição horizontal
                x_overlap = not (x1 + w1 < x2 or x2 + w2 < x1)
                
                # 3. Proximidade vertical (max 40px)
                y_last = current_group[-1]['bbox'][1]
                h_last = current_group[-1]['bbox'][3]
                vertical_gap = y2 - (y_last + h_last)
                close_vertically = vertical_gap < 40
                
                # 4. Não pode estar muito abaixo
                too_far_down = vertical_gap > 80
                
                # Decidir se agrupa
                should_group = (x_aligned or x_overlap) and close_vertically and not too_far_down
                
                if should_group:
                    current_group.append(candidate)
                    visited.add(j)
                    logger.debug(f"  ↳ Agrupando linha (gap: {vertical_gap:.0f}px, x_aligned: {x_aligned})")
                else:
                    # Se não agrupa, parar de procurar mais abaixo
                    if too_far_down:
                        break
                        
            groups.append(current_group)
            logger.debug(f"  📝 Balão {len(groups)}: {len(current_group)} linha(s)")
            
        return groups
        
    def _create_grouped_overlay(self, group: List[Dict], balloon_num: int):
        """Cria um overlay para um grupo de resultados."""
        if not group:
            return
            
        # Combinar textos (separar por linha)
        originals = [r['original'] for r in group]
        translateds = [r['translated'] for r in group]
        
        combined_original = ' '.join(originals)  # Juntar com espaço
        combined_translated = '\n'.join(translateds)  # Separar por linha
        
        # Calcular bbox envolvente
        bboxes = [r['bbox'] for r in group]
        x_min = min(b[0] for b in bboxes)
        y_min = min(b[1] for b in bboxes)
        x_max = max(b[0] + b[2] for b in bboxes)
        y_max = max(b[1] + b[3] for b in bboxes)
        
        combined_bbox = (x_min, y_min, x_max - x_min, y_max - y_min)
        
        # Calcular posição do overlay (abaixo do bbox)
        box_x = x_min
        box_y = y_max + 5
        
        # Criar overlay
        translation_box = TranslationBox(
            original=combined_original,
            translated=combined_translated,
            position=(box_x, box_y),
            bbox=combined_bbox,
            parent=None
        )
        
        self.active_boxes.append(translation_box)
        translation_box.show()
        
        # Limpar boxes antigas
        self._cleanup_old_boxes()
        
        # Log compacto
        translated_preview = combined_translated.replace('\n', ' | ')[:60]
        logger.info(f"✅ Balão #{balloon_num}: \"{translated_preview}\" ({len(group)} linha(s))")
            
    def _convert_bbox_to_absolute(self, bbox: Tuple) -> Tuple[int, int, int, int]:
        """Converte bbox relativo para absoluto."""
        try:
            if not bbox or len(bbox) != 4:
                return None
            
            rel_x = float(bbox[0])
            rel_y = float(bbox[1])
            rel_w = float(bbox[2])
            rel_h = float(bbox[3])
            
            area_x, area_y, area_w, area_h = self.screen_area
            
            abs_x = int(area_x + rel_x)
            abs_y = int(area_y + rel_y)
            abs_w = int(rel_w)
            abs_h = int(rel_h)
            
            return (abs_x, abs_y, abs_w, abs_h)
            
        except Exception as e:
            logger.error(f"Erro ao converter bbox: {e}")
            return None
            
    def _cleanup_old_boxes(self):
        """Remove boxes deletadas."""
        cleaned = []
        for box in self.active_boxes:
            try:
                if not box.isHidden():
                    cleaned.append(box)
            except RuntimeError:
                pass
        self.active_boxes = cleaned
        
    def clear_all(self):
        """Remove todas as traduções."""
        self.buffer_timer.stop()
        self.pending_results.clear()
        
        for box in self.active_boxes:
            try:
                box.deleteLater()
            except RuntimeError:
                pass
        self.active_boxes.clear()
        
    def paintEvent(self, event):
        """Overlay invisível."""
        pass
