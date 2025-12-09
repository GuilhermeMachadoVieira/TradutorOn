"""
Worker de pipeline reutilizável para TradutorOn.

Responsável por rodar o ProcessingPipeline em uma QThread, emitindo sinais:
- translation_received(dict)
- stats_updated(dict)
- error_occurred(str)
"""

from datetime import datetime

from PyQt6.QtCore import QThread, pyqtSignal
from loguru import logger

from src.utils.language_detector import LanguageDetector
from src.utils.text_grouper import TextGrouper


class PipelineWorker(QThread):
    """Worker thread para rodar pipeline sem travar GUI."""

    # Signals
    translation_received = pyqtSignal(dict)  # Resultado individual normalizado
    stats_updated = pyqtSignal(dict)         # Estatísticas periódicas
    error_occurred = pyqtSignal(str)         # Erros fatais

    def __init__(self, area: tuple, settings_manager):
        """
        Args:
            area: (x, y, w, h) da região de captura relativa à tela.
            settings_manager: instância de SettingsManager já configurada.
        """
        super().__init__()
        self.area = area
        self.settings_manager = settings_manager
        self.pipeline = None
        self.running = False
        self.result_count = 0

        # Utilidades
        self.lang_detector = LanguageDetector()
        self.text_grouper = TextGrouper(
            max_distance=settings_manager.get("translation.group_distance", 50)
        )

        # Cache de resultados recentes para evitar duplicatas
        self.recent_results = {}
        self.last_emission_time = {}

    def run(self):
        """Executa pipeline em thread separada com retry automático."""
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
                    monitor_index=0,
                )

                # Criar pipeline
                self.pipeline = ProcessingPipeline(
                    settings_manager=self.settings_manager,
                    on_result_callback=self._on_translation,
                    num_ocr_workers=2,
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
                logger.error(
                    f"Erro no pipeline worker (tentativa {retry_count}/{max_retries}): {e}"
                )
                if retry_count < max_retries:
                    logger.info("🔄 Tentando novamente em 2 segundos...")
                    self.msleep(2000)
                else:
                    self.error_occurred.emit(
                        f"Falha após {max_retries} tentativas: {str(e)}"
                    )

    def _on_translation(self, results):
        """Callback de tradução vindo do ProcessingPipeline."""
        try:
            if not results:
                return

            logger.debug(f"📦 Pipeline retornou {len(results)} resultados")

            # Results pode ser lista de dicts ou um único dict
            if isinstance(results, list):
                # Agrupar se configurado
                if self.settings_manager.get("translation.group_nearby", False):
                    results = self.text_grouper.group_results(results)

                for result in results:
                    self._process_single_result(result)
            else:
                self._process_single_result(results)

        except Exception as e:
            logger.error(f"Erro ao processar resultados: {e}")

    def _process_single_result(self, result):
        """Processa um único resultado vindo do pipeline."""
        try:
            # Verificar se resultado é válido
            if not result or not isinstance(result, dict):
                logger.debug(f"⚠️ Resultado inválido: {type(result)}")
                return

            # Extrair campos mínimos
            original = result.get("original", result.get("text", ""))
            translated = result.get("translated", result.get("translation", ""))
            if not original or not translated:
                return

            # Criar chave única para este resultado
            result_key = self._make_result_key(original, translated)

            # Verificar se já processamos este resultado recentemente
            if self._is_recent_duplicate(result_key):
                logger.debug(
                    f"⚠️ Resultado duplicado ignorado: '{translated[:30]}'"
                )
                return

            # Registrar resultado
            now = datetime.now()
            self.recent_results[result_key] = now
            self.last_emission_time[result_key] = now
            self.result_count += 1

            logger.debug(f"🔍 Resultado #{self.result_count}: {result.keys()}")

            # Detecção de idioma se habilitado
            language = result.get("language", "")
            if (
                self.settings_manager.get("translation.auto_detect", True)
                and not language
            ):
                language = self.lang_detector.detect(original)
                logger.debug(f"🔍 Idioma detectado: {language}")

            # Bbox pode vir em diferentes formatos
            bbox = None
            if "bbox" in result:
                bbox = result["bbox"]
            elif "bounding_box" in result:
                bbox = result["bounding_box"]
            elif "box" in result:
                bbox = result["box"]

            # Se não tem bbox, não criar overlay
            if not bbox:
                logger.warning("⚠️ Resultado sem bbox")
                return

            # Montar resultado normalizado para a GUI/overlay
            normalized = {
                "original": original,
                "translated": translated,
                "bbox": bbox,
                "confidence": result.get("confidence", 1.0),
                "language": language,
                "provider": result.get("provider", "unknown"),
                "timestamp": now.strftime("%H:%M:%S"),
            }

            logger.debug(
                f"✅ Emitindo: orig='{original[:30]}', "
                f"trans='{translated[:30]}', lang={language}"
            )
            self.translation_received.emit(normalized)

        except Exception as e:
            logger.error(f"Erro ao processar resultado individual: {e}")

    def _make_result_key(self, original: str, translated: str) -> str:
        """Cria chave única para resultado baseado em original+traduzido normalizados."""
        orig_normalized = original.lower().strip()
        trans_normalized = translated.lower().strip()
        return f"{orig_normalized}||{trans_normalized}"

    def _is_recent_duplicate(self, result_key: str) -> bool:
        """Verifica se resultado é duplicata recente (3s / 2s entre emissões)."""
        if result_key not in self.recent_results:
            return False

        now = datetime.now()
        age = now - self.recent_results[result_key]

        # Considerar duplicata se foi processado nos últimos 3 segundos
        if age.total_seconds() < 3.0:
            return True

        # Verificar cooldown de emissão (mínimo 2 segundos entre emissões)
        if result_key in self.last_emission_time:
            last_age = now - self.last_emission_time[result_key]
            if last_age.total_seconds() < 2.0:
                return True

        return False

    def _cleanup_old_cache(self):
        """Remove entradas antigas do cache interno de duplicatas."""
        now = datetime.now()
        expired_keys = []

        for key, ts in self.recent_results.items():
            age = now - ts
            if age.total_seconds() > 10.0:  # manter por 10s
                expired_keys.append(key)

        for key in expired_keys:
            del self.recent_results[key]
            if key in self.last_emission_time:
                del self.last_emission_time[key]

        if expired_keys:
            logger.debug(
                f"🗑️ Cache worker limpo: {len(expired_keys)} entradas"
            )

    def stop(self):
        """Para pipeline e encerra a thread com segurança."""
        self.running = False
        if self.pipeline:
            try:
                self.pipeline.stop()
            except Exception as e:
                logger.error(f"Erro ao parar pipeline: {e}")

        self.quit()
        self.wait()
