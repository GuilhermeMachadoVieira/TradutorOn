"""
Widget de histórico de traduções.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QHeaderView
)
from PyQt6.QtCore import Qt
from datetime import datetime
from loguru import logger


class HistoryWidget(QWidget):
    """Widget de histórico de traduções."""

    def __init__(self):
        super().__init__()
        
        self.history = []
        self.init_ui()
        
        logger.info("HistoryWidget inicializado")

    def init_ui(self):
        """Inicializa UI."""
        layout = QVBoxLayout(self)
        
        # Tabela
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Horário", "Original", "Traduzido", "Provedor"
        ])
        
        # Ajustar colunas
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.table)
        
        # Botões
        btn_layout = QHBoxLayout()
        
        clear_btn = QPushButton("🗑️ Limpar Histórico")
        clear_btn.clicked.connect(self.clear_history)
        
        export_btn = QPushButton("💾 Exportar CSV")
        export_btn.clicked.connect(self.export_csv)
        
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(export_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)

    def add_translation(self, original: str, translated: str, provider: str):
        """Adiciona tradução ao histórico."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        entry = {
            'timestamp': timestamp,
            'original': original,
            'translated': translated,
            'provider': provider
        }
        
        self.history.append(entry)
        
        # Adicionar à tabela
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        self.table.setItem(row, 0, QTableWidgetItem(timestamp))
        self.table.setItem(row, 1, QTableWidgetItem(original))
        self.table.setItem(row, 2, QTableWidgetItem(translated))
        self.table.setItem(row, 3, QTableWidgetItem(provider))
        
        # Auto-scroll para última linha
        self.table.scrollToBottom()

    def clear_history(self):
        """Limpa histórico."""
        self.history.clear()
        self.table.setRowCount(0)
        logger.info("Histórico limpo")

    def export_csv(self):
        """Exporta histórico para CSV."""
        # TODO: Implementar exportação
        logger.info("Exportação CSV (não implementado)")
