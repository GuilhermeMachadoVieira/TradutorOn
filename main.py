"""Entry point da aplicação TradutorOn."""
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QGroupBox, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from loguru import logger
from datetime import datetime
from src.config.logger import LoggerSetup
from src.gui.area_selector import AreaSelector
from src.gui.translation_overlay import TranslationReplacer
from src.gui.settings_dialog import SettingsDialog
from src.gui.translation_history import TranslationHistoryDialog
from src.utils.language_detector import LanguageDetector
from src.utils.text_grouper import TextGrouper


class PipelineWorker(QThread):
    """Worker thread para rodar pipeline sem travar GUI."""
    
    # Signals
    translation_received = pyqtSignal(dict)  # Resultado individual
    stats_updated = pyqtSignal(dict)  # Estatísticas
    error_occurred = pyqtSignal(str)  # Erros
    
    def __init__(self, area: tuple, settings_manager):
        super().__init__()
        self.area = area
        self.settings_manager = settings_manager
        self.pipeline = None
        self.running = False
        self.result_count = 0
        
        # Utilidades
        self.lang_detector = LanguageDetector()
        self.text_grouper = TextGrouper(
            max_distance=settings_manager.get('translation.group_distance', 50)
        )
        
        # Cache de resultados recentes para evitar duplicatas
        self.recent_results = {}
        self.last_emission_time = {}
        
    def run(self):
        """Executa pipeline em thread separada."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                from src.pipeline.processor import ProcessingPipeline
                from src.utils.types import ScreenArea
                
                x, y, w, h = self.area
                
                # Criar área
                screen_area = ScreenArea(
                    x1=x,
                    y1=y,
                    x2=x + w,
                    y2=y + h,
                    monitor_index=0
                )
                
                # Criar pipeline
                self.pipeline = ProcessingPipeline(
                    settings_manager=self.settings_manager,
                    on_result_callback=self._on_translation,
                    num_ocr_workers=2
                )
                
                # Iniciar
                self.pipeline.start(screen_area)
                self.running = True
                
                logger.info("✅ Pipeline worker iniciado")
                
                # Loop de estatísticas e limpeza (a cada 2 segundos)
                while self.running:
                    self.msleep(2000)
                    if self.pipeline and self.running:
                        stats = self.pipeline.get_stats()
                        self.stats_updated.emit(stats)
                        
                        # Limpar cache antigo
                        self._cleanup_old_cache()
                        
                # Se chegou aqui, saiu normalmente
                break
                    
            except Exception as e:
                retry_count += 1
                logger.error(f"Erro no pipeline worker (tentativa {retry_count}/{max_retries}): {e}")
                
                if retry_count < max_retries:
                    logger.info(f"🔄 Tentando novamente em 2 segundos...")
                    self.msleep(2000)
                else:
                    self.error_occurred.emit(f"Falha após {max_retries} tentativas: {str(e)}")
                    
    def _on_translation(self, results):
        """Callback de tradução."""
        try:
            if not results:
                return
                
            logger.debug(f"📦 Pipeline retornou {len(results)} resultados")
            
            # Results pode ser uma lista
            if isinstance(results, list):
                # Agrupar se configurado
                if self.settings_manager.get('translation.group_nearby', False):
                    results = self.text_grouper.group_results(results)
                    
                for result in results:
                    self._process_single_result(result)
            else:
                self._process_single_result(results)
                
        except Exception as e:
            logger.error(f"Erro ao processar resultados: {e}")
            
    def _process_single_result(self, result):
        """Processa um único resultado."""
        try:
            # Verificar se resultado é válido
            if not result or not isinstance(result, dict):
                logger.debug(f"⚠️ Resultado inválido: {type(result)}")
                return
            
            # Extrair campos
            original = result.get('original', result.get('text', ''))
            translated = result.get('translated', result.get('translation', ''))
            
            if not original or not translated:
                return
                
            # Criar chave única para este resultado
            result_key = self._make_result_key(original, translated)
            
            # Verificar se já processamos este resultado recentemente
            if self._is_recent_duplicate(result_key):
                logger.debug(f"⚠️ Resultado duplicado ignorado: '{translated[:30]}'")
                return
                
            # Registrar resultado
            self.recent_results[result_key] = datetime.now()
            self.last_emission_time[result_key] = datetime.now()
                
            self.result_count += 1
            
            # Log detalhado para debug
            logger.debug(f"🔍 Resultado #{self.result_count}: {result.keys()}")
            
            # Detecção de idioma se habilitado
            language = result.get('language', '')
            if self.settings_manager.get('translation.auto_detect', True) and not language:
                language = self.lang_detector.detect(original)
                logger.debug(f"🔍 Idioma detectado: {language}")
            
            # Bbox pode vir em diferentes formatos
            bbox = None
            if 'bbox' in result:
                bbox = result['bbox']
            elif 'bounding_box' in result:
                bbox = result['bounding_box']
            elif 'box' in result:
                bbox = result['box']
                
            # Se não tem bbox, criar um genérico
            if not bbox:
                logger.warning(f"⚠️ Resultado sem bbox")
                return  # NÃO criar overlay sem bbox
            
            # Montar resultado normalizado
            normalized = {
                'original': original,
                'translated': translated,
                'bbox': bbox,
                'confidence': result.get('confidence', 1.0),
                'language': language,
                'provider': result.get('provider', 'unknown'),
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }
            
            logger.debug(f"✅ Emitindo: orig='{original[:30]}', trans='{translated[:30]}', lang={language}")
            
            self.translation_received.emit(normalized)
                
        except Exception as e:
            logger.error(f"Erro ao processar resultado individual: {e}")
            
    def _make_result_key(self, original: str, translated: str) -> str:
        """Cria chave única para resultado."""
        # Normalizar texto (lowercase, sem espaços extras)
        orig_normalized = original.lower().strip()
        trans_normalized = translated.lower().strip()
        return f"{orig_normalized}||{trans_normalized}"
        
    def _is_recent_duplicate(self, result_key: str) -> bool:
        """Verifica se resultado é duplicata recente."""
        if result_key not in self.recent_results:
            return False
            
        # Verificar idade
        age = datetime.now() - self.recent_results[result_key]
        
        # Considerar duplicata se foi processado nos últimos 3 segundos
        if age.total_seconds() < 3.0:
            return True
            
        # Verificar cooldown de emissão (mínimo 2 segundos entre emissões)
        if result_key in self.last_emission_time:
            last_emission_age = datetime.now() - self.last_emission_time[result_key]
            if last_emission_age.total_seconds() < 2.0:
                return True
                
        return False
        
    def _cleanup_old_cache(self):
        """Remove entradas antigas do cache."""
        now = datetime.now()
        
        # Limpar recent_results
        expired_keys = []
        for key, timestamp in self.recent_results.items():
            age = now - timestamp
            if age.total_seconds() > 10.0:  # Manter por 10 segundos
                expired_keys.append(key)
                
        for key in expired_keys:
            del self.recent_results[key]
            if key in self.last_emission_time:
                del self.last_emission_time[key]
                
        if expired_keys:
            logger.debug(f"🗑️ Cache worker limpo: {len(expired_keys)} entradas")
            
    def stop(self):
        """Para pipeline."""
        self.running = False
        if self.pipeline:
            try:
                self.pipeline.stop()
            except Exception as e:
                logger.error(f"Erro ao parar pipeline: {e}")
        self.quit()
        self.wait()


class SimpleMainWindow(QMainWindow):
    """Janela principal simplificada."""
    
    def __init__(self):
        super().__init__()
        self.selected_area = None
        self.pipeline_worker = None
        self.translation_overlay = None
        self.translation_count = 0
        self.is_running = False
        self.translation_history = []  # Histórico de traduções
        self.init_ui()
        logger.info("GUI inicializada")
        
        # Carregar área salva
        self.load_saved_area()
        
        # Timer para atualizar tempo de execução
        self.start_time = datetime.now()
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_runtime)
        self.update_timer.start(1000)
        
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
        
        subtitle = QLabel("Tradutor de Mangá em Tempo Real v2.0")
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
        
        # Estatísticas em tempo real
        stats_hlayout = QHBoxLayout()
        
        self.translations_label = QLabel("📝 Traduções: 0")
        self.translations_label.setStyleSheet("font-size: 11px; padding: 5px;")
        
        self.overlays_label = QLabel("👁️ Overlays: 0")
        self.overlays_label.setStyleSheet("font-size: 11px; padding: 5px;")
        
        self.cache_label = QLabel("💾 Cache: 0")
        self.cache_label.setStyleSheet("font-size: 11px; padding: 5px;")
        
        self.db_size_label = QLabel("💽 DB: 0.00 MB")
        self.db_size_label.setStyleSheet("font-size: 11px; padding: 5px;")
        
        stats_hlayout.addWidget(self.translations_label)
        stats_hlayout.addWidget(self.overlays_label)
        stats_hlayout.addWidget(self.cache_label)
        stats_hlayout.addWidget(self.db_size_label)
        
        info_label = QLabel(
            "🔤 Tradutores: Groq + Google\n"
            "🤖 OCR: PaddleOCR\n"
            "💾 Cache: SQLite\n"
            "🖼️ Captura: MSS + Overlay\n"
            "🔍 Detecção: Auto idioma + Agrupamento"
        )
        info_label.setStyleSheet("padding: 10px; font-size: 11px;")
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.runtime_label)
        status_layout.addLayout(stats_hlayout)
        status_layout.addWidget(info_label)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(0)  # Modo indeterminado
        layout.addWidget(self.progress_bar)
        
        # Botões de teste
        test_group = QGroupBox("🧪 Controles")
        test_layout = QVBoxLayout()
        
        # Linha 1
        row1 = QHBoxLayout()
        
        test_config_btn = QPushButton("⚙️ Testar Config")
        test_config_btn.setMinimumHeight(40)
        test_config_btn.clicked.connect(self.test_config)
        
        test_translators_btn = QPushButton("🌐 Testar Tradutores")
        test_translators_btn.setMinimumHeight(40)
        test_translators_btn.clicked.connect(self.test_translators)
        
        test_overlay_btn = QPushButton("👁️ Testar Overlay")
        test_overlay_btn.setMinimumHeight(40)
        test_overlay_btn.clicked.connect(self.test_overlay)
        
        row1.addWidget(test_config_btn)
        row1.addWidget(test_translators_btn)
        row1.addWidget(test_overlay_btn)
        
        # Linha 2
        row2 = QHBoxLayout()
        
        settings_btn = QPushButton("⚙️ Configurações")
        settings_btn.setMinimumHeight(40)
        settings_btn.clicked.connect(self.open_settings)
        
        history_btn = QPushButton("📚 Histórico")
        history_btn.setMinimumHeight(40)
        history_btn.clicked.connect(self.open_history)
        
        clear_area_btn = QPushButton("🗑️ Limpar Área")
        clear_area_btn.setMinimumHeight(40)
        clear_area_btn.clicked.connect(self.clear_saved_area)
        
        row2.addWidget(settings_btn)
        row2.addWidget(history_btn)
        row2.addWidget(clear_area_btn)
        
        # Linha 3
        clear_log_btn = QPushButton("🗑️ Limpar Log")
        clear_log_btn.setMinimumHeight(35)
        clear_log_btn.clicked.connect(self.clear_log)
        
        # Botão START/STOP dinâmico
        self.start_stop_btn = QPushButton("🚀 Iniciar Tradução")
        self.start_stop_btn.setMinimumHeight(50)
        self.start_stop_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; "
            "font-size: 14px; font-weight: bold;"
        )
        self.start_stop_btn.clicked.connect(self.toggle_translation)
        
        test_layout.addLayout(row1)
        test_layout.addLayout(row2)
        test_layout.addWidget(clear_log_btn)
        test_layout.addWidget(self.start_stop_btn)
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
        self.log("✅ TradutorOn v2.0 - FASE 3 COMPLETA!")
        self.log(f"🕐 Iniciado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        self.log("=" * 60)
        self.log("🎉 Novidades da FASE 3:")
        self.log("   ✅ Detecção automática de idioma")
        self.log("   ✅ Agrupamento de textos próximos")
        self.log("   ✅ Retry automático em erros")
        self.log("   ✅ Painel de configurações")
        self.log("   ✅ Histórico de traduções")
        self.log("=" * 60)
        self.log("💡 Use os botões acima para começar")
        self.log("")
        
    def log(self, message: str):
        """Adiciona mensagem ao log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
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
        
    def load_saved_area(self):
        """Carrega área salva das configurações."""
        try:
            from src.config.settings import SettingsManager
            settings = SettingsManager()
            
            saved_area = settings.get('capture.region')
            if saved_area:
                self.selected_area = tuple(saved_area)
                x, y, w, h = self.selected_area
                self.log("")
                self.log("💾 Área salva carregada:")
                self.log(f"   📍 Posição: ({x}, {y})")
                self.log(f"   📐 Tamanho: {w} x {h} px")
                self.log("")
                self.statusBar().showMessage(f"💾 Área carregada: {w}x{h} px")
                return True
        except Exception as e:
            logger.error(f"Erro ao carregar área: {e}")
        return False
        
    def clear_saved_area(self):
        """Limpa área salva das configurações."""
        try:
            from src.config.settings import SettingsManager
            settings = SettingsManager()
            settings.set('capture.region', None)
            settings.save()
            self.selected_area = None
            
            self.log("")
            self.log("🗑️ Área salva foi removida!")
            self.log("💡 Selecione uma nova área com 'Iniciar Tradução'")
            self.log("")
            self.statusBar().showMessage("🗑️ Área salva removida")
        except Exception as e:
            self.log(f"❌ Erro ao limpar área: {e}")
            logger.error(f"Erro ao limpar área: {e}")
        
    def test_config(self):
        """Testa configurações."""
        self.log("")
        self.log("⚙️ Testando configurações...")
        self.statusBar().showMessage("⏳ Testando configurações...")
        
        try:
            from src.config.settings import SettingsManager
            settings = SettingsManager()
            
            groq_key = settings.get_api_key('groq')
            if groq_key:
                self.log(f"✅ Groq API configurada ({len(groq_key)} chars)")
            else:
                self.log("⚠️ Groq API não configurada")
            
            frame_rate = settings.get('capture.frame_rate', 2)
            self.log(f"✅ Frame rate: {frame_rate} fps")
            
            ocr_lang = settings.get('ocr.languages', ['ja', 'en'])
            self.log(f"✅ Idiomas OCR: {', '.join(ocr_lang)}")
            
            cache_size = settings.get('cache.max_entries', 1000)
            self.log(f"✅ Cache máximo: {cache_size} entradas")
            
            auto_detect = settings.get('translation.auto_detect', True)
            self.log(f"✅ Auto-detecção: {'Sim' if auto_detect else 'Não'}")
            
            group_nearby = settings.get('translation.group_nearby', False)
            self.log(f"✅ Agrupamento: {'Sim' if group_nearby else 'Não'}")
            
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
            
    def test_overlay(self):
        """Testa overlay de tradução."""
        if not self.selected_area:
            self.log("")
            self.log("⚠️ Selecione uma área primeiro!")
            self.log("💡 Clique 'Iniciar Tradução' para selecionar área")
            return
            
        self.log("")
        self.log("👁️ Testando overlay de tradução...")
        self.log("💡 Você verá 3 traduções de exemplo na área selecionada")
        self.log("🖱️ Clique nas traduções para removê-las")
        self.log("⏱️ Elas desaparecem automaticamente em 5 segundos")
        
        # Criar overlay
        if self.translation_overlay:
            self.translation_overlay.clear_all()
        else:
            self.translation_overlay = TranslationReplacer(self.selected_area)
            self.translation_overlay.show()
            
        # Simular traduções
        QTimer.singleShot(500, lambda: self.translation_overlay.show_translation({
            'original': 'こんにちは世界',
            'translated': 'Olá mundo!',
            'bbox': (50, 50, 150, 30)
        }))
        
        QTimer.singleShot(1000, lambda: self.translation_overlay.show_translation({
            'original': 'ありがとうございます',
            'translated': 'Muito obrigado!',
            'bbox': (200, 150, 180, 30)
        }))
        
        QTimer.singleShot(1500, lambda: self.translation_overlay.show_translation({
            'original': 'さようなら',
            'translated': 'Até logo!',
            'bbox': (100, 300, 120, 30)
        }))
        
        self.statusBar().showMessage("✅ Overlay de teste ativo")
        
    def open_settings(self):
        """Abre diálogo de configurações."""
        try:
            from src.config.settings import SettingsManager
            settings = SettingsManager()
            
            dialog = SettingsDialog(settings, self)
            if dialog.exec():
                self.log("")
                self.log("✅ Configurações atualizadas!")
                self.log("💡 Reinicie a tradução para aplicar mudanças")
                self.log("")
                
        except Exception as e:
            self.log(f"❌ Erro ao abrir configurações: {e}")
            logger.error(f"Erro ao abrir configurações: {e}")
            
    def open_history(self):
        """Abre histórico de traduções."""
        try:
            dialog = TranslationHistoryDialog(self.translation_history, self)
            dialog.exec()
            
        except Exception as e:
            self.log(f"❌ Erro ao abrir histórico: {e}")
            logger.error(f"Erro ao abrir histórico: {e}")
            
    def toggle_translation(self):
        """Inicia ou para tradução."""
        if not self.is_running:
            self.start_translation()
        else:
            self.stop_translation()
            
    def start_translation(self):
        """Inicia tradução."""
        # Se não tem área, selecionar
        if not self.selected_area:
            self.select_area()
            return
            
        # Iniciar pipeline
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
        self.start_stop_btn.setText("⏹️ Parar Tradução")
        self.start_stop_btn.setStyleSheet(
            "background-color: #f44336; color: white; "
            "font-size: 14px; font-weight: bold;"
        )
        self.status_label.setText("🔄 Traduzindo em tempo real...")
        self.status_label.setStyleSheet("font-size: 16px; color: orange; padding: 10px;")
        self.progress_bar.setVisible(True)
        self.statusBar().showMessage("🔄 Pipeline + Overlay rodando...")
        
        # Minimizar janela
        QTimer.singleShot(500, self.showMinimized)
        
        # Iniciar worker
        try:
            from src.config.settings import SettingsManager
            settings = SettingsManager()
            
            self.pipeline_worker = PipelineWorker(self.selected_area, settings)
            self.pipeline_worker.translation_received.connect(self.on_translation_result)
            self.pipeline_worker.stats_updated.connect(self.on_stats_update)
            self.pipeline_worker.error_occurred.connect(self.on_pipeline_error)
            self.pipeline_worker.start()
            
        except Exception as e:
            self.log(f"❌ Erro ao iniciar pipeline: {e}")
            self.stop_translation()
            
    def stop_translation(self):
        """Para tradução."""
        self.log("")
        self.log("🛑 Parando tradução...")
        
        # Parar worker
        if self.pipeline_worker:
            self.pipeline_worker.stop()
            self.pipeline_worker = None
            
        # Limpar overlay
        if self.translation_overlay:
            self.translation_overlay.clear_all()
            
        # Atualizar UI
        self.is_running = False
        self.start_stop_btn.setText("🚀 Iniciar Tradução")
        self.start_stop_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; "
            "font-size: 14px; font-weight: bold;"
        )
        self.status_label.setText("✅ Sistema pronto!")
        self.status_label.setStyleSheet("font-size: 16px; color: green; padding: 10px;")
        self.progress_bar.setVisible(False)
        self.statusBar().showMessage("✅ Pipeline parado")
        
        # Restaurar janela
        self.showNormal()
        self.activateWindow()
        
        self.log("✅ Tradução parada!")
        self.log(f"📊 Total de traduções: {self.translation_count}")
        self.log(f"📚 Histórico: {len(self.translation_history)} itens")
        self.log("")
        
    def select_area(self):
        """Abre seletor de área."""
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
            from src.config.settings import SettingsManager
            settings = SettingsManager()
            settings.set('capture.region', list(area))
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
        self.log(f"   📍 Posição: ({x}, {y})")
        self.log(f"   📐 Tamanho: {w} x {h} px")
        self.log(save_msg)
        self.log("=" * 60)
        self.log("💡 Clique 'Iniciar Tradução' para começar!")
        self.log("")
        
        self.statusBar().showMessage(f"✅ Área selecionada: {w}x{h} px")
        
        # Auto-iniciar tradução
        QTimer.singleShot(1000, self.start_translation)
        
    def on_translation_result(self, result: dict):
        """Callback quando recebe tradução."""
        try:
            self.translation_count += 1
            
            original = result.get('original', '')
            translated = result.get('translated', '')
            confidence = result.get('confidence', 0) * 100
            language = result.get('language', '?')
            bbox = result.get('bbox')
            provider = result.get('provider', '?')
            
            # Adicionar ao histórico
            history_item = {
                'timestamp': result.get('timestamp', datetime.now().strftime('%H:%M:%S')),
                'original': original,
                'translated': translated,
                'language': language,
                'provider': provider,
                'confidence': confidence
            }
            self.translation_history.append(history_item)
            
            # Limitar histórico a 1000 itens
            if len(self.translation_history) > 1000:
                self.translation_history.pop(0)
            
            # Log detalhado
            self.log(f"📝 #{self.translation_count} [{language.upper()}] {original[:50]}...")
            self.log(f"   → {translated[:80]}")
            self.log(f"   Confiança: {confidence:.1f}% | Provedor: {provider}")
            
            # Mostrar no overlay
            if self.translation_overlay and bbox:
                self.translation_overlay.show_translation(result)
                self.overlays_label.setText(f"👁️ Overlays: {self.translation_count}")
                self.log(f"   ✅ Overlay exibido")
            else:
                if not bbox:
                    self.log(f"   ⚠️ Sem bbox - overlay não exibido")
            
            # Atualizar contador
            self.translations_label.setText(f"📝 Traduções: {self.translation_count}")
            
        except Exception as e:
            logger.error(f"Erro ao processar resultado: {e}")
            self.log(f"   ❌ Erro: {e}")
        
    def on_stats_update(self, stats: dict):
        """Atualiza estatísticas na UI."""
        cache_stats = stats.get('cache', {})
        
        total_cache = cache_stats.get('total_translations', 0)
        db_size = cache_stats.get('db_size_mb', 0)
        
        self.cache_label.setText(f"💾 Cache: {total_cache}")
        self.db_size_label.setText(f"💽 DB: {db_size:.2f} MB")
        
    def on_pipeline_error(self, error: str):
        """Trata erros do pipeline."""
        self.log(f"❌ ERRO: {error}")
        self.stop_translation()
        
    def closeEvent(self, event):
        """Ao fechar janela."""
        if self.is_running:
            self.stop_translation()
        if self.translation_overlay:
            self.translation_overlay.clear_all()
        event.accept()


def main():
    """Função principal."""
    LoggerSetup.initialize(level="INFO")  # INFO para produção
    
    logger.info("=" * 60)
    logger.info("TRADUTOR ON v2.0 - FASE 3 COMPLETA")
    logger.info("=" * 60)
    
    app = QApplication(sys.argv)
    app.setApplicationName("TradutorOn")
    app.setStyle("Fusion")
    
    window = SimpleMainWindow()
    window.show()
    
    logger.info("✅ Aplicação iniciada com sucesso")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
