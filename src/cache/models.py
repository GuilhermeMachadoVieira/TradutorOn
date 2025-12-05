"""
Modelos SQLAlchemy para cache.
"""

from sqlalchemy import Column, String, Float, Integer, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class TranslationCache(Base):
    """Tabela de cache de traduções."""
    
    __tablename__ = 'translation_cache'

    id = Column(Integer, primary_key=True, autoincrement=True)
    original_text = Column(String, nullable=False)
    translated_text = Column(String, nullable=False)
    source_lang = Column(String(10), nullable=False)
    target_lang = Column(String(10), nullable=False)
    provider = Column(String(20), nullable=False)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.now)
    accessed_count = Column(Integer, default=0)
    last_accessed = Column(DateTime, default=datetime.now)

    # Índices compostos para busca rápida
    __table_args__ = (
        Index('idx_text_langs', 'original_text', 'source_lang', 'target_lang'),
        Index('idx_created', 'created_at'),
    )


class OCRCache(Base):
    """Tabela de cache de OCR."""
    
    __tablename__ = 'ocr_cache'

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_hash = Column(String(64), unique=True, nullable=False)
    extracted_text = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    language = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    accessed_count = Column(Integer, default=0)

    __table_args__ = (
        Index('idx_image_hash', 'image_hash'),
    )
