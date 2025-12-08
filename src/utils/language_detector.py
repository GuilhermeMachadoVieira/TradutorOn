"""Detector de idioma para textos OCR."""
from loguru import logger
from typing import Optional
import re


class LanguageDetector:
    """Detecta idioma de texto baseado em caracteres."""
    
    # Ranges Unicode para diferentes scripts
    JAPANESE_RANGES = [
        (0x3040, 0x309F),  # Hiragana
        (0x30A0, 0x30FF),  # Katakana
        (0x4E00, 0x9FFF),  # Kanji (CJK Unified Ideographs)
    ]
    
    KOREAN_RANGES = [
        (0xAC00, 0xD7AF),  # Hangul Syllables
        (0x1100, 0x11FF),  # Hangul Jamo
    ]
    
    CHINESE_RANGES = [
        (0x4E00, 0x9FFF),  # CJK Unified Ideographs
    ]
    
    def __init__(self):
        logger.info("LanguageDetector inicializado")
        
    def detect(self, text: str) -> str:
        """
        Detecta idioma do texto.
        
        Returns:
            'ja' = Japonês
            'ko' = Coreano
            'zh' = Chinês
            'en' = Inglês
            'unknown' = Desconhecido
        """
        if not text or len(text.strip()) == 0:
            return 'unknown'
            
        text = text.strip()
        
        # Contar caracteres por script
        japanese_chars = self._count_chars_in_ranges(text, self.JAPANESE_RANGES)
        korean_chars = self._count_chars_in_ranges(text, self.KOREAN_RANGES)
        chinese_chars = self._count_chars_in_ranges(text, self.CHINESE_RANGES)
        
        # Verificar ASCII (provável inglês)
        ascii_chars = sum(1 for c in text if ord(c) < 128)
        
        total_chars = len(text)
        
        # Calcular proporções
        ja_ratio = japanese_chars / total_chars
        ko_ratio = korean_chars / total_chars
        zh_ratio = chinese_chars / total_chars
        ascii_ratio = ascii_chars / total_chars
        
        logger.debug(f"Detecção: ja={ja_ratio:.2f}, ko={ko_ratio:.2f}, zh={zh_ratio:.2f}, ascii={ascii_ratio:.2f}")
        
        # Decidir idioma (ordem de prioridade)
        if ja_ratio > 0.3:
            return 'ja'
        elif ko_ratio > 0.3:
            return 'ko'
        elif zh_ratio > 0.3 and japanese_chars < chinese_chars * 0.5:
            # Chinês só se não tiver muito Hiragana/Katakana
            return 'zh'
        elif ascii_ratio > 0.7:
            return 'en'
        else:
            return 'unknown'
            
    def _count_chars_in_ranges(self, text: str, ranges: list) -> int:
        """Conta caracteres dentro de ranges Unicode."""
        count = 0
        for char in text:
            code = ord(char)
            for start, end in ranges:
                if start <= code <= end:
                    count += 1
                    break
        return count
        
    def is_asian_language(self, lang: str) -> bool:
        """Verifica se é idioma asiático."""
        return lang in ['ja', 'ko', 'zh']
