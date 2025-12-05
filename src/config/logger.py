"""
Sistema de logging com loguru.
"""

import sys
from pathlib import Path
from loguru import logger


class LoggerSetup:
    """Configurador de logging."""

    @staticmethod
    def initialize(level: str = "INFO", log_file: str = "./logs/translator.log"):
        """
        Inicializa o sistema de logging.
        
        Args:
            level: Nível de log (DEBUG, INFO, WARNING, ERROR)
            log_file: Caminho do arquivo de log
        """
        # Remove handlers padrão
        logger.remove()

        # Console handler (formato simplificado)
        logger.add(
            sys.stdout,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            level=level,
            colorize=True,
        )

        # File handler
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
            level=level,
            rotation="100 MB",
            retention="10 days",
            compression="zip",
        )

        logger.info(f"Logger inicializado - nivel: {level}")
