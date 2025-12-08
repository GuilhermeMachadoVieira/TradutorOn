"""Diálogo de configurações."""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QSpinBox, QDoubleSpinBox,
    QComboBox, QCheckBox, QLineEdit, QGroupBox, QTabWidget, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from loguru import logger


class SettingsDialog(QDialog):
    """Diálogo de configurações do TradutorOn."""
    
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings = settings_manager
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """Inicializa interface."""
        self.setWindowTitle("⚙️ Configurações - TradutorOn")
        self.setMinimumSize(500, 600)
        
        layout = QVBoxLayout(self)
        
        # Título
        title = QLabel("⚙️ Configurações")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Tabs
        tabs = QTabWidget()
        
        # Tab 1: Captura
        capture_tab = self._create_capture_tab()
        tabs.addTab(capture_tab, "🖼️ Captura")
        
        # Tab 2: OCR
        ocr_tab = self._create_ocr_tab()
        tabs.addTab(ocr_tab, "🔤 OCR")
        
        # Tab 3: Tradução
        translation_tab = self._create_translation_tab()
        tabs.addTab(translation_tab, "🌐 Tradução")
        
        # Tab 4: Overlay
        overlay_tab = self._create_overlay_tab()
        tabs.addTab(overlay_tab, "👁️ Overlay")
        
        # Tab 5: Cache
        cache_tab = self._create_cache_tab()
        tabs.addTab(cache_tab, "💾 Cache")
        
        layout.addWidget(tabs)
        
        # Botões
        buttons_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Salvar")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setMinimumHeight(40)
        
        cancel_btn = QPushButton("❌ Cancelar")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumHeight(40)
        
        reset_btn = QPushButton("🔄 Restaurar Padrões")
        reset_btn.clicked.connect(self.reset_defaults)
        reset_btn.setMinimumHeight(40)
        
        buttons_layout.addWidget(reset_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(save_btn)
        
        layout.addLayout(buttons_layout)
        
    def _create_capture_tab(self) -> QWidget:
        """Cria tab de captura."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Frame rate
        self.frame_rate_spin = QSpinBox()
        self.frame_rate_spin.setRange(1, 10)
        self.frame_rate_spin.setSuffix(" fps")
        layout.addRow("Frame Rate:", self.frame_rate_spin)
        
        # Frame diff threshold
        self.diff_threshold_spin = QDoubleSpinBox()
        self.diff_threshold_spin.setRange(0.01, 1.0)
        self.diff_threshold_spin.setSingleStep(0.01)
        self.diff_threshold_spin.setDecimals(2)
        layout.addRow("Threshold de Mudança:", self.diff_threshold_spin)
        
        # Diff method
        self.diff_method_combo = QComboBox()
        self.diff_method_combo.addItems(["hybrid", "ssim", "mse", "histogram"])
        layout.addRow("Método de Detecção:", self.diff_method_combo)
        
        return widget
        
    def _create_ocr_tab(self) -> QWidget:
        """Cria tab de OCR."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Languages
        self.ocr_lang_edit = QLineEdit()
        self.ocr_lang_edit.setPlaceholderText("ja, en, ko, zh")
        layout.addRow("Idiomas (separados por vírgula):", self.ocr_lang_edit)
        
        # Use GPU
        self.ocr_gpu_check = QCheckBox("Usar GPU (CUDA)")
        layout.addRow("", self.ocr_gpu_check)
        
        # Min confidence
        self.ocr_confidence_spin = QDoubleSpinBox()
        self.ocr_confidence_spin.setRange(0.0, 1.0)
        self.ocr_confidence_spin.setSingleStep(0.05)
        self.ocr_confidence_spin.setDecimals(2)
        layout.addRow("Confiança Mínima:", self.ocr_confidence_spin)
        
        return widget
        
    def _create_translation_tab(self) -> QWidget:
        """Cria tab de tradução."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Target language
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.addItems(["pt", "en", "es", "fr", "de"])
        layout.addRow("Idioma de Destino:", self.target_lang_combo)
        
        # Groq enabled
        self.groq_enabled_check = QCheckBox("Usar Groq (recomendado)")
        layout.addRow("", self.groq_enabled_check)
        
        # Google enabled
        self.google_enabled_check = QCheckBox("Usar Google Translate")
        layout.addRow("", self.google_enabled_check)
        
        # Auto-detect language
        self.auto_detect_check = QCheckBox("Detecção automática de idioma")
        layout.addRow("", self.auto_detect_check)
        
        # Group nearby text
        self.group_text_check = QCheckBox("Agrupar textos próximos")
        layout.addRow("", self.group_text_check)
        
        # Max group distance
        self.group_distance_spin = QSpinBox()
        self.group_distance_spin.setRange(10, 200)
        self.group_distance_spin.setSuffix(" px")
        layout.addRow("Distância de Agrupamento:", self.group_distance_spin)
        
        return widget
        
    def _create_overlay_tab(self) -> QWidget:
        """Cria tab de overlay."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Auto-hide delay
        self.overlay_hide_spin = QSpinBox()
        self.overlay_hide_spin.setRange(1, 30)
        self.overlay_hide_spin.setSuffix(" segundos")
        layout.addRow("Auto-hide após:", self.overlay_hide_spin)
        
        # Font size
        self.overlay_font_spin = QSpinBox()
        self.overlay_font_spin.setRange(10, 24)
        self.overlay_font_spin.setSuffix(" pt")
        layout.addRow("Tamanho da Fonte:", self.overlay_font_spin)
        
        # Show original
        self.overlay_original_check = QCheckBox("Mostrar texto original")
        layout.addRow("", self.overlay_original_check)
        
        return widget
        
    def _create_cache_tab(self) -> QWidget:
        """Cria tab de cache."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Max entries
        self.cache_max_spin = QSpinBox()
        self.cache_max_spin.setRange(100, 10000)
        self.cache_max_spin.setSingleStep(100)
        layout.addRow("Máximo de Entradas:", self.cache_max_spin)
        
        # Enabled
        self.cache_enabled_check = QCheckBox("Cache habilitado")
        layout.addRow("", self.cache_enabled_check)
        
        return widget
        
    def load_settings(self):
        """Carrega configurações atuais."""
        # Captura
        self.frame_rate_spin.setValue(self.settings.get('capture.frame_rate', 2))
        self.diff_threshold_spin.setValue(self.settings.get('capture.frame_diff_threshold', 0.08))
        diff_method = self.settings.get('capture.frame_diff_method', 'hybrid')
        index = self.diff_method_combo.findText(diff_method)
        if index >= 0:
            self.diff_method_combo.setCurrentIndex(index)
            
        # OCR
        ocr_langs = self.settings.get('ocr.languages', ['ja', 'en'])
        self.ocr_lang_edit.setText(', '.join(ocr_langs))
        self.ocr_gpu_check.setChecked(self.settings.get('ocr.use_gpu', False))
        self.ocr_confidence_spin.setValue(self.settings.get('ocr.min_confidence', 0.5))
        
        # Tradução
        target_lang = self.settings.get('translation.target_language', 'pt')
        index = self.target_lang_combo.findText(target_lang)
        if index >= 0:
            self.target_lang_combo.setCurrentIndex(index)
        self.groq_enabled_check.setChecked(self.settings.get('translation.groq_enabled', True))
        self.google_enabled_check.setChecked(self.settings.get('translation.google_enabled', True))
        self.auto_detect_check.setChecked(self.settings.get('translation.auto_detect', True))
        self.group_text_check.setChecked(self.settings.get('translation.group_nearby', False))
        self.group_distance_spin.setValue(self.settings.get('translation.group_distance', 50))
        
        # Overlay
        self.overlay_hide_spin.setValue(self.settings.get('overlay.auto_hide_delay', 5))
        self.overlay_font_spin.setValue(self.settings.get('overlay.font_size', 14))
        self.overlay_original_check.setChecked(self.settings.get('overlay.show_original', True))
        
        # Cache
        self.cache_max_spin.setValue(self.settings.get('cache.max_entries', 1000))
        self.cache_enabled_check.setChecked(self.settings.get('cache.enabled', True))
        
    def save_settings(self):
        """Salva configurações."""
        try:
            # Captura
            self.settings.set('capture.frame_rate', self.frame_rate_spin.value())
            self.settings.set('capture.frame_diff_threshold', self.diff_threshold_spin.value())
            self.settings.set('capture.frame_diff_method', self.diff_method_combo.currentText())
            
            # OCR
            ocr_langs = [lang.strip() for lang in self.ocr_lang_edit.text().split(',')]
            self.settings.set('ocr.languages', ocr_langs)
            self.settings.set('ocr.use_gpu', self.ocr_gpu_check.isChecked())
            self.settings.set('ocr.min_confidence', self.ocr_confidence_spin.value())
            
            # Tradução
            self.settings.set('translation.target_language', self.target_lang_combo.currentText())
            self.settings.set('translation.groq_enabled', self.groq_enabled_check.isChecked())
            self.settings.set('translation.google_enabled', self.google_enabled_check.isChecked())
            self.settings.set('translation.auto_detect', self.auto_detect_check.isChecked())
            self.settings.set('translation.group_nearby', self.group_text_check.isChecked())
            self.settings.set('translation.group_distance', self.group_distance_spin.value())
            
            # Overlay
            self.settings.set('overlay.auto_hide_delay', self.overlay_hide_spin.value())
            self.settings.set('overlay.font_size', self.overlay_font_spin.value())
            self.settings.set('overlay.show_original', self.overlay_original_check.isChecked())
            
            # Cache
            self.settings.set('cache.max_entries', self.cache_max_spin.value())
            self.settings.set('cache.enabled', self.cache_enabled_check.isChecked())
            
            # Salvar arquivo
            self.settings.save()
            
            logger.info("✅ Configurações salvas com sucesso")
            self.accept()
            
        except Exception as e:
            logger.error(f"Erro ao salvar configurações: {e}")
            
    def reset_defaults(self):
        """Restaura configurações padrão."""
        self.frame_rate_spin.setValue(2)
        self.diff_threshold_spin.setValue(0.08)
        self.diff_method_combo.setCurrentText('hybrid')
        self.ocr_lang_edit.setText('ja, en')
        self.ocr_gpu_check.setChecked(False)
        self.ocr_confidence_spin.setValue(0.5)
        self.target_lang_combo.setCurrentText('pt')
        self.groq_enabled_check.setChecked(True)
        self.google_enabled_check.setChecked(True)
        self.auto_detect_check.setChecked(True)
        self.group_text_check.setChecked(False)
        self.group_distance_spin.setValue(50)
        self.overlay_hide_spin.setValue(5)
        self.overlay_font_spin.setValue(14)
        self.overlay_original_check.setChecked(True)
        self.cache_max_spin.setValue(1000)
        self.cache_enabled_check.setChecked(True)
