"""
Captura de tela com mss (thread-safe).
"""

import mss
import numpy as np
from PIL import Image
from loguru import logger
from src.utils.types import ScreenArea
import threading


class ScreenCapturer:
    """Captura frames da tela usando mss (thread-safe)."""

    def __init__(self):
        # Thread-local storage para mss
        self._local = threading.local()
        logger.info("ScreenCapturer inicializado")

    def _get_sct(self):
        """Retorna instância mss thread-local."""
        if not hasattr(self._local, 'sct'):
            self._local.sct = mss.mss()
        return self._local.sct

    def capture_area(self, area: ScreenArea) -> np.ndarray:
        """
        Captura uma área específica da tela.
        
        Args:
            area: Área a ser capturada
            
        Returns:
            Frame como numpy array (BGR)
        """
        try:
            sct = self._get_sct()
            
            monitor = {
                "left": area.x1,
                "top": area.y1,
                "width": area.width,
                "height": area.height
            }
            
            screenshot = sct.grab(monitor)
            
            # Converter para numpy array (RGB)
            img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
            frame = np.array(img)
            
            # Converter RGB para BGR (padrão OpenCV)
            frame = frame[:, :, ::-1]
            
            return frame
            
        except Exception as e:
            logger.error(f"Erro ao capturar área: {e}")
            return None

    def release(self):
        """Libera recursos."""
        if hasattr(self._local, 'sct'):
            self._local.sct.close()
            logger.debug("ScreenCapturer liberado")
