"""
Interface gráfica do Manga Translator Pro.
"""

from .main_window import MainWindow
from .area_selector import AreaSelector
from .overlay import TranslationOverlay
from .settings_dialog import SettingsDialog
from .history_widget import HistoryWidget

__all__ = [
    'MainWindow',
    'AreaSelector',
    'TranslationOverlay',
    'SettingsDialog',
    'HistoryWidget'
]
