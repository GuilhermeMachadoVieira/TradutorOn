"""Seletor de área da tela com drag-drop."""
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QScreen
from loguru import logger


class AreaSelector(QWidget):
    """Widget para selecionar área da tela com drag-drop."""
    
    # Signal emitido quando área é selecionada
    area_selected = pyqtSignal(tuple)  # (x, y, width, height)
    
    def __init__(self):
        super().__init__()
        self.start_pos = None
        self.end_pos = None
        self.drawing = False
        self.init_ui()
        
    def init_ui(self):
        """Inicializa UI em fullscreen."""
        # Configurar janela
        self.setWindowTitle("Selecione a Área - TradutorOn")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Pegar tamanho da tela
        screen = QScreen.availableGeometry(self.screen())
        self.setGeometry(screen)
        
        # Cursor de cruz
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        logger.info("AreaSelector inicializado")
        
    def paintEvent(self, event):
        """Desenha overlay e retângulo de seleção."""
        painter = QPainter(self)
        
        # Overlay semi-transparente escuro
        overlay_color = QColor(0, 0, 0, 150)
        painter.fillRect(self.rect(), overlay_color)
        
        # Instruções no topo
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Arial", 16, QFont.Weight.Bold)
        painter.setFont(font)
        text = "🖱️ Arraste para selecionar a área | ESC para cancelar"
        text_rect = painter.fontMetrics().boundingRect(text)
        text_x = (self.width() - text_rect.width()) // 2
        painter.drawText(text_x, 40, text)
        
        # Desenhar retângulo de seleção se estiver desenhando
        if self.start_pos and self.end_pos:
            selection_rect = self._get_selection_rect()
            
            # Área clara (sem overlay)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(selection_rect, QColor(0, 0, 0, 0))
            
            # Voltar ao modo normal
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            
            # Borda do retângulo
            pen = QPen(QColor(33, 150, 243), 3, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(selection_rect)
            
            # Dimensões
            if selection_rect.width() > 100 and selection_rect.height() > 50:
                dim_font = QFont("Arial", 12)
                painter.setFont(dim_font)
                dim_text = f"{selection_rect.width()} x {selection_rect.height()} px"
                
                # Fundo para texto
                text_rect = painter.fontMetrics().boundingRect(dim_text)
                bg_rect = QRect(
                    selection_rect.x() + 5,
                    selection_rect.y() - text_rect.height() - 10,
                    text_rect.width() + 10,
                    text_rect.height() + 8
                )
                painter.fillRect(bg_rect, QColor(33, 150, 243, 200))
                
                # Texto
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(
                    bg_rect.x() + 5,
                    bg_rect.y() + text_rect.height() + 2,
                    dim_text
                )
                
    def mousePressEvent(self, event):
        """Inicia seleção."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.end_pos = event.pos()
            self.drawing = True
            logger.debug(f"Início seleção: {self.start_pos}")
            
    def mouseMoveEvent(self, event):
        """Atualiza seleção."""
        if self.drawing:
            self.end_pos = event.pos()
            self.update()  # Redesenha
            
    def mouseReleaseEvent(self, event):
        """Finaliza seleção."""
        if event.button() == Qt.MouseButton.LeftButton and self.drawing:
            self.end_pos = event.pos()
            self.drawing = False
            
            # Verificar se área é válida (mínimo 50x50)
            rect = self._get_selection_rect()
            if rect.width() >= 50 and rect.height() >= 50:
                area = (rect.x(), rect.y(), rect.width(), rect.height())
                logger.info(f"Área selecionada: {area}")
                self.area_selected.emit(area)
                self.close()
            else:
                logger.warning("Área muito pequena, selecione novamente")
                self.start_pos = None
                self.end_pos = None
                self.update()
                
    def keyPressEvent(self, event):
        """Cancela seleção com ESC."""
        if event.key() == Qt.Key.Key_Escape:
            logger.info("Seleção cancelada pelo usuário")
            self.close()
            
    def _get_selection_rect(self) -> QRect:
        """Retorna retângulo da seleção."""
        if not self.start_pos or not self.end_pos:
            return QRect()
            
        x = min(self.start_pos.x(), self.end_pos.x())
        y = min(self.start_pos.y(), self.end_pos.y())
        width = abs(self.end_pos.x() - self.start_pos.x())
        height = abs(self.end_pos.y() - self.start_pos.y())
        
        return QRect(x, y, width, height)


def test_area_selector():
    """Teste standalone do AreaSelector."""
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    def on_area_selected(area):
        x, y, w, h = area
        print(f"✅ Área selecionada:")
        print(f"   Posição: ({x}, {y})")
        print(f"   Tamanho: {w}x{h} px")
        app.quit()
    
    selector = AreaSelector()
    selector.area_selected.connect(on_area_selected)
    selector.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    test_area_selector()
