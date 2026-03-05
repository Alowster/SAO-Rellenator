from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QGroupBox, QMessageBox,
)

from core.config_manager import AppConfig
from core.setup_checker import kill_ollama
from ui.config_widget import ConfigWidget
from ui.ia_widget import IAWidget
from ui.log_widget import LogWidget
from ui.automation_widget import AutomationWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("foremp-bot")
        self.setMinimumWidth(600)
        self._config: AppConfig | None = None
        self._build_ui()
        self._connect_signals()

        # Push config from auto-loaded state
        config = self.config_widget.get_config()
        if config:
            self._on_config_saved(config)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        self.log_widget = LogWidget()

        self.config_widget = ConfigWidget()
        self.ia_widget = IAWidget()
        self.automation_widget = AutomationWidget(self.log_widget)

        layout.addWidget(self._wrap("Configuración", self.config_widget))
        layout.addWidget(self._wrap("IA / Gemini", self.ia_widget))
        layout.addWidget(self._wrap("Automatización", self.automation_widget))
        layout.addWidget(self._wrap("Log en tiempo real", self.log_widget))

    @staticmethod
    def _wrap(title: str, widget: QWidget) -> QGroupBox:
        box = QGroupBox(title)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(widget)
        return box

    def _connect_signals(self):
        self.config_widget.config_saved.connect(self._on_config_saved)
        self.ia_widget.text_ready.connect(self.automation_widget.set_text_valid)
        self.automation_widget.bot_started.connect(self._on_bot_started)
        self.automation_widget.bot_finished.connect(self._on_bot_finished)
        self.automation_widget.date_edit.dateChanged.connect(self._on_date_changed)

    def _on_date_changed(self, qdate):
        from datetime import date
        self.ia_widget.set_fecha(date(qdate.year(), qdate.month(), qdate.day()))

    def _on_config_saved(self, config: AppConfig):
        self._config = config
        self.ia_widget.set_config(config)
        self.automation_widget.set_config(config)

    def _on_bot_started(self):
        self.config_widget.setEnabled(False)
        self.ia_widget.setEnabled(False)

    def closeEvent(self, event):
        if self._config and self._config.cerrar_ollama_al_salir:
            kill_ollama()
        super().closeEvent(event)

    def _on_bot_finished(self, success: bool, msg: str):
        self.config_widget.setEnabled(True)
        self.ia_widget.setEnabled(True)

        level = "success" if success else "error"
        self.log_widget.append_log(msg, level)

        if success:
            QMessageBox.information(self, "Completado", msg)
        else:
            QMessageBox.critical(self, "Error", msg)
