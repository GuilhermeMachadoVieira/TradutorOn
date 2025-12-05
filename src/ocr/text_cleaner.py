"""
Limpeza e normalização de texto de OCR.
"""

import re
import unicodedata
from typing import List


class TextCleaner:
    """Limpa e normaliza texto extraído por OCR."""

    def __init__(self, normalize_unicode: bool = True):
        self.normalize_unicode = normalize_unicode

    def clean(self, text: str) -> str:
        """
        Limpa texto de OCR.
        
        Args:
            text: Texto bruto do OCR
            
        Returns:
            Texto limpo
        """
        if not text:
            return ""

        # Remover espaços extras
        text = ' '.join(text.split())

        # Remover caracteres de controle
        text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C')

        # Normalizar unicode se habilitado
        if self.normalize_unicode:
            text = unicodedata.normalize('NFKC', text)

        return text.strip()

    def split_paragraphs(self, text: str, max_words: int = 50) -> List[str]:
        """
        Divide texto em parágrafos menores.
        
        Args:
            text: Texto completo
            max_words: Máximo de palavras por parágrafo
            
        Returns:
            Lista de parágrafos
        """
        words = text.split()
        paragraphs = []
        
        for i in range(0, len(words), max_words):
            paragraph = ' '.join(words[i:i + max_words])
            paragraphs.append(paragraph)
        
        return paragraphs

    def extract_significant_text(self, text: str, min_length: int = 3) -> str:
        """
        Extrai apenas texto significativo (remove ruído).
        
        Args:
            text: Texto original
            min_length: Comprimento mínimo de palavra
            
        Returns:
            Texto filtrado
        """
        words = text.split()
        filtered = [w for w in words if len(w) >= min_length and any(c.isalnum() for c in w)]
        return ' '.join(filtered)

    @staticmethod
    def estimate_language(text: str) -> str:
        """
        Estima idioma do texto.
        
        Returns:
            'ko' (coreano), 'en' (inglês), ou 'unknown'
        """
        if not text:
            return 'unknown'

        # Detectar caracteres coreanos (Hangul)
        korean_chars = sum(1 for c in text if '\uac00' <= c <= '\ud7a3')
        
        # Detectar caracteres ASCII (inglês)
        ascii_chars = sum(1 for c in text if 'a' <= c.lower() <= 'z')

        total = len(text)
        if total == 0:
            return 'unknown'

        korean_ratio = korean_chars / total
        ascii_ratio = ascii_chars / total

        if korean_ratio > 0.3:
            return 'ko'
        elif ascii_ratio > 0.5:
            return 'en'
        
        return 'unknown'
