"""
Pipeline de processamento com workers paralelos.
"""

import queue
import threading
import time
from typing import Callable, List, Dict, Any
from datetime import datetime
from loguru import logger

from src.utils.types import ScreenArea, ProcessingTask, OCRResult
from src.capture.screen_capturer import ScreenCapturer
from src.capture.frame_diff import FrameDiff
from src.ocr.ocr_engine import OCREngine
from src.ocr.text_cleaner import TextCleaner
from src.translation.translator import TranslationService
from src.cache.cache_manager import CacheManager
from src.config.settings import SettingsManager


class ProcessingPipeline:
    """Pipeline de processamento com Producer-Consumer."""

    def __init__(
        self,
        settings_manager: SettingsManager,
        on_result_callback: Callable[[List[Dict[str, Any]]], None] = None,
        num_ocr_workers: int = 2
    ):
        """
        Args:
            settings_manager: Gerenciador de configurações
            on_result_callback: Callback chamado com resultados
            num_ocr_workers: Número de workers OCR paralelos
        """
        self.settings = settings_manager
        self.callback = on_result_callback
        self.num_workers = num_ocr_workers

        # Componentes
        self.capturer = ScreenCapturer()
        self.frame_diff = FrameDiff(threshold=settings_manager.get('capture.detection_threshold', 0.08))
        
        # OCR
        ocr_langs = settings_manager.get('ocr.languages', ['en', 'ko'])
        use_gpu = settings_manager.get('ocr.use_gpu', False)
        self.ocr_engine = OCREngine(languages=ocr_langs, use_gpu=use_gpu)
        self.text_cleaner = TextCleaner()

        # Tradução - NOVOS PROVEDORES GRATUITOS
        groq_key = settings_manager.get_api_key('groq')
        groq_model = settings_manager.get('translation.groq.model', 'llama-3.1-70b-versatile')
        google_enabled = settings_manager.get('translation.google.enabled', True)
        ollama_enabled = settings_manager.get('translation.ollama.enabled', False)
        ollama_model = settings_manager.get('translation.ollama.model', 'llama3.1')
        ollama_url = settings_manager.get('translation.ollama.base_url', 'http://localhost:11434')

        self.translation_service = TranslationService(
            groq_key=groq_key,
            google_enabled=google_enabled,
            ollama_enabled=ollama_enabled,
            groq_model=groq_model,
            ollama_model=ollama_model,
            ollama_url=ollama_url
        )

        # Cache
        cache_path = settings_manager.get_cache_db_path()
        max_entries = settings_manager.get('cache.max_entries', 100000)
        self.cache_manager = CacheManager(cache_path, max_entries)

        # Controle
        self.task_queue = queue.PriorityQueue()
        self.running = False
        self.threads = []

        logger.info(f"ProcessingPipeline inicializado - {num_ocr_workers} workers")

    def start(self, area: ScreenArea):
        """
        Inicia o pipeline.
        
        Args:
            area: Área da tela a monitorar
        """
        if self.running:
            logger.warning("Pipeline já está rodando")
            return

        self.running = True
        self.capture_area = area

        # Thread producer (captura)
        producer_thread = threading.Thread(target=self._producer_loop, daemon=True)
        producer_thread.start()
        self.threads.append(producer_thread)

        # Threads consumer (OCR workers)
        for i in range(self.num_workers):
            worker_thread = threading.Thread(target=self._consumer_loop, args=(i,), daemon=True)
            worker_thread.start()
            self.threads.append(worker_thread)

        logger.info(f"Pipeline iniciada - área: {area.width}x{area.height}")

    def stop(self):
        """Para o pipeline."""
        if not self.running:
            return

        self.running = False
        
        # Aguardar threads
        for thread in self.threads:
            thread.join(timeout=2)

        self.capturer.release()
        logger.info("Pipeline parada")

    def _producer_loop(self):
        """Loop do producer: captura frames."""
        frame_rate = self.settings.get('capture.frame_rate', 2)
        sleep_time = 1.0 / frame_rate

        logger.debug(f"Producer iniciado - {frame_rate} fps")

        while self.running:
            try:
                # Capturar frame
                frame = self.capturer.capture_area(self.capture_area)
                
                if frame is None:
                    time.sleep(sleep_time)
                    continue

                # Detectar mudança
                changed, diff_value = self.frame_diff.detect_change(frame)

                if changed:
                    # Enfileirar para processamento
                    task = ProcessingTask(
                        frame=frame,
                        area=self.capture_area,
                        timestamp=datetime.now(),
                        priority=5
                    )
                    self.task_queue.put(task)
                    logger.debug(f"Frame enfileirado - diff: {diff_value:.4f}")

                time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Erro no producer: {e}")
                time.sleep(1)

    def _consumer_loop(self, worker_id: int):
        """
        Loop do consumer: processa frames.
        
        Args:
            worker_id: ID do worker
        """
        logger.debug(f"Worker {worker_id} iniciado")

        while self.running:
            try:
                # Pegar tarefa da fila (timeout 1s)
                task = self.task_queue.get(timeout=1)

                # Processar
                results = self._process_frame(task)

                # Chamar callback se houver resultados
                if results and self.callback:
                    self.callback(results)

                self.task_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Erro no worker {worker_id}: {e}")

    def _process_frame(self, task: ProcessingTask) -> List[Dict[str, Any]]:
        """
        Processa um frame: OCR + Tradução.
        
        Args:
            task: Tarefa de processamento
            
        Returns:
            Lista de resultados
        """
        results = []

        try:
            # 1. OCR
            ocr_results: List[OCRResult] = self.ocr_engine.extract_text(task.frame)

            if not ocr_results:
                return results

            # 2. Processar cada texto detectado
            for ocr_result in ocr_results:
                # Limpar texto
                clean_text = self.text_cleaner.clean(ocr_result.text)
                
                if not clean_text or len(clean_text) < 2:
                    continue

                # Detectar idioma
                detected_lang = self.text_cleaner.estimate_language(clean_text)
                source_lang = detected_lang if detected_lang != 'unknown' else 'en'

                # 3. Tentar cache primeiro
                cached = self.cache_manager.get_translation(
                    clean_text,
                    source_lang=source_lang,
                    target_lang='pt'
                )

                if cached:
                    translated_text = cached
                    provider = 'cache'
                else:
                    # 4. Traduzir usando novo serviço
                    translation_result = self.translation_service.translate(
                        clean_text,
                        source_lang=source_lang,
                        target_lang='pt'
                    )
                    translated_text = translation_result.translated_text
                    provider = translation_result.provider.value

                    # 5. Salvar no cache
                    self.cache_manager.save_translation(
                        original_text=clean_text,
                        translated_text=translated_text,
                        source_lang=source_lang,
                        target_lang='pt',
                        provider=provider,
                        confidence=translation_result.confidence
                    )

                # 6. Adicionar aos resultados
                result = {
                    'original': clean_text,
                    'translated': translated_text,
                    'bbox': ocr_result.bbox,
                    'confidence': ocr_result.confidence,
                    'language': source_lang,
                    'provider': provider
                }
                results.append(result)

            logger.debug(f"Frame processado - {len(results)} traduções")

        except Exception as e:
            logger.error(f"Erro ao processar frame: {e}")

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do pipeline."""
        cache_stats = self.cache_manager.get_cache_stats()
        
        # Obter provedores ativos
        active_providers = self.translation_service.get_active_providers()
        
        stats = {
            'running': self.running,
            'queue_size': self.task_queue.qsize(),
            'num_workers': self.num_workers,
            'cache': cache_stats,
            'translators': active_providers
        }
        
        return stats
