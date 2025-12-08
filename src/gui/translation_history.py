"""Painel de histórico de traduções."""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from datetime import datetime


class TranslationHistoryDialog(QDialog):
    """Diálogo de histórico de traduções."""
    
    def __init__(self, history: list, parent=None):
        super().__init__(parent)
        self.history = history
        self.init_ui()
        self.load_history()
        
    def init_ui(self):
        """Inicializa interface."""
        self.setWindowTitle("📚 Histórico de Traduções")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Título
        title = QLabel(f"📚 Histórico de Traduções ({len(self.history)} itens)")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Tabela
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Hora", "Original", "Tradução", "Idioma", "Provedor"
        ])
        
        # Configurar colunas
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.table)
        
        # Botões
        buttons_layout = QHBoxLayout()
        
        export_btn = QPushButton("💾 Exportar CSV")
        export_btn.clicked.connect(self.export_csv)
        
        clear_btn = QPushButton("🗑️ Limpar Histórico")
        clear_btn.clicked.connect(self.clear_history)
        
        close_btn = QPushButton("❌ Fechar")
        close_btn.clicked.connect(self.accept)
        
        buttons_layout.addWidget(export_btn)
        buttons_layout.addWidget(clear_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)
        
    def load_history(self):
        """Carrega histórico na tabela."""
        self.table.setRowCount(len(self.history))
        
        for i, item in enumerate(self.history):
            # Hora
            timestamp = item.get('timestamp', '')
            self.table.setItem(i, 0, QTableWidgetItem(timestamp))
            
            # Original
            original = item.get('original', '')[:100]
            self.table.setItem(i, 1, QTableWidgetItem(original))
            
            # Tradução
            translated = item.get('translated', '')[:100]
            self.table.setItem(i, 2, QTableWidgetItem(translated))
            
            # Idioma
            language = item.get('language', '?')
            self.table.setItem(i, 3, QTableWidgetItem(language.upper()))
            
            # Provedor
            provider = item.get('provider', '?')
            self.table.setItem(i, 4, QTableWidgetItem(provider))
            
    def export_csv(self):
        """Exporta histórico para CSV."""
        from PyQt6.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Histórico",
            f"historico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        
        if filename:
            try:
                import csv
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Hora', 'Original', 'Tradução', 'Idioma', 'Provedor'])
                    
                    for item in self.history:
                        writer.writerow([
                            item.get('timestamp', ''),
                            item.get('original', ''),
                            item.get('translated', ''),
                            item.get('language', ''),
                            item.get('provider', '')
                        ])
                        
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Sucesso", f"Histórico exportado para:\n{filename}")
                
            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Erro", f"Erro ao exportar:\n{e}")
                
    def clear_history(self):
        """Limpa histórico."""
        from PyQt6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self,
            "Confirmar",
            "Deseja limpar todo o histórico?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.history.clear()
            self.table.setRowCount(0)
            QMessageBox.information(self, "Sucesso", "Histórico limpo!")
