"""
Diálogo de configurações.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QComboBox, QSpinBox,
    QCheckBox, QPushButton, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt
from loguru import logger

from src.config.settings import SettingsManager


class SettingsDialog(QDialog):
    """Diálogo de configurações."""

    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        
        self.settings = settings
        self.init_ui()
        self.load_settings()
        
        logger.info("SettingsDialog inicializado")

    def init_ui(self):
        """Inicializa UI."""
        self.setWindowTitle("⚙️ Configurações")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self.create_general_tab(), "Geral")
        tabs.addTab(self.create_translation_tab(), "Tradução")
        tabs.addTab(self.create_ocr_tab(), "OCR")
        tabs.addTab(self.create_overlay_tab(), "Overlay")
        
        layout.addWidget(tabs)
        
        # Botões
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Salvar")
        save_btn.clicked.connect(self.save_settings)
        
        cancel_btn = QPushButton("❌ Cancelar")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)

    def create_general_tab(self) -> QWidget:
        """Aba de configurações gerais."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Frame rate
        self.frame_rate_spin = QSpinBox()
        self.frame_rate_spin.setRange(1, 10)
        self.frame_rate_spin.setSuffix(" fps")
        layout.addRow("Taxa de captura:", self.frame_rate_spin)
        
        # Detection threshold
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(1, 50)
        self.threshold_spin.setSuffix("%")
        layout.addRow("Sensibilidade de mudança:", self.threshold_spin)
        
        return widget

    def create_translation_tab(self) -> QWidget:
        """Aba de tradução."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Groq
        groq_group = QGroupBox("Groq API")
        groq_layout = QFormLayout()
        
        self.groq_enabled = QCheckBox("Habilitado")
        self.groq_key = QLineEdit()
        self.groq_key.setPlaceholderText("gsk_...")
        self.groq_key.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.groq_model = QComboBox()
        self.groq_model.addItems([
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant"
        ])
        
        groq_layout.addRow("Status:", self.groq_enabled)
        groq_layout.addRow("API Key:", self.groq_key)
        groq_layout.addRow("Modelo:", self.groq_model)
        groq_group.setLayout(groq_layout)
        
        # Google
        google_group = QGroupBox("Google Translate")
        google_layout = QFormLayout()
        
        self.google_enabled = QCheckBox("Habilitado")
        google_layout.addRow("Status:", self.google_enabled)
        google_group.setLayout(google_layout)
        
        # Ollama
        ollama_group = QGroupBox("Ollama (Local)")
        ollama_layout = QFormLayout()
        
        self.ollama_enabled = QCheckBox("Habilitado")
        self.ollama_model = QLineEdit()
        self.ollama_model.setPlaceholderText("llama3.1")
        
        ollama_layout.addRow("Status:", self.ollama_enabled)
        ollama_layout.addRow("Modelo:", self.ollama_model)
        ollama_group.setLayout(ollama_layout)
        
        layout.addWidget(groq_group)
        layout.addWidget(google_group)
        layout.addWidget(ollama_group)
        layout.addStretch()
        
        return widget

    def create_ocr_tab(self) -> QWidget:
        """Aba de OCR."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Idiomas
        self.ocr_langs = QLineEdit()
        self.ocr_langs.setPlaceholderText("en, ko, ja")
        layout.addRow("Idiomas:", self.ocr_langs)
        
        # GPU
        self.use_gpu = QCheckBox("Usar GPU (se disponível)")
        layout.addRow("Aceleração:", self.use_gpu)
        
        # Confiança mínima
        self.confidence_spin = QSpinBox()
        self.confidence_spin.setRange(0, 100)
        self.confidence_spin.setSuffix("%")
        layout.addRow("Confiança mínima:", self.confidence_spin)
        
        return widget

    def create_overlay_tab(self) -> QWidget:
        """Aba de overlay."""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Tamanho da fonte
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setSuffix(" pt")
        layout.addRow("Tamanho da fonte:", self.font_size_spin)
        
        # Auto-hide
        self.auto_hide_spin = QSpinBox()
        self.auto_hide_spin.setRange(1000, 10000)
        self.auto_hide_spin.setSingleStep(500)
        self.auto_hide_spin.setSuffix(" ms")
        layout.addRow("Auto-esconder após:", self.auto_hide_spin)
        
        return widget

    def load_settings(self):
        """Carrega configurações atuais."""
        # Geral
        self.frame_rate_spin.setValue(self.settings.get('capture.frame_rate', 2))
        self.threshold_spin.setValue(int(self.settings.get('capture.detection_threshold', 0.08) * 100))
        
        # Tradução - Groq
        self.groq_enabled.setChecked(self.settings.get('translation.groq.enabled', True))
        groq_key = self.settings.get_api_key('groq')
        if groq_key:
            self.groq_key.setText(groq_key)
        
        groq_model = self.settings.get('translation.groq.model', 'llama-3.3-70b-versatile')
        index = self.groq_model.findText(groq_model)
        if index >= 0:
            self.groq_model.setCurrentIndex(index)
        
        # Google
        self.google_enabled.setChecked(self.settings.get('translation.google.enabled', True))
        
        # Ollama
        self.ollama_enabled.setChecked(self.settings.get('translation.ollama.enabled', False))
        self.ollama_model.setText(self.settings.get('translation.ollama.model', 'llama3.1'))
        
        # OCR
        langs = self.settings.get('ocr.languages', ['en', 'ko'])
        self.ocr_langs.setText(', '.join(langs))
        self.use_gpu.setChecked(self.settings.get('ocr.use_gpu', False))
        self.confidence_spin.setValue(int(self.settings.get('ocr.confidence_threshold', 0.3) * 100))
        
        # Overlay
        self.font_size_spin.setValue(self.settings.get('overlay.font_size', 14))
        self.auto_hide_spin.setValue(self.settings.get('overlay.auto_hide_ms', 3000))

    def save_settings(self):
        """Salva configurações."""
        # Geral
        self.settings.set('capture.frame_rate', self.frame_rate_spin.value())
        self.settings.set('capture.detection_threshold', self.threshold_spin.value() / 100.0)
        
        # Tradução
        self.settings.set('translation.groq.enabled', self.groq_enabled.isChecked())
        self.settings.set('translation.groq.model', self.groq_model.currentText())
        self.settings.set('translation.google.enabled', self.google_enabled.isChecked())
        self.settings.set('translation.ollama.enabled', self.ollama_enabled.isChecked())
        self.settings.set('translation.ollama.model', self.ollama_model.text())
        
        # OCR
        langs = [lang.strip() for lang in self.ocr_langs.text().split(',')]
        self.settings.set('ocr.languages', langs)
        self.settings.set('ocr.use_gpu', self.use_gpu.isChecked())
        self.settings.set('ocr.confidence_threshold', self.confidence_spin.value() / 100.0)
        
        # Overlay
        self.settings.set('overlay.font_size', self.font_size_spin.value())
        self.settings.set('overlay.auto_hide_ms', self.auto_hide_spin.value())
        
        # Salvar no arquivo
        self.settings.save()
        
        logger.info("Configurações salvas")
        self.accept()
