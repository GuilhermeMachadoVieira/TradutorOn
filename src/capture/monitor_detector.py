"""
Detecção de monitores com screeninfo.
"""

from typing import List
from screeninfo import get_monitors
from loguru import logger
from src.utils.types import MonitorInfo


class MonitorDetector:
    """Detecta e gerencia informações de monitores."""

    def __init__(self):
        self.monitors: List[MonitorInfo] = []
        self._detect_monitors()

    def _detect_monitors(self):
        """Detecta todos os monitores conectados."""
        try:
            raw_monitors = get_monitors()
            
            for idx, monitor in enumerate(raw_monitors):
                info = MonitorInfo(
                    index=idx,
                    name=monitor.name or f"Monitor {idx}",
                    width=monitor.width,
                    height=monitor.height,
                    x=monitor.x,
                    y=monitor.y,
                    dpi=96  # Padrão, pode ser ajustado
                )
                self.monitors.append(info)
                logger.debug(f"Monitor detectado: {info.name} ({info.width}x{info.height})")
            
            logger.info(f"Total de monitores detectados: {len(self.monitors)}")
            
        except Exception as e:
            logger.error(f"Erro ao detectar monitores: {e}")
            # Fallback: monitor padrão
            self.monitors = [MonitorInfo(0, "Primary", 1920, 1080, 0, 0)]

    def get_monitor(self, index: int = 0) -> MonitorInfo:
        """Retorna informações de um monitor específico."""
        if 0 <= index < len(self.monitors):
            return self.monitors[index]
        return self.monitors[0]

    def get_primary(self) -> MonitorInfo:
        """Retorna o monitor primário."""
        return self.monitors[0] if self.monitors else None
