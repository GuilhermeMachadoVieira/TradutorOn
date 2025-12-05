"""
Janela principal da aplicação.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QGroupBox, QTextEdit,
    QStatusBar, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QFont
from loguru import logger

from src.config.settings import SettingsManager
from src.pipeline.processor import ProcessingPipeline
from src.gui.area_selector import AreaSelector
from src.gui.overlay import TranslationOverlay
from src.gui.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    """Janela principal do Manga Translator Pro."""

    def __init__(self):
        super().__init__()
        
        self.settings = SettingsManager()
        self.pipeline = None
        self.overlay = None
        self.selected_area = None
        self.is_running = False
        
        self.init_ui()
        self.setup_shortcuts()
        
        logger.info("MainWindow inicializada")

    def init_ui(self):
        """Inicializa interface do usuário."""
        self.setWindowTitle("Manga Translator Pro")
        self.setMinimumSize(450, 600)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Título
        title = QLabel("🌐 Manga Translator Pro")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Status
        self.status_group = self.create_status_group()
        layout.addWidget(self.status_group)
        
        # Área de captura
        self.area_group = self.create_area_group()
        layout.addWidget(self.area_group)
        
        # Controles
        self.controls_group = self.create_controls_group()
        layout.addWidget(self.controls_group)
        
        # Log
        self.log_group = self.create_log_group()
        layout.addWidget(self.log_group)
        
        # Status bar
        self.statusBar().showMessage("Pronto")
        
        # Timer para atualizar stats
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(1000)  # Atualizar a cada 1s

    def create_status_group(self) -> QGroupBox:
        """Cria grupo de status."""
        group = QGroupBox("📊 Status")
        layout = QVBoxLayout()
        
        self.status_label = QLabel("⚫ Parado")
        self.status_label.setStyleSheet("font-size: 14px; padding: 5px;")
        
        self.language_label = QLabel("🔤 Idioma: EN → PT")
        self.translator_label = QLabel("🤖 Tradutor: Groq")
        self.cache_label = QLabel("💾 Cache: 0 traduções")
        
        layout.addWidget(self.status_label)
        layout.addWidget(self.language_label)
        layout.addWidget(self.translator_label)
        layout.addWidget(self.cache_label)
        
        group.setLayout(layout)
        return group

    def create_area_group(self) -> QGroupBox:
        """Cria grupo de seleção de área."""
        group = QGroupBox("📐 Área de Captura")
        layout = QVBoxLayout()
        
        self.area_label = QLabel("Nenhuma área selecionada")
        self.area_label.setStyleSheet("padding: 10px; background: #f0f0f0; border-radius: 5px;")
        self.area_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.select_area_btn = QPushButton("🎯 Selecionar Área")
        self.select_area_btn.clicked.connect(self.select_area)
        self.select_area_btn.setMinimumHeight(40)
        
        layout.addWidget(self.area_label)
        layout.addWidget(self.select_area_btn)
        
        group.setLayout(layout)
        return group

    def create_controls_group(self) -> QGroupBox:
        """Cria grupo de controles."""
        group = QGroupBox("🎮 Controles")
        layout = QVBoxLayout()
        
        # Botões principais
        self.start_btn = QPushButton("▶ Iniciar Tradução")
        self.start_btn.setMinimumHeight(45)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-size: 14px; font-weight: bold;")
        self.start_btn.clicked.connect(self.start_translation)
        
        self.pause_btn = QPushButton("⏸ Pausar")
        self.pause_btn.setMinimumHeight(40)
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.pause_translation)
        
        self.stop_btn = QPushButton("⏹ Parar")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_translation)
        
        # Botões secundários
        btn_layout = QHBoxLayout()
        
        self.settings_btn = QPushButton("⚙️ Configurações")
        self.settings_btn.clicked.connect(self.show_settings)
        
        self.clear_cache_btn = QPushButton("🗑️ Limpar Cache")
        self.clear_cache_btn.clicked.connect(self.clear_cache)
        
        btn_layout.addWidget(self.settings_btn)
        btn_layout.addWidget(self.clear_cache_btn)
        
        layout.addWidget(self.start_btn)
        layout.addWidget(self.pause_btn)
        layout.addWidget(self.stop_btn)
        layout.addLayout(btn_layout)
        
        group.setLayout(layout)
        return group

    def create_log_group(self) -> QGroupBox:
        """Cria grupo de log."""
        group = QGroupBox("📝 Log")
        layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("background: #1e1e1e; color: #00ff00; font-family: 'Courier New';")
        
        layout.addWidget(self.log_text)
        group.setLayout(layout)
        return group

    def setup_shortcuts(self):
        """Configura atalhos de teclado."""
        from PyQt6.QtGui import QShortcut, QKeySequence
        
        # F5 - Iniciar/Parar
        QShortcut(QKeySequence("F5"), self).activated.connect(self.toggle_translation)
        
        # F6 - Selecionar área
        QShortcut(QKeySequence("F6"), self).activated.connect(self.select_area)
        
        # ESC - Parar
        QShortcut(QKeySequence("Esc"), self).activated.connect(self.stop_translation)

    def select_area(self):
        """Abre seletor de área."""
        self.log("Abrindo seletor de área...")
        
        selector = AreaSelector()
        if selector.exec():
            self.selected_area = selector.get_selected_area()
            
            if self.selected_area:
                w = self.selected_area.width
                h = self.selected_area.height
                self.area_label.setText(f"✅ Área: {w}x{h} px")
                self.log(f"Área selecionada: {w}x{h} px")
            else:
                self.area_label.setText("❌ Seleção cancelada")

    def start_translation(self):
        """Inicia tradução."""
        if not self.selected_area:
            self.log("❌ Selecione uma área primeiro!")
            return
        
        self.log("▶ Iniciando tradução...")
        
        # Criar pipeline
        self.pipeline = ProcessingPipeline(
            settings_manager=self.settings,
            on_result_callback=self.on_translation_result,
            num_ocr_workers=2
        )
        
        # Criar overlay
        self.overlay = TranslationOverlay()
        self.overlay.show()
        
        # Iniciar
        self.pipeline.start(self.selected_area)
        self.is_running = True
        
        # Atualizar UI
        self.status_label.setText("🟢 Rodando")
        self.status_label.setStyleSheet("font-size: 14px; padding: 5px; color: green; font-weight: bold;")
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.select_area_btn.setEnabled(False)
        
        self.statusBar().showMessage("Tradução em andamento...")
        self.log("✅ Pipeline iniciada!")

    def pause_translation(self):
        """Pausa tradução."""
        # TODO: Implementar pausa
        self.log("⏸ Pausado (não implementado ainda)")

    def stop_translation(self):
        """Para tradução."""
        if not self.pipeline:
            return
        
        self.log("⏹ Parando tradução...")
        
        # Parar pipeline
        self.pipeline.stop()
        self.pipeline = None
        
        # Fechar overlay
        if self.overlay:
            self.overlay.close()
            self.overlay = None
        
        self.is_running = False
        
        # Atualizar UI
        self.status_label.setText("⚫ Parado")
        self.status_label.setStyleSheet("font-size: 14px; padding: 5px;")
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.select_area_btn.setEnabled(True)
        
        self.statusBar().showMessage("Pronto")
        self.log("✅ Pipeline parada")

    def toggle_translation(self):
        """Alterna entre iniciar/parar."""
        if self.is_running:
            self.stop_translation()
        else:
            self.start_translation()

    def on_translation_result(self, results):
        """Callback de resultados de tradução."""
        if not results:
            return
        
        for result in results:
            # Atualizar overlay
            if self.overlay:
                self.overlay.add_translation(
                    bbox=result['bbox'],
                    original=result['original'],
                    translated=result['translated']
                )
            
            # Log
            self.log(f"📝 {result['original']} → {result['translated']}")

    def update_stats(self):
        """Atualiza estatísticas."""
        if self.pipeline:
            stats = self.pipeline.get_stats()
            
            cache_stats = stats.get('cache', {})
            total = cache_stats.get('total_translations', 0)
            size_mb = cache_stats.get('db_size_mb', 0)
            
            self.cache_label.setText(f"💾 Cache: {total} traduções ({size_mb:.2f} MB)")
            
            translators = stats.get('translators', [])
            if translators:
                self.translator_label.setText(f"🤖 Tradutor: {translators[0]}")

    def show_settings(self):
        """Mostra diálogo de configurações."""
        dialog = SettingsDialog(self.settings, self)
        dialog.exec()

    def clear_cache(self):
        """Limpa cache."""
        # TODO: Implementar limpeza de cache
        self.log("🗑️ Limpando cache...")

    def log(self, message: str):
        """Adiciona mensagem ao log."""
        self.log_text.append(f"> {message}")
        # Auto-scroll
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def closeEvent(self, event):
        """Evento de fechamento."""
        if self.is_running:
            self.stop_translation()
        event.accept()
