"""
Overlay transparente para exibir traduções na tela.
"""

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt, QTimer, QPoint, QRect
from PyQt6.QtGui import QPainter, QColor, QFont
from typing import Tuple, List, Dict
from loguru import logger


class TranslationLabel(QWidget):
    """Label individual de tradução."""

    def __init__(self, original: str, translated: str, bbox: Tuple):
        super().__init__()
        
        self.original = original
        self.translated = translated
        self.bbox = bbox  # (x1, y1, x2, y2)
        
        self.init_ui()

    def init_ui(self):
        """Inicializa UI."""
        # Janela sem bordas, sempre no topo
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        
        # Fundo semi-transparente
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Posicionar sobre o texto original
        x1, y1, x2, y2 = self.bbox
        width = x2 - x1
        height = y2 - y1
        
        # Ajustar posição para aparecer abaixo do texto
        self.setGeometry(int(x1), int(y2 + 5), max(width, 100), 40)

    def paintEvent(self, event):
        """Desenha tradução."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fundo
        bg_color = QColor(0, 0, 0, 220)
        painter.fillRect(self.rect(), bg_color)
        
        # Borda
        painter.setPen(QColor(0, 150, 255))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        
        # Texto
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))
        
        painter.drawText(
            self.rect().adjusted(5, 5, -5, -5),
            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
            self.translated
        )


class TranslationOverlay(QWidget):
    """Overlay principal gerenciando todas as traduções."""

    def __init__(self):
        super().__init__()
        
        self.translations: List[TranslationLabel] = []
        self.auto_hide_ms = 3000  # Esconder após 3s
        
        self.init_ui()
        
        logger.info("TranslationOverlay inicializado")

    def init_ui(self):
        """Inicializa overlay invisível."""
        # Janela invisível fullscreen
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Fullscreen
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

    def add_translation(self, bbox: Tuple, original: str, translated: str):
        """
        Adiciona nova tradução ao overlay.
        
        Args:
            bbox: (x1, y1, x2, y2) coordenadas do texto original
            original: Texto original
            translated: Texto traduzido
        """
        # Criar label
        label = TranslationLabel(original, translated, bbox)
        label.show()
        
        self.translations.append(label)
        
        # Auto-esconder após delay
        QTimer.singleShot(self.auto_hide_ms, lambda: self._remove_translation(label))
        
        logger.debug(f"Tradução adicionada: {original} → {translated}")

    def _remove_translation(self, label: TranslationLabel):
        """Remove tradução do overlay."""
        if label in self.translations:
            self.translations.remove(label)
            label.close()
            label.deleteLater()

    def clear_all(self):
        """Remove todas as traduções."""
        for label in self.translations:
            label.close()
            label.deleteLater()
        
        self.translations.clear()
        logger.debug("Todas as traduções removidas")

    def closeEvent(self, event):
        """Limpa ao fechar."""
        self.clear_all()
        event.accept()
