"""
Type definitions para o projeto Manga Translator Pro.
"""

from dataclasses import dataclass
from typing import Optional, Tuple, Any
from enum import Enum
from datetime import datetime


class TranslationProvider(Enum):
    """Provedores de tradução disponíveis."""
    GROQ = "groq"
    GOOGLE = "google"
    OLLAMA = "ollama"
    OFFLINE = "offline"


class LanguageCode(Enum):
    """Códigos de idioma suportados."""
    ENGLISH = "en"
    KOREAN = "ko"
    PORTUGUESE = "pt"


@dataclass
class MonitorInfo:
    """Informações sobre um monitor."""
    index: int
    name: str
    width: int
    height: int
    x: int
    y: int
    dpi: int = 96


@dataclass
class ScreenArea:
    """Área selecionada na tela."""
    x1: int
    y1: int
    x2: int
    y2: int
    monitor_index: int = 0

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def area(self) -> int:
        return self.width * self.height

    def to_tuple(self) -> Tuple[int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2)


@dataclass
class OCRResult:
    """Resultado do OCR."""
    text: str
    confidence: float
    bbox: Tuple[float, float, float, float]
    language: str
    timestamp: datetime

    def is_valid(self, min_confidence: float = 0.3) -> bool:
        return self.confidence >= min_confidence and len(self.text.strip()) > 0


@dataclass
class TranslationResult:
    """Resultado da tradução."""
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    provider: TranslationProvider
    confidence: float = 1.0
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ProcessingTask:
    """Tarefa de processamento."""
    frame: Any
    area: ScreenArea
    timestamp: datetime
    priority: int = 5

    def __lt__(self, other: "ProcessingTask") -> bool:
        return self.priority < other.priority
