"""Overlay de tradução flutuante sobre a tela."""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from loguru import logger
from typing import List, Dict, Tuple
from datetime import datetime, timedelta


class TranslationBox(QWidget):
    """Caixa individual de tradução."""
    
    def __init__(self, original: str, translated: str, position: Tuple[int, int], 
                 bbox: Tuple[int, int, int, int], parent=None):
        super().__init__(parent)
        self.original = original
        self.translated = translated
        self.bbox = bbox  # (x, y, width, height)
        self._opacity = 1.0
        self.created_at = datetime.now()
        
        self.init_ui()
        self.move(int(position[0]), int(position[1]))
        
        # Auto-hide após 5 segundos
        self.hide_timer = QTimer()
        self.hide_timer.timeout.connect(self.start_fade_out)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.start(5000)
        
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
            "color: white; font-size: 14px; font-weight: bold; "
            "background: transparent; padding: 0px;"
        )
        self.translation_label.setMaximumWidth(400)
        
        # Label de texto original (menor)
        original_short = self.original[:50] + '...' if len(self.original) > 50 else self.original
        self.original_label = QLabel(f"'{original_short}'")
        self.original_label.setStyleSheet(
            "color: rgba(255, 255, 255, 180); font-size: 10px; "
            "background: transparent; font-style: italic; padding: 0px;"
        )
        self.original_label.setMaximumWidth(400)
        
        layout.addWidget(self.translation_label)
        layout.addWidget(self.original_label)
        
        # Ajustar tamanho
        self.adjustSize()
        
    def paintEvent(self, event):
        """Desenha fundo e borda."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fundo semi-transparente com gradiente
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
        """Getter para opacidade."""
        return self._opacity
        
    @opacity.setter
    def opacity(self, value):
        """Setter para opacidade."""
        self._opacity = value
        self.update()
        
    def mousePressEvent(self, event):
        """Ao clicar, remove imediatamente."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.hide_timer.stop()
            self.deleteLater()


class TranslationOverlay(QWidget):
    """Gerenciador de overlays de tradução."""
    
    def __init__(self, screen_area: Tuple[int, int, int, int]):
        super().__init__()
        self.screen_area = screen_area  # (x, y, width, height)
        self.active_boxes = []
        self.recent_translations = {}  # Cache de traduções recentes
        
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
        
        # Timer para limpar cache de traduções antigas
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._cleanup_old_translations)
        self.cleanup_timer.start(2000)  # A cada 2 segundos
        
        logger.info(f"TranslationOverlay criado na área: {screen_area}")
        
    def show_translation(self, result: Dict):
        """Mostra tradução no overlay."""
        try:
            original = result.get('original', '')
            translated = result.get('translated', '')
            bbox = result.get('bbox')  # BBox relativo à área capturada
            
            if not bbox or not translated:
                logger.warning(f"Resultado inválido: bbox={bbox}, translated={translated}")
                return
                
            # Converter bbox relativo para absoluto
            abs_bbox = self._convert_bbox_to_absolute(bbox)
            
            if not abs_bbox:
                logger.warning("Falha ao converter bbox para absoluto")
                return
                
            # Verificar se já existe tradução similar recente
            if self._is_duplicate(translated, abs_bbox):
                logger.debug(f"⚠️ Tradução duplicada ignorada: '{translated[:30]}'")
                return
                
            # Calcular posição para o box (abaixo do texto original)
            x, y, w, h = abs_bbox
            box_x = x
            box_y = y + h + 5  # 5px abaixo do texto
            
            # Criar chave única para esta tradução
            cache_key = self._make_cache_key(translated, abs_bbox)
            
            # Registrar no cache
            self.recent_translations[cache_key] = datetime.now()
            
            # Criar e mostrar caixa de tradução
            translation_box = TranslationBox(
                original=original,
                translated=translated,
                position=(box_x, box_y),
                bbox=abs_bbox,
                parent=None
            )
            
            self.active_boxes.append(translation_box)
            translation_box.show()
            
            # Limpar boxes antigas
            self._cleanup_old_boxes()
            
            logger.debug(f"✅ Tradução exibida: '{translated[:30]}' em ({box_x}, {box_y})")
                
        except Exception as e:
            logger.error(f"Erro ao mostrar tradução: {e}")
            
    def _is_duplicate(self, translated: str, bbox: Tuple[int, int, int, int]) -> bool:
        """Verifica se tradução já existe recentemente na mesma área."""
        cache_key = self._make_cache_key(translated, bbox)
        
        if cache_key in self.recent_translations:
            # Verificar se ainda é recente (últimos 3 segundos)
            age = datetime.now() - self.recent_translations[cache_key]
            if age.total_seconds() < 3.0:
                return True
                
        # Verificar se já existe box ativa similar
        for box in self.active_boxes:
            try:
                if not box.isHidden():
                    # Mesma tradução?
                    if box.translated == translated:
                        # Mesma região? (tolerância de 20px)
                        if self._bbox_distance(box.bbox, bbox) < 20:
                            return True
            except RuntimeError:
                pass
                
        return False
        
    def _make_cache_key(self, translated: str, bbox: Tuple[int, int, int, int]) -> str:
        """Cria chave única para tradução."""
        x, y, w, h = bbox
        # Arredondar posição para tolerar pequenas variações
        x_rounded = (x // 10) * 10
        y_rounded = (y // 10) * 10
        return f"{translated}_{x_rounded}_{y_rounded}"
        
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
            
    def _convert_bbox_to_absolute(self, bbox: Tuple) -> Tuple[int, int, int, int]:
        """Converte bbox relativo (à área capturada) para coordenadas absolutas da tela."""
        try:
            if not bbox or len(bbox) != 4:
                return None
            
            # Converter para float primeiro, depois para int
            rel_x = float(bbox[0])
            rel_y = float(bbox[1])
            rel_w = float(bbox[2])
            rel_h = float(bbox[3])
            
            area_x, area_y, area_w, area_h = self.screen_area
            
            # Coordenadas absolutas (convertendo para int)
            abs_x = int(area_x + rel_x)
            abs_y = int(area_y + rel_y)
            abs_w = int(rel_w)
            abs_h = int(rel_h)
            
            logger.debug(f"BBox: relativo={bbox} → absoluto=({abs_x}, {abs_y}, {abs_w}, {abs_h})")
            
            return (abs_x, abs_y, abs_w, abs_h)
            
        except Exception as e:
            logger.error(f"Erro ao converter bbox: {e}")
            return None
            
    def _cleanup_old_boxes(self):
        """Remove boxes que já foram deletadas."""
        cleaned_boxes = []
        for box in self.active_boxes:
            try:
                # Tentar acessar box - se foi deletada, vai dar erro
                if not box.isHidden():
                    cleaned_boxes.append(box)
            except RuntimeError:
                # Box já foi deletada - ignorar
                pass
        self.active_boxes = cleaned_boxes
        
    def _cleanup_old_translations(self):
        """Remove traduções antigas do cache."""
        now = datetime.now()
        expired_keys = []
        
        for key, timestamp in self.recent_translations.items():
            age = now - timestamp
            if age.total_seconds() > 5.0:  # Remover após 5 segundos
                expired_keys.append(key)
                
        for key in expired_keys:
            del self.recent_translations[key]
            
        if expired_keys:
            logger.debug(f"🗑️ Cache limpo: {len(expired_keys)} traduções antigas removidas")
        
    def clear_all(self):
        """Remove todas as traduções."""
        for box in self.active_boxes:
            try:
                box.deleteLater()
            except RuntimeError:
                pass
        self.active_boxes.clear()
        self.recent_translations.clear()
        
    def paintEvent(self, event):
        """Desenha contorno da área (debug opcional)."""
        # Não desenhar nada - overlay invisível
        pass


def test_overlay():
    """Teste standalone do overlay."""
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    # Simular área de captura (centro da tela)
    screen_area = (500, 300, 800, 600)
    
    overlay = TranslationOverlay(screen_area)
    overlay.show()
    
    # Simular tradução 1
    QTimer.singleShot(1000, lambda: overlay.show_translation({
        'original': 'こんにちは',
        'translated': 'Olá!',
        'bbox': (50, 50, 100, 30)
    }))
    
    # Simular tradução duplicada (deve ser ignorada)
    QTimer.singleShot(1500, lambda: overlay.show_translation({
        'original': 'こんにちは',
        'translated': 'Olá!',
        'bbox': (50, 50, 100, 30)
    }))
    
    # Simular tradução 2
    QTimer.singleShot(2000, lambda: overlay.show_translation({
        'original': 'ありがとう',
        'translated': 'Obrigado!',
        'bbox': (200, 150, 120, 30)
    }))
    
    # Simular tradução 3
    QTimer.singleShot(3000, lambda: overlay.show_translation({
        'original': 'さようなら',
        'translated': 'Até logo!',
        'bbox': (100, 300, 140, 30)
    }))
    
    print("✅ Overlay de teste ativo!")
    print("💡 Você deve ver 3 traduções (duplicata será ignorada)")
    print("🖱️ Clique em qualquer tradução para removê-la")
    print("⏱️ Traduções desaparecem após 5 segundos")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    test_overlay()
