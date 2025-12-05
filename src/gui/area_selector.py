"""
Seletor visual de área da tela (arrastar mouse).
"""

from PyQt6.QtWidgets import QDialog, QApplication
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QScreen
from loguru import logger

from src.utils.types import ScreenArea
from src.capture.monitor_detector import MonitorDetector


class AreaSelector(QDialog):
    """Diálogo para selecionar área da tela."""

    def __init__(self):
        super().__init__()
        
        self.detector = MonitorDetector()
        self.start_point = None
        self.end_point = None
        self.selected_area = None
        
        self.init_ui()
        
        logger.info("AreaSelector inicializado")

    def init_ui(self):
        """Inicializa UI fullscreen transparente."""
        # Configurar janela fullscreen sem bordas
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        
        # Tornar semi-transparente
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Fullscreen em todos os monitores
        screen_geometry = QApplication.primaryScreen().virtualGeometry()
        self.setGeometry(screen_geometry)
        
        # Cursor crosshair
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        # Instruções
        self.setWindowTitle("Selecione a área - Arraste o mouse | ESC para cancelar")

    def paintEvent(self, event):
        """Desenha retângulo de seleção."""
        painter = QPainter(self)
        
        # Fundo escuro semi-transparente
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        
        # Se está selecionando, desenhar retângulo
        if self.start_point and self.end_point:
            # Calcular retângulo
            rect = QRect(self.start_point, self.end_point).normalized()
            
            # Limpar área selecionada (transparente)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            
            # Borda azul brilhante
            pen = QPen(QColor(0, 150, 255), 3, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(rect)
            
            # Texto com dimensões
            width = rect.width()
            height = rect.height()
            text = f"{width}x{height} px"
            
            # Fundo do texto
            text_rect = painter.fontMetrics().boundingRect(text)
            text_rect.moveTopLeft(rect.topLeft() + QPoint(5, -25))
            text_rect.adjust(-5, -2, 5, 2)
            
            painter.fillRect(text_rect, QColor(0, 0, 0, 180))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

    def mousePressEvent(self, event):
        """Início da seleção."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_point = event.pos()
            self.end_point = event.pos()
            self.update()

    def mouseMoveEvent(self, event):
        """Atualiza seleção."""
        if self.start_point:
            self.end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        """Finaliza seleção."""
        if event.button() == Qt.MouseButton.LeftButton and self.start_point:
            self.end_point = event.pos()
            
            # Calcular área selecionada
            rect = QRect(self.start_point, self.end_point).normalized()
            
            # Validar tamanho mínimo
            if rect.width() < 50 or rect.height() < 50:
                logger.warning("Área muito pequena (mínimo 50x50)")
                self.start_point = None
                self.end_point = None
                self.update()
                return
            
            # Converter para coordenadas globais
            global_rect = rect.translated(self.geometry().topLeft())
            
            # Criar ScreenArea
            self.selected_area = ScreenArea(
                x1=global_rect.x(),
                y1=global_rect.y(),
                x2=global_rect.x() + global_rect.width(),
                y2=global_rect.y() + global_rect.height(),
                monitor_index=0  # TODO: Detectar monitor correto
            )
            
            logger.info(f"Área selecionada: {self.selected_area.width}x{self.selected_area.height}")
            self.accept()

    def keyPressEvent(self, event):
        """Cancela com ESC."""
        if event.key() == Qt.Key.Key_Escape:
            logger.info("Seleção cancelada")
            self.reject()

    def get_selected_area(self) -> ScreenArea:
        """Retorna área selecionada."""
        return self.selected_area
