"""Entry point da aplicação TradutorOn."""
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLabel, QPushButton, QTextEdit, QGroupBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from loguru import logger
from datetime import datetime
from src.config.logger import LoggerSetup


class SimpleMainWindow(QMainWindow):
    """Janela principal simplificada."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        logger.info("GUI inicializada")
        
        # Timer para atualizar tempo de execução
        self.start_time = datetime.now()
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_runtime)
        self.update_timer.start(1000)  # Atualiza a cada 1 segundo
        
    def init_ui(self):
        """Inicializa interface."""
        self.setWindowTitle("🌐 TradutorOn - Tradutor de Mangá em Tempo Real")
        self.setMinimumSize(600, 700)
        
        # Widget central
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Título
        title = QLabel("🌐 TradutorOn")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("padding: 15px; color: #2196F3;")
        layout.addWidget(title)
        
        subtitle = QLabel("Tradutor de Mangá em Tempo Real")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 12px; color: #666; padding-bottom: 10px;")
        layout.addWidget(subtitle)
        
        # Status
        status_group = QGroupBox("📊 Status do Sistema")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("✅ Sistema pronto!")
        self.status_label.setStyleSheet("font-size: 16px; color: green; padding: 10px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.runtime_label = QLabel("⏱️ Tempo de execução: 00:00:00")
        self.runtime_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.runtime_label.setStyleSheet("font-size: 11px; color: #555; padding: 5px;")
        
        info_label = QLabel(
            "🔤 Tradutores: Groq + Google\n"
            "🤖 OCR: PaddleOCR\n"
            "💾 Cache: SQLite\n"
            "🖼️ Captura: MSS"
        )
        info_label.setStyleSheet("padding: 10px; font-size: 12px;")
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.runtime_label)
        status_layout.addWidget(info_label)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Botões de teste
        test_group = QGroupBox("🧪 Testes Rápidos")
        test_layout = QVBoxLayout()
        
        test_config_btn = QPushButton("⚙️ Testar Configurações")
        test_config_btn.setMinimumHeight(40)
        test_config_btn.clicked.connect(self.test_config)
        test_config_btn.setStyleSheet("font-size: 13px;")
        
        test_translators_btn = QPushButton("🌐 Testar Tradutores")
        test_translators_btn.setMinimumHeight(40)
        test_translators_btn.clicked.connect(self.test_translators)
        test_translators_btn.setStyleSheet("font-size: 13px;")
        
        clear_log_btn = QPushButton("🗑️ Limpar Log")
        clear_log_btn.setMinimumHeight(35)
        clear_log_btn.clicked.connect(self.clear_log)
        clear_log_btn.setStyleSheet("font-size: 12px;")
        
        start_full_btn = QPushButton("🚀 Iniciar Modo Completo")
        start_full_btn.setMinimumHeight(50)
        start_full_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; "
            "font-size: 14px; font-weight: bold;"
        )
        start_full_btn.clicked.connect(self.start_full_mode)
        
        test_layout.addWidget(test_config_btn)
        test_layout.addWidget(test_translators_btn)
        test_layout.addWidget(clear_log_btn)
        test_layout.addWidget(start_full_btn)
        test_group.setLayout(test_layout)
        layout.addWidget(test_group)
        
        # Log
        log_group = QGroupBox("📝 Log do Sistema")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        self.log_text.setStyleSheet(
            "background: #1e1e1e; color: #00ff00; "
            "font-family: 'Courier New'; font-size: 11px; padding: 8px;"
        )
        
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # Status bar
        self.statusBar().showMessage("✅ Pronto para iniciar")
        
        # Log inicial
        self.log("=" * 60)
        self.log("✅ TradutorOn GUI carregada com sucesso!")
        self.log(f"🕐 Iniciado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        self.log("=" * 60)
        self.log("💡 Use os botões acima para testar o sistema")
        self.log("")
        
    def log(self, message: str):
        """Adiciona mensagem ao log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        # Auto-scroll para o final
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
        
    def clear_log(self):
        """Limpa o log."""
        self.log_text.clear()
        self.log("🗑️ Log limpo!")
        
    def update_runtime(self):
        """Atualiza tempo de execução."""
        elapsed = datetime.now() - self.start_time
        hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        self.runtime_label.setText(
            f"⏱️ Tempo de execução: {hours:02d}:{minutes:02d}:{seconds:02d}"
        )
        
    def test_config(self):
        """Testa configurações."""
        self.log("")
        self.log("⚙️ Testando configurações...")
        self.statusBar().showMessage("⏳ Testando configurações...")
        
        try:
            from src.config.settings import SettingsManager
            settings = SettingsManager()
            
            # Testar API keys
            groq_key = settings.get_api_key('groq')
            if groq_key:
                self.log(f"✅ Groq API configurada ({len(groq_key)} chars)")
            else:
                self.log("⚠️ Groq API não configurada")
            
            # Testar configurações
            frame_rate = settings.get('capture.frame_rate', 2)
            self.log(f"✅ Frame rate: {frame_rate} fps")
            
            ocr_lang = settings.get('ocr.languages', ['ja', 'en'])
            self.log(f"✅ Idiomas OCR: {', '.join(ocr_lang)}")
            
            cache_size = settings.get('cache.max_entries', 1000)
            self.log(f"✅ Cache máximo: {cache_size} entradas")
            
            self.log("✅ Todas configurações OK!")
            self.statusBar().showMessage("✅ Configurações testadas com sucesso")
            
        except Exception as e:
            self.log(f"❌ Erro ao testar configurações: {e}")
            self.statusBar().showMessage(f"❌ Erro: {e}")
            logger.error(f"Erro ao testar config: {e}")
            
    def test_translators(self):
        """Testa tradutores."""
        self.log("")
        self.log("🌐 Testando tradutores...")
        self.log("⏳ Carregando... (pode demorar ~5s)")
        self.statusBar().showMessage("⏳ Testando tradutores...")
        
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
            
            # Testar tradução simples
            test_text = "Hello, world!"
            self.log(f"📝 Texto original: '{test_text}'")
            
            result = service.translate(test_text, "en", "pt")
            
            self.log(f"✅ Tradução: '{result.translated_text}'")
            self.log(f"✅ Provedor: {result.provider.value}")
            self.log(f"✅ Tempo: {result.processing_time:.2f}s")
            self.log(f"✅ Cache: {'Sim' if result.from_cache else 'Não'}")
            self.log("✅ Tradutores funcionando perfeitamente!")
            
            self.statusBar().showMessage("✅ Tradutores testados com sucesso")
            
        except Exception as e:
            self.log(f"❌ Erro ao testar tradutores: {e}")
            self.statusBar().showMessage(f"❌ Erro: {e}")
            logger.error(f"Erro ao testar tradutores: {e}")
            
    def start_full_mode(self):
        """Inicia modo completo (com OCR)."""
        self.log("")
        self.log("🚀 Iniciando modo completo...")
        self.log("⚠️ Modo completo será implementado na FASE 1.2+")
        self.log("💡 Aguarde as próximas atualizações!")
        self.statusBar().showMessage("⚠️ Modo completo em desenvolvimento")


def main():
    """Função principal."""
    # Inicializar logger
    LoggerSetup.initialize(level="INFO")
    
    logger.info("=" * 60)
    logger.info("TRADUTOR ON - GUI INICIANDO")
    logger.info("=" * 60)
    
    # Criar aplicação
    app = QApplication(sys.argv)
    app.setApplicationName("TradutorOn")
    app.setStyle("Fusion")
    
    # Criar janela
    window = SimpleMainWindow()
    window.show()
    
    logger.info("✅ Aplicação iniciada com sucesso")
    
    # Executar
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
