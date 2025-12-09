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
from src.utils.language_detector import LanguageDetector
from src.utils.text_grouper import TextGrouper


class ProcessingPipeline:
    """Pipeline de processamento com Producer-Consumer."""

    def __init__(
        self,
        settings_manager: SettingsManager,
        on_result_callback: Callable[[List[Dict[str, Any]]], None] = None,
        num_ocr_workers: int = 2,
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
        self.frame_diff = FrameDiff(
            threshold=settings_manager.get("capture.detection_threshold", 0.08)
        )

        # OCR
        ocr_langs = settings_manager.get("ocr.languages", ["en", "ko"])
        use_gpu = settings_manager.get("ocr.use_gpu", False)
        self.ocr_engine = OCREngine(languages=ocr_langs, use_gpu=use_gpu)
        self.text_cleaner = TextCleaner()

        # Detector de idioma (Fase 2)
        self.language_detector = LanguageDetector()

        # Agrupamento de textos próximos (Fase 5)
        group_distance = self.settings.get("translation.group_distance", 50)
        self.group_nearby = self.settings.get(
            "translation.group_nearby", False
        )
        self.text_grouper = (
            TextGrouper(max_distance=group_distance)
            if self.group_nearby
            else None
        )

        # Fase 1 – filtro de confiança de OCR
        # Lido das configs em ocr.confidence_threshold, com default 0.3
        self.ocr_conf_threshold = settings_manager.get(
            "ocr.confidence_threshold", 0.3
        )

        # Tradução - NOVOS PROVEDORES GRATUITOS
        groq_key = settings_manager.get_api_key("groq")
        groq_model = settings_manager.get(
            "translation.groq.model", "llama-3.3-70b-versatile"
        )
        google_enabled = settings_manager.get(
            "translation.google.enabled", True
        )
        ollama_enabled = settings_manager.get(
            "translation.ollama.enabled", False
        )
        ollama_model = settings_manager.get(
            "translation.ollama.model", "qwen2.5:7b"
        )  # default alinhado ao YAML
        ollama_url = settings_manager.get(
            "translation.ollama.base_url", "http://localhost:11434"
        )

        self.translation_service = TranslationService(
            groq_key=groq_key,
            google_enabled=google_enabled,
            ollama_enabled=ollama_enabled,
            groq_model=groq_model,
            ollama_model=ollama_model,
            ollama_url=ollama_url,
        )

        # Cache
        cache_path = settings_manager.get_cache_db_path()
        max_entries = settings_manager.get("cache.max_entries", 100000)
        self.cache_manager = CacheManager(cache_path, max_entries)

        # Controle
        self.task_queue = queue.PriorityQueue()
        self.running = False
        self.threads: List[threading.Thread] = []

        logger.info(
            f"ProcessingPipeline inicializado - {num_ocr_workers} workers"
        )

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
        producer_thread = threading.Thread(
            target=self._producer_loop, daemon=True
        )
        producer_thread.start()
        self.threads.append(producer_thread)

        # Threads consumer (OCR workers)
        for i in range(self.num_workers):
            worker_thread = threading.Thread(
                target=self._consumer_loop, args=(i,), daemon=True
            )
            worker_thread.start()
            self.threads.append(worker_thread)

        logger.info(
            f"Pipeline iniciada - área: {area.width}x{area.height}"
        )

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
        frame_rate = self.settings.get("capture.frame_rate", 2)
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
                        priority=5,
                    )
                    self.task_queue.put(task)
                    logger.debug(
                        f"Frame enfileirado - diff: {diff_value:.4f}"
                    )

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
        Processa um frame: OCR + Agrupamento + Tradução.

        Args:
            task: Tarefa de processamento

        Returns:
            Lista de resultados
        """
        results: List[Dict[str, Any]] = []

        try:
            # 1. OCR
            ocr_results: List[OCRResult] = self.ocr_engine.extract_text(
                task.frame
            )
            if not ocr_results:
                return results

            # Fase 1 – filtro de confiança de OCR:
            # descarta resultados com confidence abaixo de self.ocr_conf_threshold
            total_ocr = len(ocr_results)
            filtered_ocr_results: List[OCRResult] = []

            for ocr_result in ocr_results:
                confidence = getattr(ocr_result, "confidence", None)

                # Se houver valor de confiança e ele for menor que o limiar, descarta
                if (
                    confidence is not None
                    and confidence < self.ocr_conf_threshold
                ):
                    text_preview = (ocr_result.text or "")[
                        :30
                    ].replace("\n", " ")
                    logger.debug(
                        "OCR descartado por baixa confiança "
                        f"(conf={confidence:.3f} < limiar={self.ocr_conf_threshold:.3f}): "
                        f"'{text_preview}'"
                    )
                    continue

                filtered_ocr_results.append(ocr_result)

            logger.debug(
                "OCR: "
                f"{total_ocr} detectados, "
                f"{len(filtered_ocr_results)} acima do threshold "
                f"{self.ocr_conf_threshold:.3f}"
            )

            if not filtered_ocr_results:
                # Nada acima do limiar de confiança; não há o que traduzir
                return results

            # 2. Preparar entrada para agrupamento (texto limpo + idioma + bbox normalizado)
            grouped_input: List[Dict[str, Any]] = []

            for ocr_result in filtered_ocr_results:
                # Limpar texto
                clean_text = self.text_cleaner.clean(ocr_result.text)
                if not clean_text or len(clean_text) < 2:
                    continue

                # Detectar idioma com LanguageDetector (Fase 2)
                detected_lang = self.language_detector.detect(clean_text)
                logger.debug(
                    f"Idioma detectado: {detected_lang} para "
                    f"'{clean_text[:30]}...'"
                )
                source_lang = (
                    detected_lang if detected_lang != "unknown" else "en"
                )

                # Converter bbox para (x, y, w, h) para o TextGrouper
                bbox_xyxy = ocr_result.bbox
                if bbox_xyxy and len(bbox_xyxy) == 4:
                    x1, y1, x2, y2 = bbox_xyxy
                    bbox_wh = (x1, y1, x2 - x1, y2 - y1)
                else:
                    bbox_wh = bbox_xyxy

                grouped_input.append(
                    {
                        "original": clean_text,
                        "bbox": bbox_wh,
                        "confidence": ocr_result.confidence,
                        "language": source_lang,
                    }
                )

            if not grouped_input:
                return results

            # 3. Agrupar textos próximos (balões / falas relacionadas)
            if self.text_grouper is not None and self.group_nearby:
                grouped_results = self.text_grouper.group_results(
                    grouped_input
                )
                logger.debug(
                    f"Agrupamento: {len(grouped_input)} → "
                    f"{len(grouped_results)} grupos"
                )
            else:
                grouped_results = grouped_input

            # 4. Traduzir por grupo
            for item in grouped_results:
                combined_original = item.get("original", "")
                if not combined_original or len(combined_original) < 2:
                    continue

                # Usar idioma já detectado para o grupo, ou recalcular se necessário
                source_lang = item.get("language", "")
                if not source_lang or source_lang == "unknown":
                    detected_lang = self.language_detector.detect(
                        combined_original
                    )
                    logger.debug(
                        f"Idioma (re)detectado para grupo: {detected_lang} "
                        f"para '{combined_original[:30]}...'"
                    )
                    source_lang = (
                        detected_lang if detected_lang != "unknown" else "en"
                    )

                bbox = item.get("bbox")
                confidence = item.get("confidence", 1.0)

                # 4.1 Tentar cache primeiro
                cached = self.cache_manager.get_translation(
                    combined_original,
                    source_lang=source_lang,
                    target_lang="pt",
                )

                if cached:
                    translated_text = cached
                    provider = "cache"
                else:
                    # 4.2 Traduzir usando serviço (Groq/Google/Ollama/Offline)
                    translation_result = self.translation_service.translate(
                        combined_original,
                        source_lang=source_lang,
                        target_lang="pt",
                    )
                    translated_text = translation_result.translated_text
                    provider = translation_result.provider.value

                    # 4.3 Salvar no cache
                    self.cache_manager.save_translation(
                        original_text=combined_original,
                        translated_text=translated_text,
                        source_lang=source_lang,
                        target_lang="pt",
                        provider=provider,
                        confidence=translation_result.confidence,
                    )

                # 5. Adicionar aos resultados (um por grupo)
                result = {
                    "original": combined_original,
                    "translated": translated_text,
                    "bbox": bbox,
                    "confidence": confidence,
                    "language": source_lang,
                    "provider": provider,
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
            "running": self.running,
            "queue_size": self.task_queue.qsize(),
            "num_workers": self.num_workers,
            "cache": cache_stats,
            "translators": active_providers,
        }

        return stats
