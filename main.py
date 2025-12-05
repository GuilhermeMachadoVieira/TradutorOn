"""
Entry point da aplicação Manga Translator Pro.
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QLabel, QPushButton, QTextEdit, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from loguru import logger

from src.config.logger import LoggerSetup


class SimpleMainWindow(QMainWindow):
    """Janela principal simplificada."""

    def __init__(self):
        super().__init__()
        self.init_ui()
        logger.info("GUI inicializada")

    def init_ui(self):
        """Inicializa interface."""
        self.setWindowTitle("Manga Translator Pro")
        self.setMinimumSize(500, 600)
        
        # Widget central
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título
        title = QLabel("🌐 Manga Translator Pro")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("padding: 20px; color: #2196F3;")
        layout.addWidget(title)
        
        # Status
        status_group = QGroupBox("📊 Status do Sistema")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("✅ Sistema pronto!")
        self.status_label.setStyleSheet("font-size: 16px; color: green; padding: 10px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        info_label = QLabel(
            "🔤 Tradutores: Groq + Google\n"
            "🤖 OCR: PaddleOCR\n"
            "💾 Cache: SQLite"
        )
        info_label.setStyleSheet("padding: 10px; font-size: 12px;")
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(info_label)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Botões de teste
        test_group = QGroupBox("🧪 Testes Rápidos")
        test_layout = QVBoxLayout()
        
        test_config_btn = QPushButton("⚙️ Testar Configurações")
        test_config_btn.setMinimumHeight(40)
        test_config_btn.clicked.connect(self.test_config)
        
        test_translators_btn = QPushButton("🌐 Testar Tradutores")
        test_translators_btn.setMinimumHeight(40)
        test_translators_btn.clicked.connect(self.test_translators)
        
        start_full_btn = QPushButton("🚀 Iniciar Modo Completo")
        start_full_btn.setMinimumHeight(50)
        start_full_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; "
            "font-size: 14px; font-weight: bold;"
        )
        start_full_btn.clicked.connect(self.start_full_mode)
        
        test_layout.addWidget(test_config_btn)
        test_layout.addWidget(test_translators_btn)
        test_layout.addWidget(start_full_btn)
        test_group.setLayout(test_layout)
        layout.addWidget(test_group)
        
        # Log
        log_group = QGroupBox("📝 Log")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet(
            "background: #1e1e1e; color: #00ff00; "
            "font-family: 'Courier New'; padding: 5px;"
        )
        
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # Status bar
        self.statusBar().showMessage("Pronto para iniciar")
        
        self.log("✅ GUI carregada com sucesso!")
        self.log("💡 Use os botões acima para testar o sistema")

    def log(self, message: str):
        """Adiciona mensagem ao log."""
        self.log_text.append(f"> {message}")
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def test_config(self):
        """Testa configurações."""
        self.log("⚙️ Testando configurações...")
        try:
            from src.config.settings import SettingsManager
            settings = SettingsManager()
            
            groq_key = settings.get_api_key('groq')
            frame_rate = settings.get('capture.frame_rate', 2)
            
            if groq_key:
                self.log(f"✅ Groq API configurada")
            else:
                self.log("⚠️ Groq API não configurada")
            
            self.log(f"✅ Frame rate: {frame_rate} fps")
            self.log("✅ Configurações OK!")
            
        except Exception as e:
            self.log(f"❌ Erro: {e}")

    def test_translators(self):
        """Testa tradutores."""
        self.log("🌐 Testando tradutores...")
        self.log("⏳ Carregando... (pode demorar ~5s)")
        
        try:
            from src.config.settings import SettingsManager
            from src.translation.translator import TranslationService
            
            settings = SettingsManager()
            groq_key = settings.get_api_key('groq')
            
            service = TranslationService(
                groq_key=groq_key,
                google_enabled=True,
                ollama_enabled=False
            )
            
            # Testar tradução
            result = service.translate("Hello", "en", "pt")
            
            self.log(f"✅ Tradução: 'Hello' → '{result.translated_text}'")
            self.log(f"✅ Provedor usado: {result.provider.value}")
            self.log("✅ Tradutores funcionando!")
            
        except Exception as e:
            self.log(f"❌ Erro: {e}")

    def start_full_mode(self):
        """Inicia modo completo (com OCR)."""
        self.log("🚀 Iniciando modo completo...")
        self.log("⏳ Carregando PaddleOCR... (demora ~30s)")
        self.log("💡 Aguarde, não travou!")
        
        # Desabilitar botão
        sender = self.sender()
        sender.setEnabled(False)
        sender.setText("⏳ Carregando...")
        
        # TODO: Carregar em thread separada
        self.log("⚠️ Modo completo ainda não implementado")
        self.log("💡 Use 'python example_usage.py' por enquanto")


def main():
    """Função principal."""
    # Inicializar logger
    LoggerSetup.initialize(level="INFO")
    logger.info("="*60)
    logger.info("MANGA TRANSLATOR PRO - GUI RÁPIDA")
    logger.info("="*60)
    
    # Criar aplicação
    app = QApplication(sys.argv)
    app.setApplicationName("Manga Translator Pro")
    app.setStyle("Fusion")
    
    # Criar janela
    window = SimpleMainWindow()
    window.show()
    
    logger.info("✅ Aplicação iniciada")
    
    # Executar
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
