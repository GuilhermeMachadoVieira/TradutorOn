"""
Detecção de mudanças em frames usando visão computacional.
"""

import cv2
import numpy as np
from typing import Tuple
from enum import Enum
from loguru import logger


class DiffMethod(Enum):
    """Métodos de detecção de diferença."""
    MSE = "mse"
    SSIM = "ssim"
    HYBRID = "hybrid"


class FrameDiff:
    """Detecta mudanças significativas entre frames."""

    def __init__(self, method: DiffMethod = DiffMethod.HYBRID, threshold: float = 0.08):
        """
        Args:
            method: Método de detecção
            threshold: Limiar de mudança (0.0 a 1.0)
        """
        self.method = method
        self.threshold = threshold
        self.last_frame = None
        logger.debug(f"FrameDiff inicializado - método: {method.value}, threshold: {threshold}")

    def detect_change(self, current_frame: np.ndarray, previous_frame: np.ndarray = None) -> Tuple[bool, float]:
        """
        Detecta se houve mudança significativa.
        
        Args:
            current_frame: Frame atual (BGR)
            previous_frame: Frame anterior (opcional, usa o último armazenado)
            
        Returns:
            (houve_mudança, valor_diferença)
        """
        if previous_frame is None:
            previous_frame = self.last_frame

        if previous_frame is None:
            self.last_frame = current_frame.copy()
            return True, 1.0

        try:
            if self.method == DiffMethod.MSE:
                diff_value = self._calculate_mse(current_frame, previous_frame)
            elif self.method == DiffMethod.HYBRID:
                diff_value = self._calculate_hybrid(current_frame, previous_frame)
            else:
                diff_value = self._calculate_mse(current_frame, previous_frame)

            changed = diff_value > self.threshold
            
            if changed:
                self.last_frame = current_frame.copy()
                logger.debug(f"Mudança detectada: {diff_value:.4f}")

            return changed, diff_value

        except Exception as e:
            logger.error(f"Erro ao detectar mudança: {e}")
            return True, 1.0

    def _calculate_mse(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """Calcula Mean Squared Error normalizado."""
        if frame1.shape != frame2.shape:
            return 1.0

        mse = np.mean((frame1.astype(float) - frame2.astype(float)) ** 2)
        # Normalizar para 0-1
        normalized = mse / (255.0 ** 2)
        return normalized

    def _calculate_hybrid(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """Método híbrido: MSE + detecção de features."""
        if frame1.shape != frame2.shape:
            return 1.0

        # 1. MSE rápido
        mse = self._calculate_mse(frame1, frame2)
        
        # Se MSE muito baixo, não há mudança
        if mse < 0.01:
            return mse

        # 2. Detecção de features (ORB)
        try:
            gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

            orb = cv2.ORB_create(nfeatures=100)
            kp1, des1 = orb.detectAndCompute(gray1, None)
            kp2, des2 = orb.detectAndCompute(gray2, None)

            if des1 is None or des2 is None:
                return mse

            # Matcher
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(des1, des2)

            # Proporção de features similares
            match_ratio = len(matches) / max(len(kp1), len(kp2), 1)
            feature_diff = 1.0 - match_ratio

            # Combinar MSE e features
            combined = (mse * 0.6) + (feature_diff * 0.4)
            return combined

        except Exception as e:
            logger.warning(f"Erro no cálculo híbrido, usando MSE: {e}")
            return mse

    def reset(self):
        """Reseta o frame anterior."""
        self.last_frame = None
