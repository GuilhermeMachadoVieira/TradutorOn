"""Entry point da aplicação TradutorOn (GUI principal)."""

import sys
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QGroupBox,
    QProgressBar,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from loguru import logger

from src.config.logger import LoggerSetup
from src.config.settings import SettingsManager
from src.gui.area_selector import AreaSelector
from src.gui.translation_overlay import TranslationReplacer
from src.pipeline.worker import PipelineWorker


class SimpleMainWindow(QMainWindow):
    """Janela principal simplificada + pipeline completo."""

    def __init__(self):
        super().__init__()

        # Estado de captura/tradução
        self.selected_area = None
        self.pipeline_worker = None
        self.translation_overlay = None
        self.translation_count = 0
        self.translation_history = []  # histórico em memória
        self.is_running = False

        self.init_ui()
        logger.info("GUI inicializada")

        # Carregar área salva (se houver)
        self.load_saved_area()

        # Timer para atualizar tempo de execução
        self.start_time = datetime.now()
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_runtime)
        self.update_timer.start(1000)  # Atualiza a cada 1 segundo

    def init_ui(self):
        """Inicializa interface."""
        self.setWindowTitle("🌐 TradutorOn - Tradutor de Mangá em Tempo Real")
        self.setMinimumSize(700, 800)

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
        subtitle.setStyleSheet(
            "font-size: 12px; color: #666; padding-bottom: 10px;"
        )
        layout.addWidget(subtitle)

        # Status
        status_group = QGroupBox("📊 Status do Sistema")
        status_layout = QVBoxLayout()

        self.status_label = QLabel("✅ Sistema pronto!")
        self.status_label.setStyleSheet(
            "font-size: 16px; color: green; padding: 10px;"
        )
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.runtime_label = QLabel("⏱️ Tempo de execução: 00:00:00")
        self.runtime_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.runtime_label.setStyleSheet(
            "font-size: 11px; color: #555; padding: 5px;"
        )

        # Estatísticas simples
        stats_hlayout = QHBoxLayout()
        self.translations_label = QLabel("📝 Traduções: 0")
        self.translations_label.setStyleSheet(
            "font-size: 11px; padding: 5px;"
        )

        self.overlays_label = QLabel("👁️ Overlays: 0")
        self.overlays_label.setStyleSheet(
            "font-size: 11px; padding: 5px;"
        )

        self.cache_label = QLabel("💾 Cache: 0")
        self.cache_label.setStyleSheet(
            "font-size: 11px; padding: 5px;"
        )

        self.db_size_label = QLabel("💽 DB: 0.00 MB")
        self.db_size_label.setStyleSheet(
            "font-size: 11px; padding: 5px;"
        )

        stats_hlayout.addWidget(self.translations_label)
        stats_hlayout.addWidget(self.overlays_label)
        stats_hlayout.addWidget(self.cache_label)
        stats_hlayout.addWidget(self.db_size_label)

        info_label = QLabel(
            "🔤 Tradutores: Groq + Google\n"
            "🤖 OCR: PaddleOCR\n"
            "💾 Cache: SQLite\n"
            "🖼️ Captura: MSS + Overlay"
        )
        info_label.setStyleSheet("padding: 10px; font-size: 12px;")

        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.runtime_label)
        status_layout.addLayout(stats_hlayout)
        status_layout.addWidget(info_label)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # Barra de progresso (modo indeterminado)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(0)  # Modo indeterminado
        layout.addWidget(self.progress_bar)

        # Botões de teste / controle
        test_group = QGroupBox("🧪 Controles")
        test_layout = QVBoxLayout()

        # Linha 1: testes básicos
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

        # Botão START/STOP principal
        self.start_full_btn = QPushButton("🚀 Iniciar Modo Completo")
        self.start_full_btn.setMinimumHeight(50)
        self.start_full_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; "
            "font-size: 14px; font-weight: bold;"
        )
        self.start_full_btn.clicked.connect(self.start_full_mode)

        test_layout.addWidget(test_config_btn)
        test_layout.addWidget(test_translators_btn)
        test_layout.addWidget(clear_log_btn)
        test_layout.addWidget(self.start_full_btn)

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
        self.log(
            f"🕐 Iniciado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        )
        self.log("=" * 60)
        self.log("💡 Use os botões acima para testar o sistema")
        self.log("")

    # ------------------------------------------------------------------ #
    # Utilidades de UI / log / tempo
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    # Config / testes rápidos
    # ------------------------------------------------------------------ #

    def test_config(self):
        """Testa configurações básicas."""
        self.log("")
        self.log("⚙️ Testando configurações...")
        self.statusBar().showMessage("⏳ Testando configurações...")

        try:
            settings = SettingsManager()

            # Testar API keys
            groq_key = settings.get_api_key("groq")
            if groq_key:
                self.log(f"✅ Groq API configurada ({len(groq_key)} chars)")
            else:
                self.log("⚠️ Groq API não configurada")

            # Testar configurações principais
            frame_rate = settings.get("capture.frame_rate", 2)
            self.log(f"✅ Frame rate: {frame_rate} fps")

            ocr_lang = settings.get("ocr.languages", ["ja", "en"])
            self.log(f"✅ Idiomas OCR: {', '.join(ocr_lang)}")

            cache_size = settings.get("cache.max_entries", 1000)
            self.log(f"✅ Cache máximo: {cache_size} entradas")

            self.log("✅ Todas configurações OK!")
            self.statusBar().showMessage("✅ Configurações testadas com sucesso")
        except Exception as e:
            self.log(f"❌ Erro ao testar configurações: {e}")
            self.statusBar().showMessage(f"❌ Erro: {e}")
            logger.error(f"Erro ao testar config: {e}")

    def test_translators(self):
        """Testa tradutores (mantido simples)."""
        self.log("")
        self.log("🌐 Testando tradutores...")
        self.log("⏳ Carregando... (pode demorar ~5s)")
        self.statusBar().showMessage("⏳ Testando tradutores...")

        try:
            from src.translation.translator import TranslationService

            settings = SettingsManager()
            groq_key = settings.get_api_key("groq")

            service = TranslationService(
                groq_key=groq_key,
                google_enabled=True,
                ollama_enabled=False,
            )

            # Testar tradução simples
            test_text = "Hello, world!"
            self.log(f"📝 Texto original: '{test_text}'")

            result = service.translate(test_text, "en", "pt")
            self.log(f"✅ Tradução: '{result.translated_text}'")
            self.log(f"✅ Provedor: {result.provider.value}")
            self.log(f"✅ Tempo: {result.processing_time:.2f}s")
            self.log(
                f"✅ Cache: {'Sim' if result.from_cache else 'Não'}"
            )

            self.log("✅ Tradutores funcionando perfeitamente!")
            self.statusBar().showMessage("✅ Tradutores testados com sucesso")
        except Exception as e:
            self.log(f"❌ Erro ao testar tradutores: {e}")
            self.statusBar().showMessage(f"❌ Erro: {e}")
            logger.error(f"Erro ao testar tradutores: {e}")

    # ------------------------------------------------------------------ #
    # Gestão de área / captura
    # ------------------------------------------------------------------ #

    def load_saved_area(self) -> bool:
        """Carrega área salva das configurações, se existir."""
        try:
            settings = SettingsManager()
            saved_area = settings.get("capture.region")
            if saved_area:
                self.selected_area = tuple(saved_area)
                x, y, w, h = self.selected_area
                self.log("")
                self.log("💾 Área salva carregada:")
                self.log(f" 📍 Posição: ({x}, {y})")
                self.log(f" 📐 Tamanho: {w} x {h} px")
                self.log("")
                self.statusBar().showMessage(
                    f"💾 Área carregada: {w}x{h} px"
                )
                return True
        except Exception as e:
            logger.error(f"Erro ao carregar área: {e}")
        return False

    def select_area(self):
        """Abre seletor de área para o modo completo."""
        self.log("")
        self.log("🎯 Selecione a área da tela para traduzir...")
        self.statusBar().showMessage("🎯 Selecione a área da tela")

        self.showMinimized()
        self.area_selector = AreaSelector()
        self.area_selector.area_selected.connect(self.on_area_selected)
        QTimer.singleShot(200, self.area_selector.show)

    def on_area_selected(self, area: tuple):
        """Callback quando área é selecionada."""
        x, y, w, h = area
        self.selected_area = area

        # Salvar nas configurações
        try:
            settings = SettingsManager()
            settings.set("capture.region", list(area))
            settings.save()
            save_msg = "💾 Área salva automaticamente!"
        except Exception as e:
            logger.error(f"Erro ao salvar área: {e}")
            save_msg = "⚠️ Não foi possível salvar área"

        # Restaurar janela
        self.showNormal()
        self.activateWindow()

        # Log
        self.log("=" * 60)
        self.log("✅ Área selecionada com sucesso!")
        self.log(f" 📍 Posição: ({x}, {y})")
        self.log(f" 📐 Tamanho: {w} x {h} px")
        self.log(save_msg)
        self.log("=" * 60)
        self.log("💡 Clique 'Iniciar Modo Completo' para começar!")
        self.log("")
        self.statusBar().showMessage(f"✅ Área selecionada: {w}x{h} px")

        # Auto-iniciar tradução após 1s
        QTimer.singleShot(1000, self.start_translation)

    # ------------------------------------------------------------------ #
    # Controle do modo completo (pipeline + overlay)
    # ------------------------------------------------------------------ #

    def start_full_mode(self):
        """Wrapper do botão principal: inicia ou para o modo completo."""
        if not self.is_running:
            self.start_translation()
        else:
            self.stop_translation()

    def start_translation(self):
        """Inicia tradução em tempo real (pipeline + overlay)."""
        # Se não tem área ainda, abrir seletor e sair; start será retomado em on_area_selected
        if not self.selected_area:
            self.select_area()
            return

        if self.is_running:
            return

        # Log de início
        self.log("")
        self.log("=" * 60)
        self.log("🚀 INICIANDO TRADUÇÃO EM TEMPO REAL")
        self.log("=" * 60)
        x, y, w, h = self.selected_area
        self.log(f"📍 Área: ({x}, {y}) - {w}x{h} px")
        self.log("⏳ Carregando OCR e tradutores...")
        self.log("👁️ Overlay ativo - traduções aparecerão na tela")
        self.log("🔍 Detecção de idioma: ATIVA")
        self.log("🔄 Retry automático: ATIVO")
        self.log("")

        # Criar overlay
        if self.translation_overlay:
            self.translation_overlay.clear_all()
        else:
            self.translation_overlay = TranslationReplacer(self.selected_area)
        self.translation_overlay.show()

        # Atualizar UI
        self.is_running = True
        self.start_full_btn.setText("⏹️ Parar Modo Completo")
        self.start_full_btn.setStyleSheet(
            "background-color: #f44336; color: white; "
            "font-size: 14px; font-weight: bold;"
        )

        self.status_label.setText("🔄 Traduzindo em tempo real...")
        self.status_label.setStyleSheet(
            "font-size: 16px; color: orange; padding: 10px;"
        )

        self.progress_bar.setVisible(True)
        self.statusBar().showMessage("🔄 Pipeline + Overlay rodando...")

        # Minimizar janela
        QTimer.singleShot(500, self.showMinimized)

        # Iniciar worker
        try:
            settings = SettingsManager()
            self.pipeline_worker = PipelineWorker(self.selected_area, settings)
            self.pipeline_worker.translation_received.connect(
                self.on_translation_result
            )
            self.pipeline_worker.stats_updated.connect(self.on_stats_update)
            self.pipeline_worker.error_occurred.connect(
                self.on_pipeline_error
            )
            self.pipeline_worker.start()
        except Exception as e:
            self.log(f"❌ Erro ao iniciar pipeline: {e}")
            logger.error(f"Erro ao iniciar pipeline: {e}")
            self.stop_translation()

    def stop_translation(self):
        """Para tradução em tempo real."""
        self.log("")
        self.log("🛑 Parando tradução...")

        # Parar worker
        if self.pipeline_worker:
            try:
                self.pipeline_worker.stop()
            except Exception as e:
                logger.error(f"Erro ao parar worker: {e}")
            self.pipeline_worker = None

        # Limpar overlay
        if self.translation_overlay:
            self.translation_overlay.clear_all()

        # Atualizar UI
        self.is_running = False
        self.start_full_btn.setText("🚀 Iniciar Modo Completo")
        self.start_full_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; "
            "font-size: 14px; font-weight: bold;"
        )

        self.status_label.setText("✅ Sistema pronto!")
        self.status_label.setStyleSheet(
            "font-size: 16px; color: green; padding: 10px;"
        )

        self.progress_bar.setVisible(False)
        self.statusBar().showMessage("✅ Pipeline parado")

        # Restaurar janela
        self.showNormal()
        self.activateWindow()

        self.log("✅ Tradução parada!")
        self.log(f"📊 Total de traduções: {self.translation_count}")
        self.log(f"📚 Histórico: {len(self.translation_history)} itens")
        self.log("")

    # ------------------------------------------------------------------ #
    # Callbacks do worker (traduções / stats / erros)
    # ------------------------------------------------------------------ #

    def on_translation_result(self, result: dict):
        """Callback quando recebe tradução normalizada do PipelineWorker."""
        try:
            self.translation_count += 1

            original = result.get("original", "")
            translated = result.get("translated", "")
            confidence = result.get("confidence", 0) * 100
            language = result.get("language", "?")
            bbox = result.get("bbox")
            provider = result.get("provider", "?")

            # Adicionar ao histórico em memória
            history_item = {
                "timestamp": result.get(
                    "timestamp", datetime.now().strftime("%H:%M:%S")
                ),
                "original": original,
                "translated": translated,
                "language": language,
                "provider": provider,
                "confidence": confidence,
            }
            self.translation_history.append(history_item)
            if len(self.translation_history) > 1000:
                self.translation_history.pop(0)

            # Log detalhado
            self.log(
                f"📝 #{self.translation_count} [{language.upper()}] "
                f"{original[:50]}..."
            )
            self.log(f" → {translated[:80]}")
            self.log(
                f" Confiança: {confidence:.1f}% | Provedor: {provider}"
            )

            # Mostrar no overlay
            if self.translation_overlay and bbox:
                self.translation_overlay.show_translation(result)
                self.overlays_label.setText(
                    f"👁️ Overlays: {self.translation_count}"
                )
                self.log(" ✅ Overlay exibido")
            else:
                if not bbox:
                    self.log(" ⚠️ Sem bbox - overlay não exibido")

            # Atualizar contador de traduções
            self.translations_label.setText(
                f"📝 Traduções: {self.translation_count}"
            )
        except Exception as e:
            logger.error(f"Erro ao processar resultado: {e}")
            self.log(f" ❌ Erro: {e}")

    def on_stats_update(self, stats: dict):
        """Atualiza estatísticas básicas na UI."""
        cache_stats = stats.get("cache", {})
        total_cache = cache_stats.get("total_translations", 0)
        db_size = cache_stats.get("db_size_mb", 0.0)

        self.cache_label.setText(f"💾 Cache: {total_cache}")
        self.db_size_label.setText(f"💽 DB: {db_size:.2f} MB")

    def on_pipeline_error(self, error: str):
        """Trata erros do pipeline."""
        self.log(f"❌ ERRO: {error}")
        self.stop_translation()

    # ------------------------------------------------------------------ #
    # Fechamento seguro
    # ------------------------------------------------------------------ #

    def closeEvent(self, event):
        """Ao fechar janela, garantir que o pipeline foi parado e overlay limpo."""
        if self.is_running:
            self.stop_translation()
        if self.translation_overlay:
            self.translation_overlay.clear_all()
        event.accept()


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
