
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QRect, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QFont, QFontMetrics
from loguru import logger
from typing import List, Dict, Tuple, Optional
from datetime import datetime


class TextFitter:
    """Calcula tamanho de fonte ideal para caber no espaço do balão."""

    @staticmethod
    def fit_text(
        text: str,
        available_width: int,
        available_height: int,
        max_font_size: int = 13,
        min_font_size: int = 6,
        padding: int = 4
    ) -> Tuple[int, List[str]]:
        """
        Calcula o melhor tamanho de fonte.
        """
        
        effective_width = available_width - (2 * padding)
        effective_height = available_height - (2 * padding)

        if effective_width <= 10 or effective_height <= 10:
            return min_font_size, [text[:20]]

        # Tentar tamanhos de fonte do maior para o menor
        for font_size in range(max_font_size, min_font_size - 1, -1):
            font = QFont("Arial", font_size, QFont.Weight.Bold)
            metrics = QFontMetrics(font)

            # Quebrar texto em linhas
            lines = TextFitter._break_text(text, metrics, effective_width)

            # Calcular altura necessária
            line_height = metrics.height()
            total_height = len(lines) * line_height

            # Se cabe, usar este tamanho
            if total_height <= effective_height and len(lines) <= 5:
                return font_size, lines

        return min_font_size, [text[:30]]

    @staticmethod
    def _break_text(text: str, metrics: QFontMetrics, max_width: int) -> List[str]:
        """Quebra texto em múltiplas linhas."""
        
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            
            if metrics.horizontalAdvance(test_line) <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines if lines else [text[:20]]


class BalloonTextReplacement(QWidget):
    """
    Renderiza APENAS o texto com fundo branco atrás das letras.
    Sem quadrado gigante - bem mais elegante!
    """

    def __init__(
        self,
        bbox: Tuple[int, int, int, int],
        translated_text: str,
        original_text: str = "",
        parent=None
    ):
        super().__init__(parent)

        self.bbox = bbox
        self.translated_text = translated_text
        self.original_text = original_text
        self._opacity = 1.0
        self.created_at = datetime.now()

        x, y, w, h = bbox

        # Calcular tamanho de fonte ideal
        self.font_size, self.lines = TextFitter.fit_text(
            translated_text,
            w,
            h,
            max_font_size=13,
            min_font_size=6,
            padding=4
        )

        # Calcular tamanho necessário para renderizar o texto
        font = QFont("Arial", self.font_size, QFont.Weight.Bold)
        metrics = QFontMetrics(font)
        
        # Calcular largura do texto
        max_line_width = max(metrics.horizontalAdvance(line) for line in self.lines)
        line_height = metrics.height()
        total_height = len(self.lines) * line_height

        # Tamanho final (ajustado ao texto, não ao bbox original)
        text_width = max_line_width + 8  # padding
        text_height = total_height + 8   # padding

        # Posicionar no centro do bbox original
        center_x = x + (w - text_width) // 2
        center_y = y + (h - text_height) // 2

        self.setGeometry(center_x, center_y, text_width, text_height)

        self._setup_ui()

        # Auto-hide após 10 segundos
        self.hide_timer = QTimer()
        self.hide_timer.timeout.connect(self.start_fade_out)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.start(26000)

        logger.debug(
            f"🎈 Texto: {original_text[:30]} → {translated_text[:30]} "
            f"(fonte: {self.font_size}pt, tamanho: {text_width}x{text_height})"
        )

    def _setup_ui(self):
        """Configura window flags."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

    def paintEvent(self, event):
        """Desenha APENAS o texto com fundo branco atrás."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Fonte
        font = QFont("Arial", self.font_size, QFont.Weight.Bold)
        painter.setFont(font)

        # Cor do texto
        text_color = QColor(0, 0, 0, int(255 * self._opacity))
        painter.setPen(text_color)

        # Fundo branco
        bg_color = QColor(255, 255, 255, int(240 * self._opacity))

        metrics = QFontMetrics(font)
        line_height = metrics.height()
        padding = 4

        # Desenhar cada linha
        y_offset = padding
        for i, line in enumerate(self.lines):
            # Calcular bbox para esta linha
            line_width = metrics.horizontalAdvance(line)
            
            # Desenhar fundo branco ATRÁS do texto
            bg_rect = QRect(
                (self.width() - line_width) // 2 - 2,
                y_offset - 2,
                line_width + 4,
                line_height + 2
            )
            painter.fillRect(bg_rect, bg_color)

            # Desenhar texto
            text_rect = QRect(
                0,
                y_offset,
                self.width(),
                line_height
            )
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignCenter,
                line
            )

            y_offset += line_height

    def start_fade_out(self):
        """Inicia animação de fade out (após 10s)."""
        try:
            self.fade_animation = QPropertyAnimation(self, b"opacity")
            self.fade_animation.setDuration(300)
            self.fade_animation.setStartValue(1.0)
            self.fade_animation.setEndValue(0.0)
            self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
            self.fade_animation.finished.connect(self.deleteLater)
            self.fade_animation.start()
        except Exception as e:
            logger.error(f"Erro ao fade: {e}")
            self.deleteLater()

    @pyqtProperty(float)
    def opacity(self):
        """Property para animação."""
        return self._opacity

    @opacity.setter
    def opacity(self, value: float):
        """Setter para animação."""
        self._opacity = max(0.0, min(1.0, value))
        self.update()

    def mousePressEvent(self, event):
        """Ao clicar, remove imediatamente."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.hide_timer.stop()
            self.deleteLater()


class TranslationReplacer(QWidget):
    """
    Gerenciador central de substituição de texto em balões.
    """

    def __init__(self, screen_area: Tuple[int, int, int, int]):
        super().__init__()

        self.screen_area = screen_area
        self.active_replacements: List[BalloonTextReplacement] = []

        # Buffer para agrupar resultados
        self.pending_results: List[Dict] = []
        self.buffer_timer = QTimer()
        self.buffer_timer.timeout.connect(self._process_buffer)
        self.buffer_timer.setSingleShot(True)

        # Setup window
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

        logger.info(
            f"✅ TranslationReplacer inicializado (modo TEXTO COM FUNDO) - "
            f"Área: {screen_area}"
        )

    def show_translation(self, result: Dict):
        """Adiciona uma tradução ao buffer para agrupamento."""
        try:
            original = result.get('original', '')
            translated = result.get('translated', '')
            bbox = result.get('bbox')

            if not bbox or not translated or not original:
                logger.debug(f"⚠️ Resultado incompleto")
                return

            # Converter bbox para absoluto
            abs_bbox = self._convert_bbox_to_absolute(bbox)
            if not abs_bbox:
                return

            # Adicionar ao buffer
            buffered = {
                'original': original,
                'translated': translated,
                'bbox': abs_bbox,
                'timestamp': datetime.now()
            }
            self.pending_results.append(buffered)

            # Restart timer para agrupamento
            self.buffer_timer.stop()
            self.buffer_timer.start(800)

            logger.debug(f"📥 Buffer: {translated[:40]} | Total: {len(self.pending_results)}")

        except Exception as e:
            logger.error(f"❌ Erro ao adicionar tradução: {e}")

    def _process_buffer(self):
        """Processa buffer e cria substituições agrupadas."""
        if not self.pending_results:
            return

        logger.info(
            f"🔄 Processando {len(self.pending_results)} resultado(s)"
        )

        # Agrupar por proximidade
        groups = self._smart_clustering(self.pending_results)
        logger.info(f"📦 {len(groups)} balão(ões) detectado(s)")

        # Criar substituição para cada grupo
        for i, group in enumerate(groups):
            self._create_grouped_replacement(group, i + 1)

        # Limpar buffer
        self.pending_results.clear()

    def _smart_clustering(self, results: List[Dict]) -> List[List[Dict]]:
        """Clustering inteligente por alinhamento e proximidade."""
        
        if not results:
            return []
        if len(results) == 1:
            return [results]

        # Ordenar por Y (cima para baixo)
        sorted_results = sorted(results, key=lambda r: r['bbox'][1])
        groups = []
        visited = set()

        for i, result in enumerate(sorted_results):
            if i in visited:
                continue

            current_group = [result]
            visited.add(i)

            bbox1 = result['bbox']
            x1, y1, w1, h1 = bbox1

            # Procurar próximos textos do mesmo balão
            for j in range(i + 1, len(sorted_results)):
                if j in visited:
                    continue

                candidate = sorted_results[j]
                bbox2 = candidate['bbox']
                x2, y2, w2, h2 = bbox2

                # Critérios para pertencer ao mesmo balão
                x_aligned = abs(x1 - x2) < 25
                x_overlap = not (x1 + w1 < x2 or x2 + w2 < x1)

                y_last = current_group[-1]['bbox'][1]
                h_last = current_group[-1]['bbox'][3]
                vertical_gap = y2 - (y_last + h_last)

                close_vertically = vertical_gap < 35
                too_far_down = vertical_gap > 70

                should_group = (x_aligned or x_overlap) and close_vertically and not too_far_down

                if should_group:
                    current_group.append(candidate)
                    visited.add(j)
                elif too_far_down:
                    break

            groups.append(current_group)

        return groups

    def _create_grouped_replacement(self, group: List[Dict], balloon_num: int):
        """Cria substituição para um grupo de textos."""
        
        if not group:
            return

        # Combinar textos
        originals = [r['original'] for r in group]
        translateds = [r['translated'] for r in group]

        combined_original = ' '.join(originals)
        combined_translated = '\n'.join(translateds)

        # Calcular bbox envolvente
        bboxes = [r['bbox'] for r in group]
        x_min = min(b[0] for b in bboxes)
        y_min = min(b[1] for b in bboxes)
        x_max = max(b[0] + b[2] for b in bboxes)
        y_max = max(b[1] + b[3] for b in bboxes)

        final_bbox = (x_min, y_min, x_max - x_min, y_max - y_min)

        # Criar substituição
        replacement = BalloonTextReplacement(
            bbox=final_bbox,
            translated_text=combined_translated,
            original_text=combined_original
        )

        self.active_replacements.append(replacement)
        replacement.show()

        # Cleanup
        self._cleanup_old_replacements()

        # Log
        trans_preview = combined_translated.replace('\n', ' | ')[:50]
        logger.info(
            f"✅ Balão #{balloon_num}: \"{trans_preview}\" "
            f"({len(group)} linha(s)) - TEXTO RENDERIZADO"
        )

    def _convert_bbox_to_absolute(self, bbox: Tuple) -> Optional[Tuple[int, int, int, int]]:
        """Converte bbox relativo para absoluto."""
        try:
            if not bbox or len(bbox) != 4:
                return None

            rel_x, rel_y, rel_w, rel_h = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
            area_x, area_y, area_w, area_h = self.screen_area

            abs_x = int(area_x + rel_x)
            abs_y = int(area_y + rel_y)
            abs_w = int(max(rel_w, 40))
            abs_h = int(max(rel_h, 20))

            return (abs_x, abs_y, abs_w, abs_h)

        except Exception as e:
            logger.error(f"❌ Erro ao converter bbox: {e}")
            return None

    def _cleanup_old_replacements(self):
        """Remove substituições antigas/deletadas."""
        cleaned = []
        for repl in self.active_replacements:
            try:
                if not repl.isHidden() and repl.isVisible():
                    cleaned.append(repl)
            except RuntimeError:
                pass
        self.active_replacements = cleaned

    def clear_all(self):
        """Remove todas as substituições."""
        self.buffer_timer.stop()
        self.pending_results.clear()

        for repl in self.active_replacements:
            try:
                repl.hide()
                repl.deleteLater()
            except RuntimeError:
                pass

        self.active_replacements.clear()
        logger.info("🗑️ Todas as substituições removidas")

    def paintEvent(self, event):
        """Overlay invisível."""
        pass