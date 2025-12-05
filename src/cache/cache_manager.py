"""
Gerenciador de cache com SQLite.
"""

from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger

from src.cache.models import Base, TranslationCache, OCRCache


class CacheManager:
    """Gerencia cache persistente de traduções e OCR."""

    def __init__(self, db_path: Path, max_entries: int = 100000):
        """
        Args:
            db_path: Caminho do banco SQLite
            max_entries: Número máximo de entradas
        """
        self.db_path = db_path
        self.max_entries = max_entries

        # Criar diretório se não existir
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Criar engine
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        Base.metadata.create_all(self.engine)

        # Session factory
        self.SessionLocal = sessionmaker(bind=self.engine)

        logger.info(f"CacheManager inicializado - DB: {db_path}")

    def get_translation(
        self, 
        original_text: str, 
        source_lang: str, 
        target_lang: str
    ) -> Optional[str]:
        """
        Busca tradução no cache.
        
        Args:
            original_text: Texto original
            source_lang: Idioma origem
            target_lang: Idioma destino
            
        Returns:
            Texto traduzido ou None
        """
        session: Session = self.SessionLocal()
        try:
            entry = session.query(TranslationCache).filter_by(
                original_text=original_text,
                source_lang=source_lang,
                target_lang=target_lang
            ).first()

            if entry:
                # Atualizar estatísticas
                entry.accessed_count += 1
                entry.last_accessed = datetime.now()
                session.commit()
                
                logger.debug(f"Cache hit: '{original_text[:30]}...'")
                return entry.translated_text

            return None

        except Exception as e:
            logger.error(f"Erro ao buscar no cache: {e}")
            return None
        finally:
            session.close()

    def save_translation(
        self,
        original_text: str,
        translated_text: str,
        source_lang: str,
        target_lang: str,
        provider: str,
        confidence: float = 1.0
    ):
        """
        Salva tradução no cache.
        
        Args:
            original_text: Texto original
            translated_text: Texto traduzido
            source_lang: Idioma origem
            target_lang: Idioma destino
            provider: Provedor usado
            confidence: Confiança da tradução
        """
        session: Session = self.SessionLocal()
        try:
            # Verificar se já existe
            existing = session.query(TranslationCache).filter_by(
                original_text=original_text,
                source_lang=source_lang,
                target_lang=target_lang
            ).first()

            if existing:
                # Atualizar entrada existente
                existing.translated_text = translated_text
                existing.provider = provider
                existing.confidence = confidence
                existing.accessed_count += 1
                existing.last_accessed = datetime.now()
            else:
                # Criar nova entrada
                entry = TranslationCache(
                    original_text=original_text,
                    translated_text=translated_text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    provider=provider,
                    confidence=confidence
                )
                session.add(entry)

            session.commit()
            logger.debug(f"Tradução salva no cache: '{original_text[:30]}...'")

            # Verificar limite de entradas
            self._cleanup_if_needed(session)

        except Exception as e:
            logger.error(f"Erro ao salvar no cache: {e}")
            session.rollback()
        finally:
            session.close()

    def _cleanup_if_needed(self, session: Session):
        """Remove entradas antigas se exceder o limite."""
        count = session.query(TranslationCache).count()
        
        if count > self.max_entries:
            # Remover 10% das entradas mais antigas e menos acessadas
            remove_count = int(self.max_entries * 0.1)
            
            old_entries = session.query(TranslationCache).order_by(
                TranslationCache.accessed_count.asc(),
                TranslationCache.created_at.asc()
            ).limit(remove_count).all()

            for entry in old_entries:
                session.delete(entry)

            session.commit()
            logger.info(f"Cache limpo: {remove_count} entradas removidas")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache."""
        session: Session = self.SessionLocal()
        try:
            translation_count = session.query(TranslationCache).count()
            ocr_count = session.query(OCRCache).count()

            # Tamanho do banco
            db_size_mb = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0

            stats = {
                'total_translations': translation_count,
                'total_ocr': ocr_count,
                'db_size_mb': db_size_mb,
                'max_entries': self.max_entries,
                'cache_full_percent': (translation_count / self.max_entries) * 100
            }

            return stats

        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {}
        finally:
            session.close()

    def clear_cache(self):
        """Limpa todo o cache."""
        session: Session = self.SessionLocal()
        try:
            session.query(TranslationCache).delete()
            session.query(OCRCache).delete()
            session.commit()
            logger.info("Cache completamente limpo")
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")
            session.rollback()
        finally:
            session.close()
