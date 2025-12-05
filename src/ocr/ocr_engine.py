"""
Engine OCR com PaddleOCR.
"""

from typing import List, Optional, Tuple
from datetime import datetime
import numpy as np
import hashlib
from loguru import logger

try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    logger.warning("PaddleOCR não disponível")

from src.utils.types import OCRResult


class OCREngine:
    """Engine de OCR usando PaddleOCR."""

    def __init__(self, languages: List[str] = None, use_gpu: bool = False):
        """
        Args:
            languages: Lista de idiomas (['en', 'ko'])
            use_gpu: Usar GPU se disponível
        """
        if not PADDLEOCR_AVAILABLE:
            raise RuntimeError("PaddleOCR não está instalado")

        self.languages = languages or ['en', 'ko']
        self.use_gpu = use_gpu
        self.cache = {}  # Cache simples em memória
        
        # Mapear códigos de idioma
        lang_map = {'en': 'en', 'ko': 'korean'}
        paddle_langs = [lang_map.get(lang, 'en') for lang in self.languages]

        try:
            self.ocr = PaddleOCR(
                use_angle_cls=True,
                lang=paddle_langs[0],  # Idioma primário
                use_gpu=use_gpu,
                show_log=False
            )
            logger.info(f"PaddleOCR inicializado - idiomas: {self.languages}, GPU: {use_gpu}")
        except Exception as e:
            logger.error(f"Erro ao inicializar PaddleOCR: {e}")
            raise

    def extract_text(self, image: np.ndarray) -> List[OCRResult]:
        """
        Extrai texto de uma imagem.
        
        Args:
            image: Imagem como numpy array (BGR)
            
        Returns:
            Lista de OCRResult
        """
        # Cache baseado em hash da imagem
        img_hash = self._hash_image(image)
        if img_hash in self.cache:
            logger.debug("Cache hit para OCR")
            return self.cache[img_hash]

        try:
            results = []
            ocr_results = self.ocr.ocr(image, cls=True)

            if not ocr_results or not ocr_results[0]:
                logger.debug("Nenhum texto detectado")
                return []

            for line in ocr_results[0]:
                bbox = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                text_info = line[1]  # (text, confidence)
                
                text = text_info[0]
                confidence = text_info[1]

                # Converter bbox para formato simples (x1, y1, x2, y2)
                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]
                simple_bbox = (
                    min(x_coords),
                    min(y_coords),
                    max(x_coords),
                    max(y_coords)
                )

                result = OCRResult(
                    text=text,
                    confidence=confidence,
                    bbox=simple_bbox,
                    language=self.languages[0],
                    timestamp=datetime.now()
                )

                if result.is_valid():
                    results.append(result)

            # Armazenar no cache
            if len(self.cache) < 100:  # Limite de cache
                self.cache[img_hash] = results

            logger.debug(f"OCR extraiu {len(results)} textos")
            return results

        except Exception as e:
            logger.error(f"Erro no OCR: {e}")
            return []

    def _hash_image(self, image: np.ndarray) -> str:
        """Gera hash SHA256 de uma imagem."""
        return hashlib.sha256(image.tobytes()).hexdigest()[:16]

    def clear_cache(self):
        """Limpa o cache de OCR."""
        self.cache.clear()
        logger.debug("Cache de OCR limpo")
